"""EST-001 acceptance tests (§6) and ART-002 §13 tests 5–8: timber schedule, preliminary estimate, price books."""

from __future__ import annotations

import json
from fractions import Fraction

import jsonschema
import psycopg
import pytest

from collections import Counter

from api_support import unit_for
from conftest import FIXTURE, REPO_ROOT, VECTORS_PATH
from homedesign.estimating import amount_minor, build_estimate, validate_price_book
from homedesign.model import codes
from homedesign.model.connections import CONNECTION_TYPES, DESCRIPTIONS, FAMILIES
from homedesign.model.canonical import fingerprint
from homedesign.model.schema import Snapshot
from homedesign.project import CommandRejected, NotFound, ProjectService
from homedesign.project.postgres import PostgresStore
from homedesign.timber.schedule import build_schedule, select_schedule, reference_length
from test_connections import _expected_counts, _grid_doc, _with
from test_project import ACTOR, KEY, T0, at, cid, create, envelope, preview_commit, width_cmd

SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())
VECTOR = json.loads(VECTORS_PATH.read_text())["geometry"]["timber_schedule"]
FIXTURE_SNAPSHOT = Snapshot.model_validate(FIXTURE)


def validate_against(name, value):
    jsonschema.Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"}).validate(value)


def book(**prices):
    return {
        "currency": "USD", "as_of": "2026-11-01", "source": "Supplier quote #123", "geography": "Chittenden County, VT",
        "rows": [{"key": key, "unit": unit_for(key), "unit_price_minor": price} for key, price in prices.items()],
    }


POST, BEAM = "timber.POST.8x8", "timber.BEAM.8x12"
PMT, BRIDLE, DOVETAIL = "connection.PEGGED_MORTISE_TENON", "connection.BRIDLE", "connection.HOUSED_DOVETAIL"
# Every timber line of Reference House 001 v2 (D053).
TIMBER = {POST: 3150, BEAM: 4725, "timber.SILL.8x8": 3150, "timber.FLOOR_JOIST.4x8": 1200,
          "timber.PRINCIPAL_RAFTER.8x10": 3900, "timber.PURLIN.6x8": 2350, "timber.KNEE_BRACE.4x6": 900}
# Plus its three connection types (ART-002 §7.1): a book with these rows is complete.
FULL = {**TIMBER, PMT: 4500, BRIDLE: 6500, DOVETAIL: 3800}
# ART-002 §6.2: (junction_class, connection_type) -> count, with the default types.
REFERENCE_CONNECTION_AGGREGATES = [
    ("brace", "PEGGED_MORTISE_TENON", 136), ("joist-beam", "HOUSED_DOVETAIL", 60), ("post-beam", "PEGGED_MORTISE_TENON", 68),
    ("post-sill", "PEGGED_MORTISE_TENON", 12), ("purlin-rafter", "PEGGED_MORTISE_TENON", 24),
    ("rafter-foot", "PEGGED_MORTISE_TENON", 8), ("rafter-peak", "BRIDLE", 4),
]
# ART-002 §6.3, restated so that a change to the constant fails here.
CATALOG_TABLE = {
    "PEGGED_MORTISE_TENON": ("traditional", "Pegged mortise and tenon. Representational only: no capacity, sizes, or fasteners."),
    "BRIDLE": ("traditional", "Bridle joint. Representational only: no capacity, sizes, or fasteners."),
    "HOUSED_DOVETAIL": ("traditional", "Housed dovetail. Representational only: no capacity, sizes, or fasteners."),
    "STEEL_KNIFE_PLATE": ("engineered", "Concealed steel knife plate with dowels. Representational only: no capacity, sizes, or fasteners."),
    "JOIST_HANGER": ("engineered", "Joist hanger. Representational only: no capacity, sizes, or fasteners."),
}
ASSUMPTION_CODES = ["REFERENCE_AXIS_LENGTH", "CONNECTIONS_REPRESENTATIONAL", "UNCLASSED_JOINTS_NOT_COUNTED"]
# D053 reference inventory: (role, section) -> (count, total reference-axis length in feet).
REFERENCE_AGGREGATES = {
    ("BEAM", "8x12"): (34, 34 * 12), ("FLOOR_JOIST", "4x8"): (30, 30 * 12), ("KNEE_BRACE", "4x6"): (68, 68 * 3 * 2**0.5),
    ("POST", "8x8"): (24, 12 * 10 + 12 * 9), ("PRINCIPAL_RAFTER", "8x10"): (8, 8 * 15), ("PURLIN", "6x8"): (12, 12 * 12),
    ("SILL", "8x8"): (17, 17 * 12),
}


