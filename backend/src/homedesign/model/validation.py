"""Five-stage snapshot validation (building-model.md §6; D035, D046).

Stages run in order; a later stage runs only if all earlier stages passed, and
each stage reports every issue it finds. Validation is a pure function of its
input: no I/O, clock, or randomness, and independent of the order of ``entities``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from . import codes, limits
from . import connections as connection_catalog
from .codes import Stage
from .paths import UUID_PATTERN, EntityAddresser, Step, render
from .schema import ENTITY_KINDS, TIMESTAMP_PATTERN, X_LINE_ID_PATTERN, Y_LINE_ID_PATTERN, Snapshot
from .strict_json import DuplicateKeyDict, NonFinite, check_depth, parse


@dataclass(frozen=True)
class Issue:
    """One error detail (interfaces.md §7; D036 paths; D037 related_paths)."""

    path: str
    code: str
    message: str
    value: Any = None
    related_paths: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"path": self.path, "code": self.code, "message": self.message}
        if self.value is not None:
            result["value"] = self.value
        if self.related_paths:
            result["related_paths"] = list(self.related_paths)
        return result


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    code: str | None
    issues: tuple[Issue, ...] = ()
    snapshot: Snapshot | None = field(default=None, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "code": self.code,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be", errors="surrogatepass")


def _scalar(value: Any) -> Any:
    """Return value if it may be echoed in an issue (finite scalar), else None."""
    if isinstance(value, bool) or isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return value if math.isfinite(value) else None
        except OverflowError:
            return None
    return None


class _Collector:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def add(
        self,
        path: str,
        code: str,
        message: str,
        value: Any = None,
        related: Sequence[str] = (),
    ) -> None:
        related_unique = sorted({p for p in related if p != path}, key=_utf16)
        self.issues.append(Issue(path, code, message, _scalar(value), tuple(related_unique)))

    def result(self, stage: Stage) -> ValidationResult | None:
        if not self.issues:
            return None
        for issue in self.issues:
            assert codes.CATALOG[issue.code] is stage, (issue.code, stage)
        ordered = sorted(
            self.issues,
            key=lambda i: (_utf16(i.path), i.code, i.message, [_utf16(p) for p in i.related_paths]),
        )
        return ValidationResult(False, stage.top_level_code, tuple(ordered))


# ---------------------------------------------------------------------------
# Public entry points


def validate_bytes(
    data: bytes,
    *,
    max_bytes: int = limits.DEFAULT_MAX_BYTES,
    max_depth: int = limits.DEFAULT_MAX_DEPTH,
) -> ValidationResult:
    """Parse and validate snapshot JSON bytes. Never raises."""
    outcome = parse(data, max_bytes=max_bytes, max_depth=max_depth)
    if outcome.fatal is not None:
        issue = Issue("", outcome.fatal.code, outcome.fatal.message)
        return ValidationResult(False, codes.VALIDATION_FAILED, (issue,))
    return _validate_parsed(outcome.value, max_depth)


def validate_value(value: Any, *, max_depth: int = limits.DEFAULT_MAX_DEPTH) -> ValidationResult:
    """Validate an already-parsed JSON value (for example, a candidate snapshot)."""
    depth_error = check_depth(value, max_depth)
    if depth_error is not None:
        return ValidationResult(
            False, codes.VALIDATION_FAILED, (Issue("", depth_error.code, depth_error.message),)
        )
    return _validate_parsed(value, max_depth)


def _validate_parsed(value: Any, max_depth: int) -> ValidationResult:
    addresser = EntityAddresser.from_raw(value)
    syntactic, snapshot = _stage_syntactic(value, addresser)
    if syntactic is not None:
        return syntactic
    assert snapshot is not None
    for stage_check in (_stage_referential, _stage_geometric, _stage_domain, _stage_conformance):
        failed = stage_check(snapshot)
        if failed is not None:
            return failed
    return ValidationResult(True, None, (), snapshot)


# ---------------------------------------------------------------------------
# Stage 1 — syntactic


def _scan_raw(value: Any, steps: list[str | int], addresser: EntityAddresser, out: _Collector, flagged: set[str]) -> None:
    """Report parser-level problems: duplicate keys, non-finite numbers, lone surrogates."""
    if isinstance(value, NonFinite) or (isinstance(value, float) and not math.isfinite(value)):
        path = addresser.path(steps)
        flagged.add(path)
        out.add(path, codes.NON_FINITE_NUMBER, "Numbers must be finite.")
        return
    if isinstance(value, str):
        if _has_surrogate(value):
            path = addresser.path(steps)
            flagged.add(path)
            out.add(path, codes.MALFORMED_JSON, "String contains a lone surrogate (not I-JSON).")
        return
    if isinstance(value, dict):
        if isinstance(value, DuplicateKeyDict):
            for key in value.duplicate_keys:
                out.add(addresser.path([*steps, key]), codes.DUPLICATE_KEY, "Object key appears more than once.")
        for key, child in value.items():
            if isinstance(key, str) and _has_surrogate(key):
                path = addresser.path(steps)
                flagged.add(path)
                out.add(path, codes.MALFORMED_JSON, "Object key contains a lone surrogate (not I-JSON).")
                continue
            _scan_raw(child, [*steps, key], addresser, out, flagged)
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_raw(child, [*steps, index], addresser, out, flagged)


def _has_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(char) <= 0xDFFF for char in text)


_PYDANTIC_CODE = {
    "missing": codes.MISSING_FIELD,
    "extra_forbidden": codes.UNKNOWN_FIELD,
    "union_tag_invalid": codes.UNKNOWN_KIND,
    "union_tag_not_found": codes.MISSING_FIELD,
    "literal_error": codes.INVALID_ENUM,
    "enum": codes.INVALID_ENUM,
    "invalid_timestamp": codes.INVALID_TIMESTAMP,
    "integer_out_of_range": codes.INTEGER_OUT_OF_RANGE,
    "less_than_equal": codes.INTEGER_OUT_OF_RANGE,
    "greater_than_equal": codes.INTEGER_OUT_OF_RANGE,
    "unsupported_schema_version": codes.UNSUPPORTED_SCHEMA_VERSION,
    "finite_number": codes.NON_FINITE_NUMBER,
}

_MESSAGES = {
    codes.MISSING_FIELD: "Required field is missing.",
    codes.UNKNOWN_FIELD: "Field is not defined by the schema.",
    codes.UNKNOWN_KIND: "Record kind is not a model schema version 2 entity kind.",
    codes.INVALID_ENUM: "Value is not one of the allowed values.",
    codes.INVALID_UUID: "Must be a lowercase, hyphenated UUID.",
    codes.INVALID_TIMESTAMP: "Must be an RFC 3339 UTC timestamp ending in Z.",
    codes.INVALID_LINE_ID: "Grid line IDs must be x<n> in x_lines and y<n> in y_lines (D042).",
    codes.INTEGER_OUT_OF_RANGE: "Must be an integer within ±(2^53 − 1).",
    codes.UNSUPPORTED_SCHEMA_VERSION: "Schema version is not supported.",
    codes.NON_FINITE_NUMBER: "Numbers must be finite.",
    codes.WRONG_TYPE: "Value has the wrong type or shape.",
}


def code_for_pydantic_error(error: dict[str, Any]) -> str:
    """Map a Pydantic error to a D035 detail code (shared by snapshot and command validation)."""
    error_type = error["type"]
    code = _PYDANTIC_CODE.get(error_type, codes.WRONG_TYPE)
    if error_type == "string_pattern_mismatch":
        pattern = (error.get("ctx") or {}).get("pattern")
        if pattern == UUID_PATTERN:
            code = codes.INVALID_UUID
        elif pattern == TIMESTAMP_PATTERN:
            code = codes.INVALID_TIMESTAMP
        elif pattern in (X_LINE_ID_PATTERN, Y_LINE_ID_PATTERN):
            code = codes.INVALID_LINE_ID
    return code


def message_for(code: str) -> str:
    return _MESSAGES.get(code, "Invalid value.")


def _pydantic_issue(error: dict[str, Any], addresser: EntityAddresser) -> tuple[str, str, Any]:
    error_type = error["type"]
    loc = [step for step in error["loc"]]
    # Drop the discriminator tag that Pydantic inserts after an entity index.
    if len(loc) >= 3 and loc[0] == "entities" and isinstance(loc[1], int) and loc[2] in ENTITY_KINDS:
        del loc[2]
    # Pydantic marks errors in a mapping's key with a trailing "[key]" step.
    invalid_key = bool(loc) and loc[-1] == "[key]"
    if invalid_key:
        del loc[-1]
    raw_input = error.get("input")
    if error_type in ("union_tag_invalid", "union_tag_not_found"):
        loc.append("kind")
        raw_input = raw_input.get("kind") if isinstance(raw_input, dict) else None
    code = code_for_pydantic_error(error)
    if error_type == "literal_error" and loc and loc[-1] == "kind" and not invalid_key:
        code = codes.UNKNOWN_KIND
    if code == codes.MISSING_FIELD and error_type == "missing":
        raw_input = None  # Pydantic reports the parent object as input
    return addresser.path(loc), code, raw_input


def _stage_syntactic(value: Any, addresser: EntityAddresser) -> tuple[ValidationResult | None, Snapshot | None]:
    out = _Collector()
    flagged: set[str] = set()
    _scan_raw(value, [], addresser, out, flagged)
    snapshot: Snapshot | None = None
    try:
        snapshot = Snapshot.model_validate(value)
    except ValidationError as exc:
        seen: set[tuple[str, str]] = set()
        for error in exc.errors(include_url=False):
            path, code, raw_input = _pydantic_issue(error, addresser)
            if path in flagged or (path, code) in seen:
                continue  # already reported by the raw scan, or a duplicate
            seen.add((path, code))
            out.add(path, code, _MESSAGES.get(code, "Invalid value."), raw_input)
    result = out.result(Stage.SYNTACTIC)
    return result, (snapshot if result is None else None)


# ---------------------------------------------------------------------------
# Shared helpers for stages 2–4


class _Index:
    """Lookups over a syntactically valid snapshot."""

    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot = snapshot
        self.addresser = EntityAddresser(snapshot.building.id, [e.id for e in snapshot.entities])
        self.by_id: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
        self.by_id[snapshot.building.id].append(("building", snapshot.building))
        for index, entity in enumerate(snapshot.entities):
            self.by_id[entity.id].append((index, entity))

    def locator_steps(self, locator: Any) -> list[Step]:
        return ["building"] if locator == "building" else ["entities", self.addresser.entity(locator)]

    def path(self, locator: Any, *rest: str | int) -> str:
        return render([*self.locator_steps(locator), *rest])

    def resolve(self, record_id: str, kind: str) -> tuple[Any, Any] | None:
        """First record with this ID and kind, or None."""
        for locator, record in self.by_id.get(record_id, []):
            if record.kind == kind:
                return locator, record
        return None

    def of_kind(self, kind: str) -> list[tuple[int, Any]]:
        return [(i, e) for i, e in enumerate(self.snapshot.entities) if e.kind == kind]


# ---------------------------------------------------------------------------
# Stage 2 — referential


def _stage_referential(snapshot: Snapshot) -> ValidationResult | None:
    out = _Collector()
    idx = _Index(snapshot)
    building = snapshot.building

    for record_id, occurrences in idx.by_id.items():
        if len(occurrences) > 1:
            first_path = idx.path(occurrences[0][0])
            for locator, _ in occurrences[1:]:
                out.add(idx.path(locator), codes.DUPLICATE_ID, "ID is used by more than one record.", record_id, [first_path])

    for index, entity in idx.of_kind("Building"):
        out.add(idx.path(index), codes.BUILDING_IN_ENTITIES, "The Building record belongs in `building`, not `entities`.")

    def check_ref(path: str, ref_id: str, expected: str) -> None:
        candidates = idx.by_id.get(ref_id, [])
        if not candidates:
            out.add(path, codes.DANGLING_REFERENCE, f"Referenced {expected} does not exist.", ref_id)
        elif not any(record.kind == expected for _, record in candidates):
            out.add(path, codes.WRONG_REFERENCE_KIND, f"Referenced record is not a {expected}.", ref_id)

    check_ref(idx.path("building", "footprint_id"), building.footprint_id, "Footprint")
    for k, level_id in enumerate(building.level_ids):
        check_ref(idx.path("building", "level_ids", k), level_id, "Level")
    check_ref(idx.path("building", "roof_id"), building.roof_id, "GableRoof")
    check_ref(idx.path("building", "frame_system_id"), building.frame_system_id, "FrameSystem")
    for index, frame in idx.of_kind("FrameSystem"):
        check_ref(idx.path(index, "grid_id"), frame.grid_id, "TimberGrid")
        for k, member_id in enumerate(frame.member_ids):
            check_ref(idx.path(index, "member_ids", k), member_id, "TimberMember")
        # D039: per-role section and material defaults.
        for role, default in frame.member_defaults.items():
            check_ref(idx.path(index, "member_defaults", role, "section_id"), default.section_id, "Section")
            check_ref(idx.path(index, "member_defaults", role, "material_id"), default.material_id, "Material")
        for k, connection_id in enumerate(frame.connection_ids):
            check_ref(idx.path(index, "connection_ids", k), connection_id, "Connection")
        grid_hit = idx.resolve(frame.grid_id, "TimberGrid")
        rule = _rule(grid_hit[1].generation_rule_version) if grid_hit is not None else None
        if rule is not None:
            for role in sorted(rule.generated_roles - frame.member_defaults.keys()):
                out.add(
                    idx.path(index, "member_defaults"),
                    codes.MISSING_ROLE_DEFAULT,
                    f"member_defaults needs a {role} entry: {rule.version} generates {role} members (D039).",
                    role,
                )
            # MODEL-005 §6.2: a connection type for every junction class the rule generates (D054).
            for junction_class in sorted(rule.generated_junction_classes - frame.connection_defaults.keys()):
                out.add(
                    idx.path(index, "connection_defaults"),
                    codes.MISSING_CONNECTION_DEFAULT,
                    f"connection_defaults needs a {junction_class} entry: {rule.version} generates {junction_class} junctions (D054).",
                    junction_class,
                )
    # D042: grid line IDs are unique per axis.
    for index, grid in idx.of_kind("TimberGrid"):
        for axis in ("x_lines", "y_lines"):
            first_seen: dict[str, int] = {}
            for k, line in enumerate(getattr(grid, axis)):
                if line.id in first_seen:
                    out.add(
                        idx.path(index, axis, k, "id"),
                        codes.DUPLICATE_LINE_ID,
                        "Grid line ID repeats within the axis.",
                        line.id,
                        [idx.path(index, axis, first_seen[line.id], "id")],
                    )
                else:
                    first_seen[line.id] = k
    for index, member in idx.of_kind("TimberMember"):
        check_ref(idx.path(index, "section_id"), member.section_id, "Section")
        check_ref(idx.path(index, "material_id"), member.material_id, "Material")
    # MODEL-005 §6.2: a connection joins two distinct existing members.
    for index, connection in idx.of_kind("Connection"):
        for k, member_id in enumerate(connection.member_ids):
            check_ref(idx.path(index, "member_ids", k), member_id, "TimberMember")
        if connection.member_ids[0] == connection.member_ids[1]:
            out.add(
                idx.path(index, "member_ids", 1),
                codes.SELF_CONNECTION,
                "A connection joins two different members.",
                connection.member_ids[1],
                [idx.path(index, "member_ids", 0)],
            )

    # D038: every Footprint, Level, GableRoof, TimberGrid, FrameSystem must be referenced.
    referenced_frames = {building.frame_system_id}
    referenced_grids = {
        frame.grid_id for _, frame in idx.of_kind("FrameSystem") if frame.id in referenced_frames
    }
    referenced = {
        "Footprint": {building.footprint_id},
        "Level": set(building.level_ids),
        "GableRoof": {building.roof_id},
        "FrameSystem": referenced_frames,
        "TimberGrid": referenced_grids,
    }
    for kind, ids in referenced.items():
        for index, entity in idx.of_kind(kind):
            if entity.id not in ids:
                out.add(idx.path(index), codes.UNREFERENCED_ENTITY, f"{kind} is not referenced by the building or frame system.")

    frame_hit = idx.resolve(building.frame_system_id, "FrameSystem")
    members = idx.of_kind("TimberMember")
    connections = idx.of_kind("Connection")
    if frame_hit is not None:
        frame_locator, frame = frame_hit
        # Members and connections are listed the same way: exactly the set, ascending by key (D030).
        for field, kind, records, code in (
            ("member_ids", "TimberMember", members, codes.MEMBER_SET_MISMATCH),
            ("connection_ids", "Connection", connections, codes.CONNECTION_SET_MISMATCH),
        ):
            listed = set(getattr(frame, field))
            unlisted = [index for index, record in records if record.id not in listed]
            if unlisted:
                out.add(
                    idx.path(frame_locator, field),
                    code,
                    f"{field} must list exactly the snapshot's {kind} records.",
                    related=[idx.path(index) for index in unlisted],
                )
            resolved = [idx.resolve(record_id, kind) for record_id in getattr(frame, field)]
            if all(hit is not None for hit in resolved):
                keys = [_utf16(hit[1].generation_key) for hit in resolved]  # type: ignore[index]
                if any(b <= a for a, b in zip(keys, keys[1:])):
                    out.add(idx.path(frame_locator, field), codes.ORDER_VIOLATION, f"{field} must be in strictly ascending generation_key order.")

    # MODEL-005 §6.2: keys are unique across members and connections, because IDs are minted from them (D041).
    by_key: dict[str, list[tuple[int, Any]]] = defaultdict(list)
    for index, record in (*members, *connections):
        by_key[record.generation_key].append((index, record))
    for group in by_key.values():
        if len(group) > 1:
            group = sorted(group, key=lambda item: item[1].id)
            first_path = idx.path(group[0][0], "generation_key")
            for index, record in group[1:]:
                out.add(idx.path(index, "generation_key"), codes.DUPLICATE_GENERATION_KEY, "generation_key is used by more than one member or connection.", record.generation_key, [first_path])

    # D049: section labels are unique (they key schedule aggregates and price-book rows).
    by_label: dict[str, list[tuple[int, Any]]] = defaultdict(list)
    for index, section in idx.of_kind("Section"):
        by_label[section.nominal_label].append((index, section))
    for group in by_label.values():
        if len(group) > 1:
            group = sorted(group, key=lambda item: item[1].id)
            first_path = idx.path(group[0][0], "nominal_label")
            for index, section in group[1:]:
                out.add(idx.path(index, "nominal_label"), codes.DUPLICATE_SECTION_LABEL, "Section labels must be unique within a project (D049).", section.nominal_label, [first_path])

    resolved_levels = [idx.resolve(level_id, "Level") for level_id in building.level_ids]
    if all(hit is not None for hit in resolved_levels):
        indexes = [hit[1].index for hit in resolved_levels]  # type: ignore[index]
        if any(b <= a for a, b in zip(indexes, indexes[1:])):
            out.add(idx.path("building", "level_ids"), codes.ORDER_VIOLATION, "level_ids must be in strictly ascending Level.index order.")

    return out.result(Stage.REFERENTIAL)


# ---------------------------------------------------------------------------
# Stages 3 and 4 operate on a referentially valid snapshot.


@dataclass(frozen=True)
class _Resolved:
    idx: _Index
    footprint: tuple[int, Any]
    levels: list[tuple[int, Any]]
    roof: tuple[int, Any]
    frame: tuple[int, Any]
    grid: tuple[int, Any]


def _resolve_all(snapshot: Snapshot) -> _Resolved:
    idx = _Index(snapshot)
    building = snapshot.building

    def must(record_id: str, kind: str) -> tuple[int, Any]:
        hit = idx.resolve(record_id, kind)
        assert hit is not None, "stage 2 guarantees references resolve"
        return hit

    frame = must(building.frame_system_id, "FrameSystem")
    return _Resolved(
        idx=idx,
        footprint=must(building.footprint_id, "Footprint"),
        levels=[must(level_id, "Level") for level_id in building.level_ids],
        roof=must(building.roof_id, "GableRoof"),
        frame=frame,
        grid=must(frame[1].grid_id, "TimberGrid"),
    )


def _stage_geometric(snapshot: Snapshot) -> ValidationResult | None:
    out = _Collector()
    r = _resolve_all(snapshot)
    idx = r.idx
    fp_loc, fp = r.footprint

    for name in ("width_m", "depth_m"):
        value = getattr(fp, name)
        if not value > 0:
            out.add(idx.path(fp_loc, name), codes.OUT_OF_RANGE, "Footprint dimensions must be greater than zero.", value)
    if any(coordinate != 0 for coordinate in fp.origin_m):
        out.add(idx.path(fp_loc, "origin_m"), codes.DATUM_MISMATCH, "Footprint origin must be [0, 0]: the building-local origin is the southwest corner (D026, D031).")

    levels = r.levels
    for loc, level in levels:
        if level.index < 0:
            out.add(idx.path(loc, "index"), codes.OUT_OF_RANGE, "Level index must not be negative.", level.index)
        if not level.story_height_m > 0:
            out.add(idx.path(loc, "story_height_m"), codes.OUT_OF_RANGE, "Story height must be greater than zero.", level.story_height_m)
    for (lower_loc, lower), (upper_loc, upper) in zip(levels, levels[1:]):
        if not upper.elevation_m > lower.elevation_m:
            out.add(idx.path(upper_loc, "elevation_m"), codes.NOT_STRICTLY_ASCENDING, "Level elevations must strictly increase with index.", upper.elevation_m, [idx.path(lower_loc, "elevation_m")])
        gap = upper.elevation_m - lower.elevation_m
        if abs(lower.story_height_m - gap) > limits.LENGTH_EPSILON_M:
            out.add(idx.path(lower_loc, "story_height_m"), codes.STORY_HEIGHT_MISMATCH, "Story height must equal the elevation gap to the next level (D033).", lower.story_height_m, [idx.path(upper_loc, "elevation_m")])
    if levels and levels[0][1].elevation_m != 0:
        out.add(idx.path(levels[0][0], "elevation_m"), codes.DATUM_MISMATCH, "Level 0 elevation must be exactly 0, the first-floor reference (D034).", levels[0][1].elevation_m)

    roof_loc, roof = r.roof
    if not 0 < roof.pitch_rad < math.pi / 2:
        out.add(idx.path(roof_loc, "pitch_rad"), codes.OUT_OF_RANGE, "Roof pitch must be between 0 and π/2 radians, exclusive.", roof.pitch_rad)
    if roof.eave_overhang_m < 0:
        out.add(idx.path(roof_loc, "eave_overhang_m"), codes.OUT_OF_RANGE, "Eave overhang must not be negative.", roof.eave_overhang_m)

    grid_loc, grid = r.grid
    for axis in ("x_lines", "y_lines"):
        fractions = [line.fraction for line in getattr(grid, axis)]
        if len(fractions) < 2 or fractions[0] != 0 or fractions[-1] != 1:
            out.add(idx.path(grid_loc, axis), codes.GRID_ENDPOINT_MISSING, "Grid line fractions must start at 0 and end at 1.")
        for k in range(1, len(fractions)):
            if not fractions[k] > fractions[k - 1]:
                out.add(idx.path(grid_loc, axis, k, "fraction"), codes.NOT_STRICTLY_ASCENDING, "Grid line fractions must strictly increase.", fractions[k])

    frame_loc, frame = r.frame
    params = frame.parameters
    for name in ("joist_spacing_m", "knee_brace_leg_m"):
        value = getattr(params, name)
        if not value > 0:
            out.add(idx.path(frame_loc, "parameters", name), codes.OUT_OF_RANGE, "Must be greater than zero.", value)
    if params.purlins_per_slope < 0:
        out.add(idx.path(frame_loc, "parameters", "purlins_per_slope"), codes.OUT_OF_RANGE, "Must not be negative.", params.purlins_per_slope)

    for index, member in idx.of_kind("TimberMember"):
        if math.dist(member.start_m, member.end_m) <= limits.LENGTH_EPSILON_M:
            out.add(idx.path(index), codes.ZERO_LENGTH_MEMBER, "Member axis length must exceed 1e-6 m.")
    for index, section in idx.of_kind("Section"):
        for name in ("actual_width_m", "actual_depth_m"):
            value = getattr(section, name)
            if not value > 0:
                out.add(idx.path(index, name), codes.OUT_OF_RANGE, "Section dimensions must be greater than zero.", value)
    for index, material in idx.of_kind("Material"):
        if material.density_kg_m3 is not None and not material.density_kg_m3 > 0:
            out.add(idx.path(index, "density_kg_m3"), codes.OUT_OF_RANGE, "Density, when known, must be greater than zero.", material.density_kg_m3)

    return out.result(Stage.GEOMETRIC)


# ---------------------------------------------------------------------------
# Stage 4 — domain (VS-01 supported configurations)


def _stage_domain(snapshot: Snapshot) -> ValidationResult | None:
    out = _Collector()
    r = _resolve_all(snapshot)
    idx = r.idx
    fp_loc, fp = r.footprint
    roof_loc, roof = r.roof
    grid_loc, grid = r.grid
    frame_loc, frame = r.frame

    # D031 — unsupported values (exact comparison; -0 equals 0).
    if fp.rotation_rad != 0:
        out.add(idx.path(fp_loc, "rotation_rad"), codes.UNSUPPORTED_VALUE, "VS-01 supports only unrotated footprints (D031).", fp.rotation_rad)
    if roof.ridge_axis != "X":
        out.add(idx.path(roof_loc, "ridge_axis"), codes.UNSUPPORTED_VALUE, "VS-01 supports only a ridge along X (D031).", roof.ridge_axis)
    if roof.ridge_offset_m != 0:
        out.add(idx.path(roof_loc, "ridge_offset_m"), codes.UNSUPPORTED_VALUE, "VS-01 supports only a centered ridge (D031).", roof.ridge_offset_m)

    # D034 — exactly two levels, indices 0 and 1, story heights 8'–14'.
    levels = r.levels
    if len(levels) != limits.LEVEL_COUNT:
        out.add(idx.path("building", "level_ids"), codes.ENTITY_COUNT, "VS-01 supports exactly two levels (D034).", len(levels))
    else:
        for position, (loc, level) in enumerate(levels):
            if level.index != position:
                out.add(idx.path(loc, "index"), codes.UNSUPPORTED_VALUE, "VS-01 level indices must be exactly 0 and 1 (D034).", level.index)
    for loc, level in levels:
        if not limits.within(level.story_height_m, limits.STORY_HEIGHT_MIN_M, limits.STORY_HEIGHT_MAX_M, limits.LENGTH_EPSILON_M):
            out.add(idx.path(loc, "story_height_m"), codes.OUT_OF_SUPPORTED_RANGE, "Story height must be between 8'-0\" and 14'-0\" (D034).", level.story_height_m)

    # D032 — footprint, roof, grid bounds.
    for name in ("width_m", "depth_m"):
        value = getattr(fp, name)
        if not limits.within(value, limits.FOOTPRINT_MIN_M, limits.FOOTPRINT_MAX_M, limits.LENGTH_EPSILON_M):
            out.add(idx.path(fp_loc, name), codes.OUT_OF_SUPPORTED_RANGE, "Footprint dimensions must be between 12'-0\" and 80'-0\" (D032).", value)
    if not limits.within(roof.pitch_rad, limits.PITCH_MIN_RAD, limits.PITCH_MAX_RAD, limits.ANGLE_EPSILON_RAD):
        out.add(idx.path(roof_loc, "pitch_rad"), codes.OUT_OF_SUPPORTED_RANGE, "Roof pitch must be between 3/12 and 12/12 (D032).", roof.pitch_rad)
    if roof.eave_overhang_m > limits.EAVE_OVERHANG_MAX_M + limits.LENGTH_EPSILON_M:
        out.add(idx.path(roof_loc, "eave_overhang_m"), codes.OUT_OF_SUPPORTED_RANGE, "Eave overhang must not exceed 3'-0\" (D032).", roof.eave_overhang_m)

    for axis, length_name in (("x_lines", "width_m"), ("y_lines", "depth_m")):
        fractions = [line.fraction for line in getattr(grid, axis)]
        if not limits.GRID_STATIONS_MIN <= len(fractions) <= limits.GRID_STATIONS_MAX:
            out.add(idx.path(grid_loc, axis), codes.OUT_OF_SUPPORTED_RANGE, "A grid axis must have 2 to 7 stations (D032).", len(fractions))
            continue
        length = getattr(fp, length_name)
        bays = [length * (b - a) for a, b in zip(fractions, fractions[1:])]
        if any(not limits.within(bay, limits.BAY_MIN_M, limits.BAY_MAX_M, limits.LENGTH_EPSILON_M) for bay in bays):
            listed = ", ".join(f"{bay:.4f}" for bay in bays)
            out.add(
                idx.path(grid_loc, axis),
                codes.OUT_OF_SUPPORTED_RANGE,
                f"Bay lengths must be between 4'-0\" and 24'-0\" (D032); computed bays: {listed} m.",
                related=[idx.path(fp_loc, length_name)],
            )

    # MODEL-005 §5: frame parameter bounds and the brace-fit rule.
    params = frame.parameters
    ppath = lambda name: idx.path(frame_loc, "parameters", name)  # noqa: E731
    if not limits.within(params.joist_spacing_m, limits.JOIST_SPACING_MIN_M, limits.JOIST_SPACING_MAX_M, limits.LENGTH_EPSILON_M):
        out.add(ppath("joist_spacing_m"), codes.OUT_OF_SUPPORTED_RANGE, "Joist spacing must be between 12\" and 48\" (MODEL-005 §5).", params.joist_spacing_m)
    if params.purlins_per_slope > limits.PURLINS_PER_SLOPE_MAX:
        out.add(ppath("purlins_per_slope"), codes.OUT_OF_SUPPORTED_RANGE, "Purlins per slope must be between 0 and 4 (MODEL-005 §5).", params.purlins_per_slope)
    if not limits.within(params.knee_brace_leg_m, limits.KNEE_BRACE_LEG_MIN_M, limits.KNEE_BRACE_LEG_MAX_M, limits.LENGTH_EPSILON_M):
        out.add(ppath("knee_brace_leg_m"), codes.OUT_OF_SUPPORTED_RANGE, "Knee brace leg must be between 1'-6\" and 4'-0\" (MODEL-005 §5).", params.knee_brace_leg_m)
    elif params.knee_braces_level_1 or params.knee_braces_eave:
        shortest: tuple[float, str, str] | None = None
        for axis, length_name in (("x_lines", "width_m"), ("y_lines", "depth_m")):
            fractions = [line.fraction for line in getattr(grid, axis)]
            length = getattr(fp, length_name)
            for a, b in zip(fractions, fractions[1:]):
                bay = length * (b - a)
                if shortest is None or bay < shortest[0]:
                    shortest = (bay, axis, length_name)
        if shortest is not None and 2 * params.knee_brace_leg_m > shortest[0] + limits.LENGTH_EPSILON_M:
            bay, axis, length_name = shortest
            out.add(
                ppath("knee_brace_leg_m"),
                codes.OUT_OF_SUPPORTED_RANGE,
                f"Two knee braces must fit under the shortest beam: twice the leg exceeds the {bay:.4f} m bay (MODEL-005 §5.2).",
                params.knee_brace_leg_m,
                [idx.path(fp_loc, length_name), idx.path(grid_loc, axis)],
            )

    # D054: connection types must be allowed for their junction class.
    for junction_class, connection_type in frame.connection_defaults.items():
        if not connection_catalog.allowed(junction_class, connection_type):
            out.add(idx.path(frame_loc, "connection_defaults", junction_class), codes.UNSUPPORTED_VALUE, f"{connection_type} is not offered for {junction_class} junctions (D054).", connection_type)
    for index, connection in idx.of_kind("Connection"):
        if not connection_catalog.allowed(connection.junction_class, connection.connection_type):
            out.add(idx.path(index, "connection_type"), codes.UNSUPPORTED_VALUE, f"{connection.connection_type} is not offered for {connection.junction_class} junctions (D054).", connection.connection_type, [idx.path(index, "junction_class")])

    # Generation rule and mode.
    rule = _rule(grid.generation_rule_version)
    if rule is None:
        out.add(idx.path(grid_loc, "generation_rule_version"), codes.UNSUPPORTED_VALUE, f"Supported generation rules: {', '.join(_registered_rules())}.", grid.generation_rule_version)
    if frame.generation_mode != limits.SUPPORTED_GENERATION_MODE:
        out.add(idx.path(frame_loc, "generation_mode"), codes.UNSUPPORTED_VALUE, f"Only generation mode {limits.SUPPORTED_GENERATION_MODE} is supported.", frame.generation_mode)
    if rule is not None:
        for index, member in idx.of_kind("TimberMember"):
            if member.member_role not in rule.generated_roles:
                out.add(idx.path(index, "member_role"), codes.UNSUPPORTED_VALUE, f"Rule {rule.version} generates only {', '.join(sorted(rule.generated_roles))} members.", member.member_role)

    return out.result(Stage.DOMAIN)


# ---------------------------------------------------------------------------
# Stage 5 — conformance (D046)


def _rule(version: str):
    """Look up a generation rule in the timber registry (TIMBER-001 §6)."""
    from homedesign.timber.rules import get_rule  # imported lazily: timber depends on model types

    return get_rule(version)


def _registered_rules() -> tuple[str, ...]:
    from homedesign.timber.rules import registered_versions

    return registered_versions()


def _stage_conformance(snapshot: Snapshot) -> ValidationResult | None:
    out = _Collector()
    r = _resolve_all(snapshot)
    idx = r.idx
    rule = _rule(r.grid[1].generation_rule_version)
    assert rule is not None, "stage 4 guarantees a registered rule"
    locator = {entity.id: index for index, entity in enumerate(snapshot.entities)}
    # Member and connection findings come from the rule's shared comparison (TIMBER-002 §6).
    for finding in rule.conformance(snapshot):
        out.add(
            idx.path(locator[finding.entity_id], *finding.field),
            finding.code,
            finding.message,
            finding.value,
            [idx.path(locator[entity_id], *field) for entity_id, field in finding.related],
        )
    return out.result(Stage.CONFORMANCE)
