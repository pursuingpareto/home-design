"""EST-001 acceptance tests (§6): timber schedule, preliminary estimate, price books."""

from __future__ import annotations

import json
from fractions import Fraction

import jsonschema
import psycopg
import pytest

from conftest import FIXTURE, REPO_ROOT, VECTORS_PATH
from homedesign.estimating import amount_minor, build_estimate, validate_price_book
from homedesign.model import codes
from homedesign.model.canonical import fingerprint
from homedesign.model.schema import Snapshot
from homedesign.project import CommandRejected, NotFound, ProjectService
from homedesign.project.postgres import PostgresStore
from homedesign.timber.schedule import build_schedule, reference_length
from test_project import ACTOR, KEY, T0, at, cid, create, envelope, preview_commit, width_cmd

SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())
VECTOR = json.loads(VECTORS_PATH.read_text())["geometry"]["timber_schedule"]
FIXTURE_SNAPSHOT = Snapshot.model_validate(FIXTURE)


def validate_against(name, value):
    jsonschema.Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"}).validate(value)


def book(**prices):
    return {
        "currency": "USD", "as_of": "2026-11-01", "source": "Supplier quote #123", "geography": "Chittenden County, VT",
        "rows": [{"key": key, "unit": "m", "unit_price_minor": price} for key, price in prices.items()],
    }


POST, BEAM = "timber.POST.8x8", "timber.BEAM.8x12"


def svc_project(store):
    svc = ProjectService(store, token_key=KEY)
    return svc, create(svc).project_id


def estimate(svc, pid, now=T0):
    return svc.artifacts.get_artifact(pid, "preliminary_estimate", now=now)


# 1. schedule -----------------------------------------------------------------------------------


def test_reference_house_schedule():
    schedule = build_schedule(FIXTURE_SNAPSHOT)
    members = {e.id for e in FIXTURE_SNAPSHOT.entities if e.kind == "TimberMember"}
    assert len(schedule["members"]) == 58 and {r["member_id"] for r in schedule["members"]} == members
    keys = [r["generation_key"] for r in schedule["members"]]
    assert keys == sorted(keys) and all(r["quantity"] == 1 for r in schedule["members"])
    (beam, post) = schedule["aggregates"]
    assert (beam["role"], beam["nominal_section"], beam["count"]) == ("BEAM", "8x12", 34)
    assert (post["role"], post["nominal_section"], post["count"]) == ("POST", "8x8", 24)
    assert abs(beam["total_length_m"] - 124.3584) <= 1e-6 * 34 and abs(post["total_length_m"] - 69.4944) <= 1e-6 * 24
    assert sum(a["count"] for a in schedule["aggregates"]) == 58  # reconciles with the inventory (AC-04)
    for aggregate in schedule["aggregates"]:
        rows = [r for r in schedule["members"] if (r["role"], r["nominal_section"]) == (aggregate["role"], aggregate["nominal_section"])]
        total = 0.0
        for r in rows:  # generation_key order (C6)
            total += r["length_m"]
        assert aggregate["total_length_m"] == total
    assert [a["code"] for a in schedule["assumptions"]] == ["REFERENCE_AXIS_LENGTH", "NO_CONNECTIONS"]
    assert {r["species"] for r in schedule["members"]} == {"eastern-white-pine"} and {r["grade"] for r in schedule["members"]} == {None}
    validate_against("TimberSchedulePayload", schedule)


def test_reference_length_is_the_plain_formula():
    assert reference_length([0.0, 0.0, 0.0], [3.0, 4.0, 12.0]) == 13.0
    assert reference_length([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_schedule_matches_independent_ecmascript_implementation():
    schedule = build_schedule(FIXTURE_SNAPSHOT)
    assert fingerprint(schedule) == VECTOR["fingerprint"] and schedule["aggregates"] == VECTOR["aggregates"]


# 2.–4. coverage -----------------------------------------------------------------------------------


def test_no_book_is_unavailable_never_zero(store):
    svc, pid = svc_project(store)
    env = estimate(svc, pid)
    payload = env["payload"]
    assert env["status"] == "UNAVAILABLE" and payload["coverage"] == "none" and payload["currency"] is None
    assert payload["price_book"] is None and payload["totals"] == {"priced_amount_minor": None, "unpriced_line_count": 2, "grand_total_minor": None}
    assert "COST_INPUTS_MISSING" in [w["code"] for w in env["warnings"]]
    schedule = svc.artifacts.get_artifact(pid, "timber_schedule", now=T0)["payload"]
    assert [(li["key"], li["quantity_value"]) for li in payload["line_items"]] == [
        (f"timber.{a['role']}.{a['nominal_section']}", a["total_length_m"]) for a in schedule["aggregates"]]  # artifacts.md §10 test 8
    validate_against("PreliminaryEstimatePayload", payload)


def test_partial_book(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**{POST: 3150}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    payload = env["payload"]
    assert (env["status"], payload["coverage"], payload["currency"]) == ("CURRENT", "partial", "USD")
    assert payload["totals"]["grand_total_minor"] is None and payload["totals"]["unpriced_line_count"] == 1
    assert payload["totals"]["priced_amount_minor"] == next(li["amount_minor"] for li in payload["line_items"] if li["key"] == POST)
    assert "COST_INPUTS_MISSING" in [w["code"] for w in env["warnings"]]


def test_complete_book(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**{POST: 3150, BEAM: 4725}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    payload = env["payload"]
    assert (env["status"], payload["coverage"]) == ("CURRENT", "complete")
    for line in payload["line_items"]:  # independent exact check with Fraction and banker's rounding
        assert line["amount_minor"] == round(Fraction(line["unit_price_minor"]) * Fraction(line["quantity_value"]))
    assert payload["totals"]["grand_total_minor"] == sum(li["amount_minor"] for li in payload["line_items"])
    assert isinstance(payload["totals"]["grand_total_minor"], int)
    assert payload["price_book"]["price_book_version"] == 1 and payload["price_book"]["source"] == "Supplier quote #123"
    assert "COST_INPUTS_MISSING" not in [w["code"] for w in env["warnings"]]


def test_unused_rows_are_ignored_with_a_warning(store):
    svc, pid = svc_project(store)
    svc.set_price_book(pid, book(**{POST: 3150, BEAM: 4725, "timber.RAFTER.2x10": 900}), actor_id=ACTOR, now=at(1))
    env = estimate(svc, pid, at(1))
    assert env["payload"]["coverage"] == "complete"
    assert any(w["code"] == "PRICE_ROWS_UNUSED" and "timber.RAFTER.2x10" in w["message"] for w in env["warnings"])


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
    svc.set_price_book(pid, book(**{POST: 3150, BEAM: 4725}), actor_id=ACTOR, now=at(1))
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
    schedule = build_schedule(FIXTURE_SNAPSHOT)
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