def svc_project(store):
    svc = ProjectService(store, token_key=KEY)
    return svc, create(svc).project_id


def estimate(svc, pid, now=T0):
    return svc.artifacts.get_artifact(pid, "preliminary_estimate", now=now)


# 1. schedule -----------------------------------------------------------------------------------


def test_reference_house_schedule():
    schedule = build_schedule(select_schedule(FIXTURE_SNAPSHOT))
    members = {e.id for e in FIXTURE_SNAPSHOT.entities if e.kind == "TimberMember"}
    assert len(schedule["members"]) == 193 and {r["member_id"] for r in schedule["members"]} == members
    keys = [r["generation_key"] for r in schedule["members"]]
    assert keys == sorted(keys) and all(r["quantity"] == 1 for r in schedule["members"])
    aggregates = {(a["role"], a["nominal_section"]): a for a in schedule["aggregates"]}
    assert list(aggregates) == sorted(REFERENCE_AGGREGATES)
    for key, (count, feet) in REFERENCE_AGGREGATES.items():
        assert aggregates[key]["count"] == count
        assert abs(aggregates[key]["total_length_m"] - feet * 0.3048) <= 1e-6 * count, key
    assert sum(a["count"] for a in schedule["aggregates"]) == 193  # reconciles with the inventory (AC-04, AC2-06)
    for aggregate in schedule["aggregates"]:
        rows = [r for r in schedule["members"] if (r["role"], r["nominal_section"]) == (aggregate["role"], aggregate["nominal_section"])]
        total = 0.0
        for r in rows:  # generation_key order (C6)
            total += r["length_m"]
        assert aggregate["total_length_m"] == total
    assert [a["code"] for a in schedule["assumptions"]] == ASSUMPTION_CODES
    assert {r["species"] for r in schedule["members"]} == {"eastern-white-pine"} and {r["grade"] for r in schedule["members"]} == {None}
    validate_against("TimberSchedulePayload", schedule)


# ART-002 §13 test 5: connections in the schedule (AC2-03, AC2-06) -------------------------------


def test_reference_house_schedule_connections():
    schedule = build_schedule(select_schedule(FIXTURE_SNAPSHOT))
    records = {e.id: e for e in FIXTURE_SNAPSHOT.entities if e.kind == "Connection"}
    rows = schedule["connections"]
    assert len(rows) == 312 and {r["connection_id"] for r in rows} == set(records)
    keys = [r["generation_key"] for r in rows]
    assert keys == sorted(keys, key=lambda k: k.encode("utf-16-be"))
    for row in rows:
        record = records[row["connection_id"]]
        assert set(row) == {"connection_id", "generation_key", "junction_class", "connection_type", "member_ids", "quantity"}  # no location
        assert (row["generation_key"], row["junction_class"], row["connection_type"]) == (record.generation_key, record.junction_class, record.connection_type)
        assert row["member_ids"] == record.member_ids and row["quantity"] == 1
    assert [(a["junction_class"], a["connection_type"], a["count"]) for a in schedule["connection_aggregates"]] == REFERENCE_CONNECTION_AGGREGATES
    assert sum(a["count"] for a in schedule["connection_aggregates"]) == len(rows) == len(records)
    assert schedule["connection_catalog"] == {
        "catalog_version": "vs02-connections-1",
        "types": [{"connection_type": t, "family": CATALOG_TABLE[t][0], "description": CATALOG_TABLE[t][1]}
                  for t in ("BRIDLE", "HOUSED_DOVETAIL", "PEGGED_MORTISE_TENON")],
    }
    codes_ = [a["code"] for a in schedule["assumptions"]]
    assert codes_ == ASSUMPTION_CODES and "NO_CONNECTIONS" not in codes_
    assert "not counted" in schedule["assumptions"][2]["message"]  # D059


def test_catalog_families_and_descriptions():
    assert {t: (FAMILIES[t], DESCRIPTIONS[t]) for t in CONNECTION_TYPES} == CATALOG_TABLE
    assert all("Representational only" in d for d in DESCRIPTIONS.values())  # D054, AC2-07


