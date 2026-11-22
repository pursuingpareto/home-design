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

from conftest import FIXTURE, FIXTURE_BYTES, entities_of, epath, fresh_fixture, index_of, regenerate, remove_openings
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


def _grid_fractions(axis, fractions):
    def mutate(d):
        for line, fraction in zip(_find(d, GRID["id"])[axis], fractions, strict=True):
            line["fraction"] = fraction

    return mutate


def _line_id(axis, k, new_id):
    return lambda d: _find(d, GRID["id"])[axis][k].__setitem__("id", new_id)


_BEAM_SECTION = next(e for e in entities_of(FIXTURE, "Section") if e["nominal_label"] == "8x12")


def _label_paths():
    # D049: sections ordered by id; the later one is reported, related to the first.
    first, later = sorted([SECTION_8X8, _BEAM_SECTION], key=lambda s: s["id"])
    return epath(later, "nominal_label"), (epath(first, "nominal_label"),)


def _member_with_key(key):
    return next(m for m in MEMBERS if m["generation_key"] == key)


STRAY = _member_with_key("frame/axis-x/y0/x0-x1/plane-L1/beam")
A_POST = _member_with_key("frame/x0/y0/level-0/post")
BEAM_SECTION_ID = FRAME["member_defaults"]["BEAM"]["section_id"]


def _shift_end(member, dx):
    def mutate(d):
        end = _find(d, member["id"])["end_m"]
        end[0] = end[0] + dx
    return mutate


def _swap_endpoints(member):
    def mutate(d):
        m = _find(d, member["id"])
        m["start_m"], m["end_m"] = m["end_m"], m["start_m"]
    return mutate


def _remove_member(member):
    """Remove a member and the connections that name it, so only the member is missing."""
    def mutate(d):
        gone = {e["id"] for e in d["entities"] if e["id"] == member["id"] or (e["kind"] == "Connection" and member["id"] in e["member_ids"])}
        d["entities"] = [e for e in d["entities"] if e["id"] not in gone]
        frame = _find(d, FRAME["id"])
        frame["member_ids"].remove(member["id"])
        frame["connection_ids"] = [i for i in frame["connection_ids"] if i not in gone]
    return mutate


WALLS = entities_of(FIXTURE, "Wall")
OPENINGS = entities_of(FIXTURE, "Opening")
WALL_SYSTEM = entities_of(FIXTURE, "WallSystem")[0]
STUD_INFILL = next(d for d in entities_of(FIXTURE, "AssemblyDefinition") if d["label"] == "stud-infill")


def _opening_on(wall_key):
    wall = next(w for w in WALLS if w["generation_key"] == wall_key)
    return next(o for o in OPENINGS if o["wall_id"] == wall["id"])


def _second_opening(wall_key):
    """A copy of a wall's opening at the same offset (D079)."""
    def mutate(d):
        d["entities"].append(dict(_find(d, _opening_on(wall_key)["id"]), id=NEW_ID))
        system = _find(d, WALL_SYSTEM["id"])
        system["opening_ids"] = sorted([*system["opening_ids"], NEW_ID])
    return mutate


def _stud_girts(count):
    def mutate(d):
        _find(d, WALL_SYSTEM["id"])["default_assembly_definition_id"] = STUD_INFILL["id"]
        _find(d, STUD_INFILL["id"])["layers"][2]["framing"]["girt_count"] = count
    return mutate


def _v3_cases() -> list[Case]:
    """MODEL-006 §11 item 3: the version 3 codes, from test_walls_model's minimal mutations."""
    from test_walls_model import CASES as WALL_CASES

    def build_case(fn):
        def build():
            doc = fresh_fixture()
            fn(doc)
            return validate_value(doc)
        return build

    cases = []
    for name, fn in sorted(WALL_CASES.items()):
        code, path, related = fn(fresh_fixture())
        top = UC if codes.CATALOG[code] is codes.Stage.DOMAIN else VF
        cases.append(Case(f"m006-{name}", build_case(fn), top, [Expect(code, path, tuple(sorted(related, key=lambda p: p.encode("utf-16-be"))))]))
    return cases


CONNECTIONS = entities_of(FIXTURE, "Connection")
A_CONNECTION = next(c for c in CONNECTIONS if c["generation_key"] == "connection/post-beam/frame/x0/y0/level-0/post/frame/axis-x/y0/x0-x1/plane-L1/beam")


