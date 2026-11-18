"""MODEL-001 §7.2 mutation table, D036 path forms, and D037 related-path mapping.

Each case mutates Reference House 001 once and asserts the top-level code and the
expected detail issues (code, path, and related_paths where specified).
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from conftest import FIXTURE, FIXTURE_BYTES, entities_of, epath, fresh_fixture, index_of
from homedesign.model import codes, validate_bytes, validate_value
from homedesign.model.validation import ValidationResult

VF = codes.VALIDATION_FAILED
UC = codes.UNSUPPORTED_CONFIGURATION

FOOTPRINT = entities_of(FIXTURE, "Footprint")[0]
LEVEL0, LEVEL1 = sorted(entities_of(FIXTURE, "Level"), key=lambda e: e["index"])
ROOF = entities_of(FIXTURE, "GableRoof")[0]
GRID = entities_of(FIXTURE, "TimberGrid")[0]
FRAME = entities_of(FIXTURE, "FrameSystem")[0]
SECTION_8X8 = next(e for e in entities_of(FIXTURE, "Section") if e["nominal_label"] == "8x8")
MATERIAL = entities_of(FIXTURE, "Material")[0]
MEMBERS = entities_of(FIXTURE, "TimberMember")
NEW_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _find(doc, entity_id):
    return next(e for e in doc["entities"] if e["id"] == entity_id)


@dataclass
class Expect:
    code: str
    path: str
    related: tuple[str, ...] | None = None  # None = do not check


@dataclass
class Case:
    name: str
    build: Callable[[], ValidationResult]
    top: str | None
    expect: list[Expect] = field(default_factory=list)
    only: bool = False  # the expected issues are the complete issue list


def doc_case(name, mutate, top, expect, only=False) -> Case:
    def build():
        doc = fresh_fixture()
        mutate(doc)
        return validate_value(doc)

    return Case(name, build, top, expect, only)


def text_case(name, transform, top, expect, only=False) -> Case:
    return Case(name, lambda: validate_bytes(transform(FIXTURE_BYTES)), top, expect, only)


def _set(entity_id, key, value):
    return lambda d: _find(d, entity_id).__setitem__(key, value)


def _swap_member_ids(d):
    ids = _find(d, FRAME["id"])["member_ids"]
    ids[0], ids[1] = ids[1], ids[0]


def _duplicate_material(d):
    d["entities"].append(dict(_find(d, MATERIAL["id"])))


def _second_footprint(d):
    d["entities"].append(dict(_find(d, FOOTPRINT["id"]), id=NEW_ID))


def _third_level(d):
    d["entities"].append(
        {"id": NEW_ID, "kind": "Level", "schema_version": 1, "index": 2, "elevation_m": 5.7912, "story_height_m": 2.7432}
    )
    d["building"]["level_ids"].append(NEW_ID)


def _deep(d):
    nested: list = []
    for _ in range(40):
        nested = [nested]
    d["deep"] = nested


MEMBER_A, MEMBER_B = sorted(MEMBERS[:2], key=lambda m: m["id"])  # A has the lower id
UPPER_SECTION_ID = SECTION_8X8["id"].upper()
SECTION_INDEX = index_of(FIXTURE, SECTION_8X8["id"])
MATERIAL_INDEX = index_of(FIXTURE, MATERIAL["id"])
LAST = len(FIXTURE["entities"])  # index of an appended entity

CASES: list[Case] = [
    doc_case("01-negative-width", _set(FOOTPRINT["id"], "width_m", -1), VF,
             [Expect(codes.OUT_OF_RANGE, epath(FOOTPRINT, "width_m"))], only=True),
    text_case("02-nan-token", lambda b: b.replace(b'"width_m": 10.9728', b'"width_m": NaN'), VF,
              [Expect(codes.NON_FINITE_NUMBER, epath(FOOTPRINT, "width_m"))], only=True),
    text_case("03-overflowing-literal", lambda b: b.replace(b'"width_m": 10.9728', b'"width_m": 1e400'), VF,
              [Expect(codes.NON_FINITE_NUMBER, epath(FOOTPRINT, "width_m"))], only=True),
    doc_case("04-width-30m", _set(FOOTPRINT["id"], "width_m", 30), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FOOTPRINT, "width_m"))]),
    doc_case("05-width-23m-bays-too-long", _set(FOOTPRINT["id"], "width_m", 23), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(GRID, "x_fractions"), (epath(FOOTPRINT, "width_m"),))], only=True),
    doc_case("06-dangling-section", _set(MEMBERS[0]["id"], "section_id", NEW_ID), VF,
             [Expect(codes.DANGLING_REFERENCE, epath(MEMBERS[0], "section_id"))], only=True),
    doc_case("07-section-points-to-material", _set(MEMBERS[0]["id"], "section_id", MATERIAL["id"]), VF,
             [Expect(codes.WRONG_REFERENCE_KIND, epath(MEMBERS[0], "section_id"))], only=True),
    doc_case("08-missing-footprint-id", lambda d: d["building"].pop("footprint_id"), VF,
             [Expect(codes.MISSING_FIELD, "building.footprint_id")], only=True),
    doc_case("09-duplicate-id", _duplicate_material, VF,
             [Expect(codes.DUPLICATE_ID, f"entities[#{LAST}]", (f"entities[#{MATERIAL_INDEX}]",))], only=True),
    text_case("10-uppercase-uuid", lambda b: b.replace(SECTION_8X8["id"].encode(), UPPER_SECTION_ID.encode()), VF,
              [Expect(codes.INVALID_UUID, f"entities[#{SECTION_INDEX}].id")]),
    doc_case("11-fractions-out-of-order", _set(GRID["id"], "x_fractions", [0.0, 2 / 3, 1 / 3, 1.0]), VF,
             [Expect(codes.NOT_STRICTLY_ASCENDING, epath(GRID, "x_fractions", 2))], only=True),
    doc_case("12-missing-grid-endpoint", _set(GRID["id"], "y_fractions", [0.0, 0.5]), VF,
             [Expect(codes.GRID_ENDPOINT_MISSING, epath(GRID, "y_fractions"))], only=True),
    doc_case("13-model-schema-version-2", lambda d: d.__setitem__("model_schema_version", 2), VF,
             [Expect(codes.UNSUPPORTED_SCHEMA_VERSION, "model_schema_version")], only=True),
    doc_case("14-unknown-field", _set(FOOTPRINT["id"], "color", "red"), VF,
             [Expect(codes.UNKNOWN_FIELD, epath(FOOTPRINT, "color"))], only=True),
    text_case("15-duplicate-key", lambda b: b.replace(b'"width_m": 10.9728,', b'"width_m": 10.9728, "width_m": 10.9728,'), VF,
              [Expect(codes.DUPLICATE_KEY, epath(FOOTPRINT, "width_m"))], only=True),
    doc_case("16-story-height-mismatch", _set(LEVEL0["id"], "story_height_m", 3.0), VF,
             [Expect(codes.STORY_HEIGHT_MISMATCH, epath(LEVEL0, "story_height_m"), (epath(LEVEL1, "elevation_m"),))], only=True),
    doc_case("17-origin-not-zero", _set(FOOTPRINT["id"], "origin_m", [1.0, 0.0]), VF,
             [Expect(codes.DATUM_MISMATCH, epath(FOOTPRINT, "origin_m"))], only=True),
    doc_case("18-rotation", _set(FOOTPRINT["id"], "rotation_rad", 0.1), UC,
             [Expect(codes.UNSUPPORTED_VALUE, epath(FOOTPRINT, "rotation_rad"))], only=True),
    doc_case("19-ridge-axis-y", _set(ROOF["id"], "ridge_axis", "Y"), UC,
             [Expect(codes.UNSUPPORTED_VALUE, epath(ROOF, "ridge_axis"))], only=True),
    doc_case("20a-pitch-too-steep", _set(ROOF["id"], "pitch_rad", math.atan(2)), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(ROOF, "pitch_rad"))], only=True),
    doc_case("20b-pitch-zero", _set(ROOF["id"], "pitch_rad", 0.0), VF,
             [Expect(codes.OUT_OF_RANGE, epath(ROOF, "pitch_rad"))], only=True),
    doc_case("21-zero-length-member", _set(MEMBERS[0]["id"], "end_m", list(MEMBERS[0]["start_m"])), VF,
             [Expect(codes.ZERO_LENGTH_MEMBER, epath(MEMBERS[0]))], only=True),
    doc_case("22-member-missing-from-member-ids", lambda d: _find(d, FRAME["id"])["member_ids"].remove(MEMBERS[5]["id"]), VF,
             [Expect(codes.MEMBER_SET_MISMATCH, epath(FRAME, "member_ids"), (epath(MEMBERS[5]),))], only=True),
    doc_case("23-member-ids-swapped", _swap_member_ids, VF,
             [Expect(codes.ORDER_VIOLATION, epath(FRAME, "member_ids"))], only=True),
    doc_case("24-building-in-entities", lambda d: d["entities"].append(dict(d["building"])), VF,
             [Expect(codes.BUILDING_IN_ENTITIES, f"entities[#{LAST}]"),
              Expect(codes.DUPLICATE_ID, f"entities[#{LAST}]", ("building",))]),
    doc_case("25-story-height-15ft", _set(LEVEL1["id"], "story_height_m", 4.572), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(LEVEL1, "story_height_m"))], only=True),
    doc_case("26-schema-version-2^53", _set(FOOTPRINT["id"], "schema_version", 2**53), VF,
             [Expect(codes.INTEGER_OUT_OF_RANGE, epath(FOOTPRINT, "schema_version"))], only=True),
    doc_case("27-material-grade-missing", lambda d: _find(d, MATERIAL["id"]).pop("grade"), VF,
             [Expect(codes.MISSING_FIELD, epath(MATERIAL, "grade"))], only=True),
    doc_case("28-stage-gating",
             lambda d: (_set(FOOTPRINT["id"], "width_m", -1)(d), _set(FOOTPRINT["id"], "rotation_rad", 0.1)(d)), VF,
             [Expect(codes.OUT_OF_RANGE, epath(FOOTPRINT, "width_m"))], only=True),
    doc_case("29-width-inside-epsilon", _set(FOOTPRINT["id"], "width_m", 3.6576 - 5e-7), None, [], only=True),
    doc_case("30-width-outside-epsilon", _set(FOOTPRINT["id"], "width_m", 3.6576 - 2e-6), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FOOTPRINT, "width_m"))], only=True),
    text_case("31-truncated", lambda b: b[: len(b) // 2], VF, [Expect(codes.MALFORMED_JSON, "")], only=True),
    text_case("32a-too-large", lambda b: b + b" " * (4 * 1024 * 1024), VF,
              [Expect(codes.PAYLOAD_LIMIT_EXCEEDED, "")], only=True),
    doc_case("32b-too-deep", _deep, VF, [Expect(codes.PAYLOAD_LIMIT_EXCEEDED, "")], only=True),
    doc_case("33-width-string", _set(FOOTPRINT["id"], "width_m", "36"), VF,
             [Expect(codes.WRONG_TYPE, epath(FOOTPRINT, "width_m"))], only=True),
    doc_case("34-ridge-axis-z", _set(ROOF["id"], "ridge_axis", "Z"), VF,
             [Expect(codes.INVALID_ENUM, epath(ROOF, "ridge_axis"))], only=True),
    doc_case("35-bad-timestamp", lambda d: d.__setitem__("created_at", "yesterday"), VF,
             [Expect(codes.INVALID_TIMESTAMP, "created_at")], only=True),
    doc_case("36-unknown-kind", _set(SECTION_8X8["id"], "kind", "Wall"), VF,
             [Expect(codes.UNKNOWN_KIND, epath(SECTION_8X8, "kind"))], only=True),
    doc_case("37-second-footprint", _second_footprint, VF,
             [Expect(codes.UNREFERENCED_ENTITY, f"entities[{NEW_ID}]")], only=True),
    doc_case("38-duplicate-generation-key", _set(MEMBER_B["id"], "generation_key", MEMBER_A["generation_key"]), VF,
             [Expect(codes.DUPLICATE_GENERATION_KEY, epath(MEMBER_B, "generation_key"), (epath(MEMBER_A, "generation_key"),))]),
    doc_case("39-third-level", _third_level, UC,
             [Expect(codes.ENTITY_COUNT, "building.level_ids")], only=True),
    doc_case("40-rafter-role", _set(MEMBERS[0]["id"], "member_role", "RAFTER"), UC,
             [Expect(codes.UNSUPPORTED_VALUE, epath(MEMBERS[0], "member_role"))], only=True),
    # D037 mapping row: level elevations
    doc_case("d037-elevations-not-ascending", _set(LEVEL1["id"], "elevation_m", 0.0), VF,
             [Expect(codes.NOT_STRICTLY_ASCENDING, epath(LEVEL1, "elevation_m"), (epath(LEVEL0, "elevation_m"),)),
              Expect(codes.STORY_HEIGHT_MISMATCH, epath(LEVEL0, "story_height_m"), (epath(LEVEL1, "elevation_m"),))]),
    # D036 path forms: quoted keys
    doc_case("d036-quoted-entity-key", _set(FOOTPRINT["id"], "a.b", 1), VF,
             [Expect(codes.UNKNOWN_FIELD, f'entities[{FOOTPRINT["id"]}]["a.b"]')], only=True),
    doc_case("d036-quoted-root-key", lambda d: d.__setitem__("x-y", 1), VF,
             [Expect(codes.UNKNOWN_FIELD, '["x-y"]')], only=True),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mutation(case: Case):
    result = case.build()
    assert result.code == case.top, result.to_dict()
    assert result.valid is (case.top is None)
    found = {(i.code, i.path): i for i in result.issues}
    for expected in case.expect:
        issue = found.get((expected.code, expected.path))
        assert issue is not None, f"missing {expected}; got {result.to_dict()['issues']}"
        if expected.related is not None:
            assert issue.related_paths == expected.related
    if case.only:
        assert len(result.issues) == len(case.expect), result.to_dict()
    for issue in result.issues:
        assert codes.CATALOG[issue.code].top_level_code == result.code


def test_every_catalog_code_is_exercised():
    exercised = {e.code for case in CASES for e in case.expect}
    assert exercised == set(codes.CATALOG)


def test_issue_values_are_finite_scalars_only():
    result = CASES[0].build()
    assert result.issues[0].value == -1
    missing = next(c for c in CASES if c.name.startswith("08")).build()
    assert missing.issues[0].value is None


@pytest.mark.parametrize("seed", [7, 99])
def test_id_addressed_issues_do_not_depend_on_entity_order(seed):
    doc = fresh_fixture()
    _set(FOOTPRINT["id"], "width_m", 23)(doc)
    baseline = validate_value(json.loads(json.dumps(doc))).to_dict()
    random.Random(seed).shuffle(doc["entities"])
    assert validate_value(doc).to_dict() == baseline


def test_issues_are_sorted_by_path_then_code():
    doc = fresh_fixture()
    for member in doc["entities"]:
        if member["kind"] == "TimberMember":
            member["section_id"] = NEW_ID
    result = validate_value(doc)
    keys = [(i.path.encode("utf-16-be"), i.code) for i in result.issues]
    assert keys == sorted(keys) and len(keys) == 58