def _class_counts(doc) -> Counter:
    schedule = build_schedule(select_schedule(Snapshot.model_validate(doc)))
    counts = Counter()
    for a in schedule["connection_aggregates"]:
        counts[a["junction_class"]] += a["count"]
    assert sum(counts.values()) == len(schedule["connections"])
    assert all(a["count"] > 0 for a in schedule["connection_aggregates"])  # zero rows are omitted
    return counts


@pytest.mark.parametrize("nx", range(2, 8))
@pytest.mark.parametrize("ny", range(2, 8))
def test_schedule_counts_follow_the_formula_for_every_grid(nx, ny):
    doc = _grid_doc(nx, ny)
    assert _class_counts(doc) == _expected_counts(doc)


@pytest.mark.parametrize(
    "parameters",
    [{"joist_spacing_m": 0.3048}, {"joist_spacing_m": 1.2192}, {"purlins_per_slope": 0}, {"purlins_per_slope": 4},
     {"knee_brace_leg_m": 0.4572}, {"knee_brace_leg_m": 1.2192}, {"knee_braces_level_1": False}],
)
def test_schedule_counts_at_parameter_bounds(parameters):
    doc = _with(**parameters)
    assert _class_counts(doc) == _expected_counts(doc)


def test_zero_cases_omit_their_rows():
    """§13 test 10: both brace planes off and zero purlins leave no brace or purlin-rafter rows."""
    schedule = build_schedule(select_schedule(Snapshot.model_validate(_with(purlins_per_slope=0, knee_braces_level_1=False, knee_braces_eave=False))))
    classes = {a["junction_class"] for a in schedule["connection_aggregates"]}
    assert classes == {"joist-beam", "post-beam", "post-sill", "rafter-foot", "rafter-peak"}
    validate_against("TimberSchedulePayload", schedule)