def _remove_connection(connection):
    def mutate(d):
        d["entities"] = [e for e in d["entities"] if e["id"] != connection["id"]]
        _find(d, FRAME["id"])["connection_ids"].remove(connection["id"])
    return mutate


def _add_member(key):
    def mutate(d):
        d["entities"].append(dict(_find(d, A_POST["id"]), id=NEW_ID, generation_key=key))
        frame = _find(d, FRAME["id"])
        keys = {e["id"]: e["generation_key"] for e in d["entities"] if e["kind"] == "TimberMember"}
        frame["member_ids"] = sorted([*frame["member_ids"], NEW_ID], key=lambda i: keys[i])
    return mutate


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


def _params(**values):
    return lambda d: _find(d, FRAME["id"])["parameters"].update(values)


BEAM_AT_POST = _member_with_key("frame/axis-x/y0/x0-x1/plane-L1/beam")


def _add_connection(*, member_ids=None, junction_class="post-beam", connection_type="PEGGED_MORTISE_TENON",
                    key="connection/test", listed=True):
    def mutate(d):
        d["entities"].append({
            "id": NEW_ID, "kind": "Connection", "schema_version": 1,
            "junction_class": junction_class, "connection_type": connection_type,
            "member_ids": member_ids if member_ids is not None else [A_POST["id"], BEAM_AT_POST["id"]],
            "location_m": [0.0, 0.0, 3.048], "generation_key": key,
        })
        if listed:
            _find(d, FRAME["id"])["connection_ids"].append(NEW_ID)
    return mutate


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
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(GRID, "x_lines"), (epath(FOOTPRINT, "width_m"),))], only=True),
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
    doc_case("11-fractions-out-of-order", _grid_fractions("x_lines", [0.0, 2 / 3, 1 / 3, 1.0]), VF,
             [Expect(codes.NOT_STRICTLY_ASCENDING, epath(GRID, "x_lines", 2, "fraction"))], only=True),
    doc_case("12-missing-grid-endpoint", lambda d: _find(d, GRID["id"])["y_lines"].pop(), VF,
             [Expect(codes.GRID_ENDPOINT_MISSING, epath(GRID, "y_lines"))], only=True),
    doc_case("13-model-schema-version-1-retired", lambda d: d.__setitem__("model_schema_version", 1), VF,
             [Expect(codes.UNSUPPORTED_SCHEMA_VERSION, "model_schema_version")], only=True),
    # MODEL-005 §4.1: record versions are per kind (FrameSystem 2, Footprint 1).
    doc_case("13b-record-version-per-kind", _set(FRAME["id"], "schema_version", 1), VF,
             [Expect(codes.UNSUPPORTED_SCHEMA_VERSION, epath(FRAME, "schema_version"))], only=True),
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
    # Parameter-only edits leave members stale; stage 5 (D046) would then fail, so valid
    # cases regenerate members first.
    # 4'-0" bays need short braces: twice the leg must fit the shortest bay (MODEL-005 §5.2).
    # MODEL-006 §10: 4' bays leave no room for any D072 window, so the D032 bound is checked on the
    # house without its openings; 29b records the v3 house's own (changed) outcome.
    doc_case("29-width-inside-epsilon", lambda d: (remove_openings(d), _set(FOOTPRINT["id"], "width_m", 3.6576 - 5e-7)(d), _params(knee_brace_leg_m=0.4572)(d), regenerate(d)), None, [], only=True),
    doc_case("29b-width-inside-epsilon-windows-do-not-fit", lambda d: (_set(FOOTPRINT["id"], "width_m", 3.6576 - 5e-7)(d), _params(knee_brace_leg_m=0.4572)(d), regenerate(d)), UC,
             [Expect(codes.OPENING_OUTSIDE_WALL, epath(_opening_on("wall/axis-x/y2/x1-x2/level-1"), "width_m"))]),
    doc_case("30-width-outside-epsilon", lambda d: (remove_openings(d), _set(FOOTPRINT["id"], "width_m", 3.6576 - 2e-6)(d), _params(knee_brace_leg_m=0.4572)(d)), UC,
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
    doc_case("36-unknown-kind", _set(SECTION_8X8["id"], "kind", "AssemblyInstance"), VF,
             [Expect(codes.UNKNOWN_KIND, epath(SECTION_8X8, "kind"))], only=True),
    doc_case("37-second-footprint", _second_footprint, VF,
             [Expect(codes.UNREFERENCED_ENTITY, f"entities[{NEW_ID}]")], only=True),
    doc_case("38-duplicate-generation-key", _set(MEMBER_B["id"], "generation_key", MEMBER_A["generation_key"]), VF,
             [Expect(codes.DUPLICATE_GENERATION_KEY, epath(MEMBER_B, "generation_key"), (epath(MEMBER_A, "generation_key"),))]),
    doc_case("39-third-level", _third_level, UC,
             [Expect(codes.ENTITY_COUNT, "building.level_ids")], only=True),
    doc_case("40-retired-rafter-role", _set(MEMBERS[0]["id"], "member_role", "RAFTER"), VF,
             [Expect(codes.INVALID_ENUM, epath(MEMBERS[0], "member_role"))], only=True),
    # D037 mapping row: level elevations
    doc_case("d037-elevations-not-ascending", _set(LEVEL1["id"], "elevation_m", 0.0), VF,
             [Expect(codes.NOT_STRICTLY_ASCENDING, epath(LEVEL1, "elevation_m"), (epath(LEVEL0, "elevation_m"),)),
              Expect(codes.STORY_HEIGHT_MISMATCH, epath(LEVEL0, "story_height_m"), (epath(LEVEL1, "elevation_m"),))]),
    # D039: per-role member defaults on FrameSystem
    doc_case("d039-dangling-default-section",
             lambda d: _find(d, FRAME["id"])["member_defaults"]["POST"].__setitem__("section_id", NEW_ID), VF,
             [Expect(codes.DANGLING_REFERENCE, epath(FRAME, "member_defaults", "POST", "section_id"))], only=True),
    doc_case("d039-default-material-wrong-kind",
             lambda d: _find(d, FRAME["id"])["member_defaults"]["BEAM"].__setitem__("material_id", SECTION_8X8["id"]), VF,
             [Expect(codes.WRONG_REFERENCE_KIND, epath(FRAME, "member_defaults", "BEAM", "material_id"))], only=True),
    doc_case("d039-missing-beam-default", lambda d: _find(d, FRAME["id"])["member_defaults"].pop("BEAM"), VF,
             [Expect(codes.MISSING_ROLE_DEFAULT, epath(FRAME, "member_defaults"))], only=True),
    doc_case("d039-invalid-role-key",
             lambda d: _find(d, FRAME["id"])["member_defaults"].__setitem__("COLUMN", dict(FRAME["member_defaults"]["POST"])), VF,
             [Expect(codes.INVALID_ENUM, epath(FRAME, "member_defaults", "COLUMN"))], only=True),
    doc_case("d039-member-defaults-absent", lambda d: _find(d, FRAME["id"]).pop("member_defaults"), VF,
             [Expect(codes.MISSING_FIELD, epath(FRAME, "member_defaults"))], only=True),
    doc_case("d039-incomplete-role-default",
             lambda d: _find(d, FRAME["id"])["member_defaults"]["POST"].pop("material_id"), VF,
             [Expect(codes.MISSING_FIELD, epath(FRAME, "member_defaults", "POST", "material_id"))], only=True),
    # D042: stable grid-line IDs
    doc_case("d042-wrong-axis-letter", _line_id("x_lines", 1, "y1"), VF,
             [Expect(codes.INVALID_LINE_ID, epath(GRID, "x_lines", 1, "id"))], only=True),
    doc_case("d042-leading-zero", _line_id("y_lines", 1, "y01"), VF,
             [Expect(codes.INVALID_LINE_ID, epath(GRID, "y_lines", 1, "id"))], only=True),
    doc_case("d042-duplicate-line-id", _line_id("x_lines", 2, "x1"), VF,
             [Expect(codes.DUPLICATE_LINE_ID, epath(GRID, "x_lines", 2, "id"), (epath(GRID, "x_lines", 1, "id"),))], only=True),
    doc_case("d042-line-ids-need-not-be-sequential", lambda d: (_line_id("x_lines", 1, "x9")(d), regenerate(d)), None, [], only=True),
    doc_case("d042-renamed-line-without-regeneration", _line_id("x_lines", 1, "x9"), VF,
             [Expect(codes.MISSING_GENERATED_MEMBER, epath(FRAME, "member_ids")),
              Expect(codes.UNEXPECTED_MEMBER, epath(_member_with_key("frame/x1/y0/level-0/post"), "generation_key"))]),
    # TIMBER-001 / D046: stage 5 conformance
    doc_case("t001-endpoint-inside-epsilon", _shift_end(STRAY, 5e-7), None, [], only=True),
    doc_case("t001-endpoint-outside-epsilon", _shift_end(STRAY, 2e-6), VF,
             [Expect(codes.MEMBER_GEOMETRY_MISMATCH, epath(STRAY, "end_m"))], only=True),
    doc_case("t001-swapped-endpoints", _swap_endpoints(STRAY), VF,
             [Expect(codes.MEMBER_GEOMETRY_MISMATCH, epath(STRAY, "start_m")),
              Expect(codes.MEMBER_GEOMETRY_MISMATCH, epath(STRAY, "end_m"))], only=True),
    doc_case("t001-missing-member", _remove_member(STRAY), VF,
             [Expect(codes.MISSING_GENERATED_MEMBER, epath(FRAME, "member_ids"))], only=True),
    doc_case("t001-unexpected-member", _add_member("frame/x9/y0/level-0/post"), VF,
             [Expect(codes.UNEXPECTED_MEMBER, f"entities[{NEW_ID}].generation_key")], only=True),
    doc_case("t001-post-with-beam-section", _set(A_POST["id"], "section_id", BEAM_SECTION_ID), VF,
             [Expect(codes.MEMBER_ASSIGNMENT_MISMATCH, epath(A_POST, "section_id"),
                     (epath(FRAME, "member_defaults", "POST", "section_id"),))], only=True),
    doc_case("t001-post-labelled-beam", _set(A_POST["id"], "member_role", "BEAM"), VF,
             [Expect(codes.MEMBER_ASSIGNMENT_MISMATCH, epath(A_POST, "member_role"))], only=True),
    doc_case("t001-stale-members-outside-domain", _set(FOOTPRINT["id"], "width_m", 30), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FOOTPRINT, "width_m"))]),
    # MODEL-005 §5: frame parameters (stage 1 types, stage 3 physical checks, stage 4 bounds and brace fit)
    doc_case("m005-purlins-not-integer", _params(purlins_per_slope=2.5), VF,
             [Expect(codes.INTEGER_OUT_OF_RANGE, epath(FRAME, "parameters", "purlins_per_slope"))], only=True),
    doc_case("m005-brace-flag-not-boolean", _params(knee_braces_eave="yes"), VF,
             [Expect(codes.WRONG_TYPE, epath(FRAME, "parameters", "knee_braces_eave"))], only=True),
    doc_case("m005-parameters-missing-key", lambda d: _find(d, FRAME["id"])["parameters"].pop("joist_spacing_m"), VF,
             [Expect(codes.MISSING_FIELD, epath(FRAME, "parameters", "joist_spacing_m"))], only=True),
    doc_case("m005-zero-spacing", _params(joist_spacing_m=0.0), VF,
             [Expect(codes.OUT_OF_RANGE, epath(FRAME, "parameters", "joist_spacing_m"))], only=True),
    doc_case("m005-negative-purlins", _params(purlins_per_slope=-1), VF,
             [Expect(codes.OUT_OF_RANGE, epath(FRAME, "parameters", "purlins_per_slope"))], only=True),
    doc_case("m005-spacing-too-wide", _params(joist_spacing_m=1.2192 + 2e-6), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FRAME, "parameters", "joist_spacing_m"))], only=True),
    doc_case("m005-spacing-at-bound", lambda d: (_params(joist_spacing_m=0.3048)(d), regenerate(d)), None, [], only=True),
    doc_case("m005-five-purlins", _params(purlins_per_slope=5), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FRAME, "parameters", "purlins_per_slope"))], only=True),
    doc_case("m005-brace-leg-too-short", _params(knee_brace_leg_m=0.4572 - 2e-6), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FRAME, "parameters", "knee_brace_leg_m"))], only=True),
    # MODEL-006 §10: a 5' bay fits no D072 window, so the brace-fit cases run without openings.
    doc_case("m005-braces-do-not-fit", lambda d: (remove_openings(d), _grid_fractions("x_lines", [0.0, 0.5, 0.5 + 5 * 0.3048 / 10.9728, 1.0])(d)), UC,
             [Expect(codes.OUT_OF_SUPPORTED_RANGE, epath(FRAME, "parameters", "knee_brace_leg_m"),
                     tuple(sorted((epath(FOOTPRINT, "width_m"), epath(GRID, "x_lines")), key=lambda s: s.encode("utf-16-be"))))], only=True),
    doc_case("m005-braces-off-need-no-fit",
             lambda d: (remove_openings(d), _grid_fractions("x_lines", [0.0, 0.5, 0.5 + 5 * 0.3048 / 10.9728, 1.0])(d),
                        _params(knee_braces_level_1=False, knee_braces_eave=False)(d), regenerate(d)), None, [], only=True),
    # MODEL-005 §4.4, §6: connections and connection types (D054)
    doc_case("m005-disallowed-default-type", lambda d: _find(d, FRAME["id"])["connection_defaults"].__setitem__("post-beam", "JOIST_HANGER"), UC,
             [Expect(codes.UNSUPPORTED_VALUE, epath(FRAME, "connection_defaults") + '["post-beam"]')], only=True),  # D036 quotes hyphenated keys
    doc_case("m005-unknown-junction-class", lambda d: _find(d, FRAME["id"])["connection_defaults"].__setitem__("post-girt", "BRIDLE"), VF,
             [Expect(codes.INVALID_ENUM, epath(FRAME, "connection_defaults") + '["post-girt"]')], only=True),
    doc_case("m005-missing-connection-default", lambda d: _find(d, FRAME["id"])["connection_defaults"].pop("brace"), VF,
             [Expect(codes.MISSING_CONNECTION_DEFAULT, epath(FRAME, "connection_defaults"))], only=True),
    doc_case("m005-self-connection", _add_connection(member_ids=[A_POST["id"], A_POST["id"]]), VF,
             [Expect(codes.SELF_CONNECTION, f"entities[{NEW_ID}].member_ids[1]", (f"entities[{NEW_ID}].member_ids[0]",))], only=True),
    doc_case("m005-connection-to-a-section", _add_connection(member_ids=[A_POST["id"], SECTION_8X8["id"]]), VF,
             [Expect(codes.WRONG_REFERENCE_KIND, f"entities[{NEW_ID}].member_ids[1]")], only=True),
    doc_case("m005-connection-not-listed", _add_connection(listed=False), VF,
             [Expect(codes.CONNECTION_SET_MISMATCH, epath(FRAME, "connection_ids"), (f"entities[{NEW_ID}]",))], only=True),
    doc_case("m005-connection-reuses-member-key", _add_connection(key=A_POST["generation_key"]), VF,
             [Expect(codes.DUPLICATE_GENERATION_KEY, f"entities[{NEW_ID}].generation_key", (epath(A_POST, "generation_key"),))]
             if NEW_ID > A_POST["id"] else
             [Expect(codes.DUPLICATE_GENERATION_KEY, epath(A_POST, "generation_key"), (f"entities[{NEW_ID}].generation_key",))], only=True),
    doc_case("m005-disallowed-connection-type", _add_connection(connection_type="HOUSED_DOVETAIL"), UC,
             [Expect(codes.UNSUPPORTED_VALUE, f"entities[{NEW_ID}].connection_type", (f"entities[{NEW_ID}].junction_class",))], only=True),
    doc_case("m005-connection-wrong-member-count", _add_connection(member_ids=[A_POST["id"]]), VF,
             [Expect(codes.WRONG_TYPE, f"entities[{NEW_ID}].member_ids")], only=True),
    # CONN-001 §12 test 8: connection conformance (D046, MODEL-005 §6.5) from minimal fixture mutations.
    doc_case("m005-unexpected-connection", _add_connection(), VF,
             [Expect(codes.UNEXPECTED_CONNECTION, f"entities[{NEW_ID}].generation_key")], only=True),
    doc_case("c001-missing-connection", _remove_connection(A_CONNECTION), VF,
             [Expect(codes.MISSING_GENERATED_CONNECTION, epath(FRAME, "connection_ids"))], only=True),
    doc_case("c001-location-inside-epsilon", lambda d: _find(d, A_CONNECTION["id"])["location_m"].__setitem__(2, A_CONNECTION["location_m"][2] + 5e-7), None, [], only=True),
    doc_case("c001-moved-location", lambda d: _find(d, A_CONNECTION["id"])["location_m"].__setitem__(2, A_CONNECTION["location_m"][2] + 2e-6), VF,
             [Expect(codes.CONNECTION_GEOMETRY_MISMATCH, epath(A_CONNECTION, "location_m"))], only=True),
    doc_case("c001-wrong-junction-class", _set(A_CONNECTION["id"], "junction_class", "brace"), VF,
             [Expect(codes.CONNECTION_ASSIGNMENT_MISMATCH, epath(A_CONNECTION, "junction_class"))], only=True),
    doc_case("c001-swapped-members", _set(A_CONNECTION["id"], "member_ids", A_CONNECTION["member_ids"][::-1]), VF,
             [Expect(codes.CONNECTION_ASSIGNMENT_MISMATCH, epath(A_CONNECTION, "member_ids"))], only=True),
    doc_case("c001-engineered-type-on-one-connection", _set(A_CONNECTION["id"], "connection_type", "STEEL_KNIFE_PLATE"), VF,
             [Expect(codes.CONNECTION_ASSIGNMENT_MISMATCH, epath(A_CONNECTION, "connection_type"),
                     (epath(FRAME, "connection_defaults") + '["post-beam"]',))], only=True),
    # D049: unique section labels
    doc_case("d049-duplicate-section-label", _set(_BEAM_SECTION["id"], "nominal_label", "8x8"), VF,
             [Expect(codes.DUPLICATE_SECTION_LABEL, *_label_paths())], only=True),
    # D036 path forms: quoted keys
    doc_case("d036-quoted-entity-key", _set(FOOTPRINT["id"], "a.b", 1), VF,
             [Expect(codes.UNKNOWN_FIELD, f'entities[{FOOTPRINT["id"]}]["a.b"]')], only=True),
    doc_case("d036-quoted-root-key", lambda d: d.__setitem__("x-y", 1), VF,
             [Expect(codes.UNKNOWN_FIELD, '["x-y"]')], only=True),
    # MODEL-006 §5: the fit rules
    doc_case("m006-opening-outside-wall", _set(_opening_on("wall/axis-y/x3/y1-y2/level-1")["id"], "width_m", 6.0), UC,
             [Expect(codes.OPENING_OUTSIDE_WALL, epath(_opening_on("wall/axis-y/x3/y1-y2/level-1"), "width_m"))]),
    doc_case("m006-opening-crosses-brace", _set(_opening_on("wall/axis-y/x3/y1-y2/level-1")["id"], "offset_m", 0.3 + 0.0381), UC,
             [Expect(codes.OPENING_CROSSES_BRACE, epath(_opening_on("wall/axis-y/x3/y1-y2/level-1"), "offset_m"))], only=True),
    doc_case("m006-openings-overlap", _second_opening("wall/axis-y/x3/y1-y2/level-1"), UC,
             [Expect(codes.OPENINGS_OVERLAP, f'entities[{max(_opening_on("wall/axis-y/x3/y1-y2/level-1")["id"], NEW_ID)}].offset_m',
                     (f'entities[{min(_opening_on("wall/axis-y/x3/y1-y2/level-1")["id"], NEW_ID)}].offset_m',))], only=True),
    doc_case("m006-girt-crosses-brace", _stud_girts(4), UC,
             [Expect(codes.GIRT_CROSSES_BRACE, epath(STUD_INFILL, "layers", 2, "framing", "girt_count"))]),
    doc_case("m006-unexpected-wall", lambda d: _find(d, WALL_SYSTEM["wall_ids"][-1]).__setitem__("generation_key", _find(d, WALL_SYSTEM["wall_ids"][-1])["generation_key"] + "x"), VF,
             [Expect(codes.UNEXPECTED_WALL, f"entities[{WALL_SYSTEM['wall_ids'][-1]}].generation_key")]),
    *_v3_cases(),
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