def test_reference_length_is_the_plain_formula():
    assert reference_length([0.0, 0.0, 0.0], [3.0, 4.0, 12.0]) == 13.0
    assert reference_length([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_schedule_matches_independent_ecmascript_implementation():
    schedule = build_schedule(select_schedule(FIXTURE_SNAPSHOT))
    assert fingerprint(schedule) == VECTOR["fingerprint"] and schedule["aggregates"] == VECTOR["aggregates"]
    assert schedule["connection_aggregates"] == VECTOR["connection_aggregates"]


# 2.–4. coverage -----------------------------------------------------------------------------------


def test_no_book_is_unavailable_never_zero(store):
    svc, pid = svc_project(store)
    env = estimate(svc, pid)
    payload = env["payload"]
    assert env["status"] == "UNAVAILABLE" and payload["coverage"] == "none" and payload["currency"] is None
    assert payload["price_book"] is None and payload["totals"] == {"priced_amount_minor": None, "unpriced_line_count": 10, "grand_total_minor": None}
    assert "COST_INPUTS_MISSING" in [w["code"] for w in env["warnings"]]
    schedule = svc.artifacts.get_artifact(pid, "timber_schedule", now=T0)["payload"]
    # ART-002 §7.1: the connection lines precede the timber lines, by key; quantities from this revision's schedule.
    assert [(li["kind"], li["key"], li["quantity_value"], li["quantity_unit"]) for li in payload["line_items"]] == [
        ("connection", BRIDLE, 4, "each"), ("connection", DOVETAIL, 60, "each"), ("connection", PMT, 248, "each"),
        *(("timber", f"timber.{a['role']}.{a['nominal_section']}", a["total_length_m"], "m") for a in schedule["aggregates"])]  # artifacts.md §10 test 8
    assert all(not li["priced"] and li["amount_minor"] is None and li["unit_price_minor"] is None for li in payload["line_items"])
    assert_connection_lines_follow(schedule, payload)
    validate_against("PreliminaryEstimatePayload", payload)


def assert_connection_lines_follow(schedule, payload):
    """Connection quantities are the per-type sums of the same schedule; its assumptions are copied (§7.1–7.2)."""
    per_type = Counter()
    for a in schedule["connection_aggregates"]:
        per_type[a["connection_type"]] += a["count"]
    lines = {li["connection_type"]: li["quantity_value"] for li in payload["line_items"] if li["kind"] == "connection"}
    assert lines == dict(per_type)
    assert all(isinstance(q, int) for q in lines.values())
    assert payload["assumptions"] == schedule["assumptions"]


def test_partial_book(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**{POST: 3150}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    payload = env["payload"]
    assert (env["status"], payload["coverage"], payload["currency"]) == ("CURRENT", "partial", "USD")
    assert payload["totals"]["grand_total_minor"] is None and payload["totals"]["unpriced_line_count"] == 9
    assert payload["totals"]["priced_amount_minor"] == next(li["amount_minor"] for li in payload["line_items"] if li["key"] == POST)
    assert "COST_INPUTS_MISSING" in [w["code"] for w in env["warnings"]]


def test_timber_only_book_is_partial(store):
    """§13 test 6: a book that prices every timber line leaves the connection lines unpriced, never 0."""
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**TIMBER), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    payload = env["payload"]
    assert (env["status"], payload["coverage"], payload["totals"]["grand_total_minor"]) == ("CURRENT", "partial", None)
    assert payload["totals"]["unpriced_line_count"] == 3
    unpriced = [li for li in payload["line_items"] if not li["priced"]]
    assert [li["key"] for li in unpriced] == [BRIDLE, DOVETAIL, PMT]
    assert all(li["amount_minor"] is None and li["unit_price_minor"] is None for li in unpriced)
    assert payload["totals"]["priced_amount_minor"] == sum(li["amount_minor"] for li in payload["line_items"] if li["priced"])
    assert "COST_INPUTS_MISSING" in [w["code"] for w in env["warnings"]]


def test_complete_book(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**FULL), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    payload = env["payload"]
    assert (env["status"], payload["coverage"]) == ("CURRENT", "complete")
    for line in payload["line_items"]:  # independent exact check with Fraction and banker's rounding
        assert line["amount_minor"] == round(Fraction(line["unit_price_minor"]) * Fraction(line["quantity_value"]))
    connection_amounts = {li["key"]: li["amount_minor"] for li in payload["line_items"] if li["kind"] == "connection"}
    assert connection_amounts == {BRIDLE: 6500 * 4, DOVETAIL: 3800 * 60, PMT: 4500 * 248}  # exact integer products
    schedule = svc.artifacts.get_artifact(pid, "timber_schedule", now=at(1))["payload"]
    assert_connection_lines_follow(schedule, payload)
    assert payload["totals"]["grand_total_minor"] == sum(li["amount_minor"] for li in payload["line_items"])
    assert isinstance(payload["totals"]["grand_total_minor"], int)
    assert payload["price_book"]["price_book_version"] == 1 and payload["price_book"]["source"] == "Supplier quote #123"
    assert "COST_INPUTS_MISSING" not in [w["code"] for w in env["warnings"]]


def test_unused_rows_are_ignored_with_a_warning(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**FULL, **{"timber.RAFTER.2x10": 900}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    assert env["payload"]["coverage"] == "complete"
    assert any(w["code"] == "PRICE_ROWS_UNUSED" and "timber.RAFTER.2x10" in w["message"] for w in env["warnings"])


def test_unused_connection_row_warns(store):
    """§7.3: a type with no connections (before any SetConnectionType) is an unused row."""
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**FULL, **{"connection.STEEL_KNIFE_PLATE": 12000}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    assert env["payload"]["coverage"] == "complete"
    (unused,) = [w for w in env["warnings"] if w["code"] == "PRICE_ROWS_UNUSED"]
    assert "connection.STEEL_KNIFE_PLATE" in unused["message"]


def test_connection_type_switch_moves_the_count(store):
    """§13 test 7: SetConnectionType {joist-beam, JOIST_HANGER} moves 60 pieces to a new, unpriced line."""
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**FULL), actor_id=ACTOR, now=at(1))
    preview_commit(svc, pid, envelope(svc, pid, "SetConnectionType", {"junction_class": "joist-beam", "connection_type": "JOIST_HANGER"}), now=at(2))
    schedule = svc.artifacts.get_artifact(pid, "timber_schedule", now=at(2))["payload"]
    assert ("joist-beam", "JOIST_HANGER", 60) in [(a["junction_class"], a["connection_type"], a["count"]) for a in schedule["connection_aggregates"]]
    assert [t["connection_type"] for t in schedule["connection_catalog"]["types"]] == ["BRIDLE", "JOIST_HANGER", "PEGGED_MORTISE_TENON"]
    env = estimate(svc, pid, at(2))
    lines = {li["key"]: li for li in env["payload"]["line_items"]}
    assert lines["connection.JOIST_HANGER"]["quantity_value"] == 60 and not lines["connection.JOIST_HANGER"]["priced"]
    assert DOVETAIL not in lines and env["payload"]["coverage"] == "partial"
    (unused,) = [w for w in env["warnings"] if w["code"] == "PRICE_ROWS_UNUSED"]
    assert DOVETAIL in unused["message"]
    assert_connection_lines_follow(schedule, env["payload"])


def test_amount_beyond_safe_integers_fails_the_derivation(store):
    """§7.3: an amount outside ±(2^53 − 1) fails the payload's validation and is DERIVATION_FAILED."""
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**{PMT: 2**53 - 1}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    assert env["status"] == "FAILED" and env["error"]["code"] == "DERIVATION_FAILED" and env.get("payload") is None


# 5. rounding -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "price,quantity,expected",
    [(3, 0.5, 2), (5, 0.5, 2), (7, 0.5, 4), (1, 0.5, 0), (1, 1.5, 2), (1, 2.5, 2),
     (5, 0.1, 1),  # 0.1 is slightly above 1/10 in binary, so 0.5000000000000000277… rounds up
     (10, 0.1, 1), (0, 69.4944, 0), (3150, 69.49440000000003, 218907)],
)
def test_half_even_on_the_exact_binary_value(price, quantity, expected):
    assert amount_minor(price, quantity) == expected == round(Fraction(price) * Fraction(quantity))