# Codes raised only outside snapshot validation, with the test that exercises them. Since
# CONN-001 every connection conformance code is reached by a fixture mutation above.
NON_SNAPSHOT_CODES = {
    codes.DUPLICATE_PRICE_KEY: "test_estimating.py::test_invalid_books_are_rejected",
    codes.PRICE_UNIT_MISMATCH: "test_estimating.py::test_invalid_books_are_rejected",
}


def test_every_catalog_code_is_exercised():
    exercised = {e.code for case in CASES for e in case.expect}
    assert exercised | set(NON_SNAPSHOT_CODES) == set(codes.CATALOG)
    assert not exercised & set(NON_SNAPSHOT_CODES)


def test_missing_role_defaults_report_each_role():
    doc = fresh_fixture()
    _find(doc, FRAME["id"])["member_defaults"] = {}
    result = validate_value(doc)
    assert [(i.code, i.path, i.value) for i in result.issues] == [
        (codes.MISSING_ROLE_DEFAULT, epath(FRAME, "member_defaults"), role)
        for role in sorted(("POST", "BEAM", "SILL", "FLOOR_JOIST", "PRINCIPAL_RAFTER", "PURLIN", "KNEE_BRACE"))
    ]


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
    assert keys == sorted(keys) and len(keys) == 193