# 6. book changes -----------------------------------------------------------------------------------


def test_book_change_makes_only_the_estimate_stale(store):
    svc, pid = svc_project(store)
    head_id = svc.get_project(pid)["head_revision_id"]
    before = {t: svc.artifacts.get_artifact(pid, t, now=T0) for t in ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate")}
    first = svc.set_price_book(pid, book(**{POST: 3150}), actor_id=ACTOR, now=at(1))
    second = svc.set_price_book(pid, book(**{POST: 3150, BEAM: 4725}), actor_id=ACTOR, now=at(2))
    assert (first["version"], second["version"]) == (1, 2) and first["price_book_id"] == second["price_book_id"]
    assert svc.get_project(pid)["head_revision_id"] == head_id  # not a model command: no revision
    statuses = svc.artifacts.statuses(pid, head_id)
    assert statuses == {"plan2d": "CURRENT", "mesh3d": "CURRENT", "timber_schedule": "CURRENT", "preliminary_estimate": "STALE"}
    refreshed = estimate(svc, pid, at(3))
    assert refreshed["status"] == "CURRENT" and refreshed["payload"]["price_book"]["price_book_version"] == 2
    assert refreshed["input_fingerprint"] != before["preliminary_estimate"]["input_fingerprint"]
    for t in ("plan2d", "mesh3d", "timber_schedule"):
        assert svc.artifacts.get_artifact(pid, t, now=at(3))["input_fingerprint"] == before[t]["input_fingerprint"]
    assert svc.get_price_book(pid)["version"] == 2


# 7. unique labels (D049) ----------------------------------------------------------------------------


def test_duplicate_section_label_is_rejected(store):
    svc, pid = svc_project(store)
    command = envelope(svc, pid, "AddSection", {"nominal_label": "8x8", "actual_width_m": 0.1905, "actual_depth_m": 0.1905})
    with pytest.raises(CommandRejected) as exc:
        svc.commit(pid, command, actor_id=ACTOR, now=T0)
    assert codes.DUPLICATE_SECTION_LABEL in {i.code for i in exc.value.result.issues}


# 8. recomputation after model changes -------------------------------------------------------------------


def test_width_change_recomputes_schedule_and_estimate(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**FULL), actor_id=ACTOR, now=at(1))
    before = estimate(svc, pid, at(1))["payload"]
    preview_commit(svc, pid, width_cmd(svc, pid, 12.192), now=at(2))
    schedule = svc.artifacts.get_artifact(pid, "timber_schedule", now=at(2))["payload"]
    after = estimate(svc, pid, at(2))["payload"]
    beam = next(a for a in schedule["aggregates"] if a["role"] == "BEAM")
    assert beam["total_length_m"] > 124.3584  # longer X-beams
    assert next(li for li in after["line_items"] if li["key"] == BEAM)["quantity_value"] == beam["total_length_m"]
    assert after["totals"]["grand_total_minor"] > before["totals"]["grand_total_minor"]


# 9. determinism -----------------------------------------------------------------------------------------


def test_estimate_is_deterministic():
    schedule = build_schedule(select_schedule(FIXTURE_SNAPSHOT))
    row = {"price_book_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "version": 3, "book": book(**{POST: 3150, BEAM: 4725})}
    assert build_estimate(schedule, row) == build_estimate(schedule, row)


# 10. contract and invalid books -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate,code,path",
    [
        (lambda b: b.__setitem__("currency", "EUR"), codes.INVALID_ENUM, "currency"),
        (lambda b: b.__setitem__("as_of", "Nov 1"), codes.INVALID_TIMESTAMP, "as_of"),
        (lambda b: b.__setitem__("as_of", "2026-02-30"), codes.INVALID_TIMESTAMP, "as_of"),
        (lambda b: b["rows"][0].__setitem__("unit", "ft"), codes.INVALID_ENUM, "rows[0].unit"),
        (lambda b: b["rows"][0].__setitem__("unit_price_minor", 12.5), codes.INTEGER_OUT_OF_RANGE, "rows[0].unit_price_minor"),
        (lambda b: b["rows"][0].__setitem__("unit_price_minor", -1), codes.OUT_OF_RANGE, "rows[0].unit_price_minor"),
        (lambda b: b["rows"].append(dict(b["rows"][0])), codes.DUPLICATE_PRICE_KEY, "rows[2].key"),
        (lambda b: b.__setitem__("discount", 5), codes.UNKNOWN_FIELD, "discount"),
        (lambda b: b.pop("source"), codes.MISSING_FIELD, "source"),
        (lambda b: b["rows"][0].__setitem__("unit", "each"), codes.PRICE_UNIT_MISMATCH, "rows[0].unit"),
        (lambda b: b["rows"].append({"key": PMT, "unit": "m", "unit_price_minor": 4500}), codes.PRICE_UNIT_MISMATCH, "rows[2].unit"),
    ],
)
def test_invalid_books_are_rejected(store, mutate, code, path):
    svc, pid = svc_project(store)
    candidate = book(**{POST: 3150, BEAM: 4725})
    mutate(candidate)
    _, result = validate_price_book(candidate)
    assert (code, path) in {(i.code, i.path) for i in result.issues}
    with pytest.raises(CommandRejected):
        svc.set_price_book(pid, candidate, actor_id=ACTOR, now=T0)
    assert svc.get_price_book(pid) is None


def test_unit_mismatch_is_reported_with_duplicate_keys():
    """§13 test 8: PRICE_UNIT_MISMATCH shares stage 2 with DUPLICATE_PRICE_KEY, so both are reported."""
    candidate = book(**{POST: 3150, PMT: 4500})
    candidate["rows"][0]["unit"] = "each"
    candidate["rows"].append({"key": PMT, "unit": "m", "unit_price_minor": 4600})
    _, result = validate_price_book(candidate)
    assert result.code == codes.VALIDATION_FAILED
    assert [(i.code, i.path, i.value, i.related_paths) for i in result.issues] == [
        (codes.PRICE_UNIT_MISMATCH, "rows[0].unit", "each", ("rows[0].key",)),
        (codes.DUPLICATE_PRICE_KEY, "rows[2].key", PMT, ("rows[1].key",)),
        (codes.PRICE_UNIT_MISMATCH, "rows[2].unit", "m", ("rows[2].key",)),
    ]


def test_each_rows_and_other_keys():
    """`each` rows are accepted for connection keys; keys of other families take either unit (§7.3)."""
    candidate = book(**{PMT: 4500})
    candidate["rows"] += [{"key": "labor.framing", "unit": "each", "unit_price_minor": 1}, {"key": "misc", "unit": "m", "unit_price_minor": 1}]
    parsed, result = validate_price_book(candidate)
    assert result is None and [r.unit for r in parsed.rows] == ["each", "each", "m"]
    validate_against("PriceBook", candidate)


def test_price_book_schema_and_unknown_project(store):
    validate_against("PriceBook", book(**{POST: 3150}))
    svc = ProjectService(store, token_key=KEY)
    with pytest.raises(NotFound):
        svc.set_price_book(cid(), book(**{POST: 1}), actor_id=ACTOR, now=T0)


def test_price_books_are_append_only(pg_url):
    svc = ProjectService(PostgresStore(pg_url), token_key=KEY)
    pid = create(svc).project_id
    svc.set_price_book(pid, book(**{POST: 3150}), actor_id=ACTOR, now=T0)
    with psycopg.connect(pg_url) as conn, pytest.raises(psycopg.errors.RestrictViolation):
        conn.execute("UPDATE price_books SET version = 9 WHERE project_id = %s", (pid,))
