"""Typed commands to candidate snapshots (MODEL-003; interfaces.md §2–4, §7.1).

``propose`` and ``propose_create`` are pure: no I/O beyond reading the packaged
template, no clock (the caller passes ``at``), and no randomness. Persistence,
preview storage, and authorization are MODEL-004 / API concerns.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, replace
from functools import cache
from importlib import resources
from typing import Any, Callable

from .. import codes
from ..canonical import fingerprint
from ..codes import Stage
from ..jcs import canonical_json
from ..limits import RECORD_SCHEMA_VERSIONS
from ..paths import EntityStep, render
from ..schema import Snapshot
from ..validation import Issue, ValidationResult, _Collector, validate_value
from .envelope import parse_command, reject
from .mint import mint

CLASSIFICATION_VERSION = "vs02-change-classes-1"  # dependencies.md §4.1, D057
CLASSIFICATION = {
    "AddSection": "routine",
    # D057: the pitch places principal rafters and purlins, so roof edits regenerate framing.
    "SetGableRoofParameters": "consequential",
    "SetFrameParameters": "consequential",
    "SetFootprintDimensions": "consequential",
    "SetStoryHeights": "consequential",
    "SetTimberGrid": "consequential",
    "SetMemberSection": "consequential",
    "UndoToRevision": "consequential",
    "CreateReferenceProject": "consequential",
}
IMPACTED_ARTIFACTS = ("mesh3d", "plan2d", "preliminary_estimate", "timber_schedule")  # interfaces.md §3
WARNINGS = (
    {
        "code": "PRELIMINARY_UNVERIFIED",
        "message": "Framing and estimates are preliminary. Structural adequacy has not been assessed.",
    },
)


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


def spath(entity_id: str, *steps: str | int) -> str:
    """D036 path of a field of an entity addressed by ID."""
    return render(["entities", EntityStep(-1, entity_id), *steps])


# --- results -----------------------------------------------------------------


@dataclass(frozen=True)
class CandidateChange:
    candidate: Snapshot
    command_type: str
    base_revision_id: str | None
    revision_id: str
    operation_id: str
    command_hash: str
    is_noop: bool
    classification: str
    changes: tuple[dict[str, Any], ...]
    members_added: tuple[dict[str, str], ...]
    members_removed: tuple[dict[str, str], ...]
    members_updated: tuple[str, ...]
    classification_version: str = CLASSIFICATION_VERSION
    impacted_artifacts: tuple[str, ...] = IMPACTED_ARTIFACTS
    warnings: tuple[dict[str, str], ...] = WARNINGS

    @property
    def confirmation_required(self) -> bool:
        return self.classification == "consequential" and not self.is_noop  # D045

    def to_preview_dict(self) -> dict[str, Any]:
        """interfaces.md §3 fields (``preview_id``/``expires_at`` are added by the server)."""
        return {
            "base_revision_id": self.base_revision_id,
            "revision_id": None if self.is_noop else self.revision_id,
            "command_hash": self.command_hash,
            "classification": self.classification,
            "classification_version": self.classification_version,
            "confirmation_required": self.confirmation_required,
            "is_noop": self.is_noop,
            "changes": [dict(c) for c in self.changes],
            "members": {
                "added": [dict(m) for m in self.members_added],
                "removed": [dict(m) for m in self.members_removed],
                "updated": list(self.members_updated),
            },
            "impacted_artifacts": list(self.impacted_artifacts),
            "warnings": [dict(w) for w in self.warnings],
        }


@dataclass(frozen=True)
class ProposeResult:
    change: CandidateChange | None = None
    rejection: ValidationResult | None = None

    @property
    def accepted(self) -> bool:
        return self.change is not None


def _rejected(result: ValidationResult) -> ProposeResult:
    return ProposeResult(rejection=result)


# --- applying commands to a draft -------------------------------------------


@dataclass
class _Context:
    base: Snapshot
    command: Any
    actor_id: str
    target: Snapshot | None

    def mint(self, purpose: str, key: str | None) -> str:
        return mint(purpose, self.base.project_id, self.actor_id, self.command.command_id, key)


@dataclass
class _Applied:
    field_map: dict[str, str] = field(default_factory=dict)  # snapshot path -> args path
    regenerate: bool = False
    rejection: ValidationResult | None = None


def _entity(draft: dict, entity_id: str) -> dict:
    return next(e for e in draft["entities"] if e["id"] == entity_id)


def _frame_and_grid(draft: dict) -> tuple[dict, dict]:
    frame = _entity(draft, draft["building"]["frame_system_id"])
    return frame, _entity(draft, frame["grid_id"])


def _apply_footprint(draft: dict, ctx: _Context) -> _Applied:
    args = ctx.command.args
    fp = _entity(draft, draft["building"]["footprint_id"])
    fp["width_m"], fp["depth_m"] = args.width_m, args.depth_m
    return _Applied({spath(fp["id"], "width_m"): "args.width_m", spath(fp["id"], "depth_m"): "args.depth_m"}, regenerate=True)


def _apply_story_heights(draft: dict, ctx: _Context) -> _Applied:
    h0, h1 = ctx.command.args.story_heights_m
    l0, l1 = (_entity(draft, i) for i in draft["building"]["level_ids"])
    l0["story_height_m"], l1["elevation_m"], l1["story_height_m"] = h0, h0, h1
    return _Applied(
        {
            spath(l0["id"], "story_height_m"): "args.story_heights_m[0]",
            spath(l1["id"], "elevation_m"): "args.story_heights_m[0]",
            spath(l1["id"], "story_height_m"): "args.story_heights_m[1]",
        },
        regenerate=True,
    )


def _apply_roof(draft: dict, ctx: _Context) -> _Applied:
    args = ctx.command.args
    roof = _entity(draft, draft["building"]["roof_id"])
    roof["pitch_rad"], roof["eave_overhang_m"] = args.pitch_rad, args.eave_overhang_m
    return _Applied({spath(roof["id"], "pitch_rad"): "args.pitch_rad", spath(roof["id"], "eave_overhang_m"): "args.eave_overhang_m"}, regenerate=True)


def _apply_frame_parameters(draft: dict, ctx: _Context) -> _Applied:
    args = ctx.command.args
    frame, _ = _frame_and_grid(draft)
    frame["parameters"] = args.model_dump(mode="json")
    return _Applied({spath(frame["id"], "parameters", name): f"args.{name}" for name in frame["parameters"]}, regenerate=True)


def _apply_grid(draft: dict, ctx: _Context) -> _Applied:
    _, grid = _frame_and_grid(draft)
    out = _Collector()
    applied = _Applied(regenerate=True)
    new_lines: dict[str, list[dict]] = {}
    for axis, prefix in (("x_lines", "x"), ("y_lines", "y")):
        base_ids = {line["id"] for line in grid[axis]}
        first_seen: dict[str, int] = {}
        for k, arg in enumerate(getattr(ctx.command.args, axis)):
            if arg.id is None:
                continue
            if arg.id not in base_ids:
                out.add(f"args.{axis}[{k}].id", codes.DANGLING_REFERENCE, f"{arg.id} is not a line of the base grid's {axis}.", arg.id)
            elif arg.id in first_seen:
                out.add(f"args.{axis}[{k}].id", codes.DUPLICATE_LINE_ID, "Line listed more than once.", arg.id, [f"args.{axis}[{first_seen[arg.id]}].id"])
            else:
                first_seen[arg.id] = k
        # D042: new lines are numbered from one more than the largest existing number.
        next_number = 1 + max((int(i[1:]) for i in base_ids), default=-1)
        lines = []
        for k, arg in enumerate(getattr(ctx.command.args, axis)):
            if arg.id is None:
                line_id = f"{prefix}{next_number}"
                next_number += 1
            else:
                line_id = arg.id
            lines.append({"id": line_id, "fraction": arg.fraction})
            applied.field_map[spath(grid["id"], axis, k, "fraction")] = f"args.{axis}[{k}].fraction"
        applied.field_map[spath(grid["id"], axis)] = f"args.{axis}"
        new_lines[axis] = lines
    applied.rejection = out.result(Stage.REFERENTIAL)
    if applied.rejection is None:
        grid["x_lines"], grid["y_lines"] = new_lines["x_lines"], new_lines["y_lines"]
    return applied


def _apply_member_section(draft: dict, ctx: _Context) -> _Applied:
    from homedesign.timber import get_rule

    args = ctx.command.args
    frame, grid = _frame_and_grid(draft)
    target = next((e for e in draft["entities"] if e["id"] == args.section_id), None)
    if target is None:
        return _Applied(rejection=reject("args.section_id", codes.DANGLING_REFERENCE, "Section does not exist.", args.section_id))
    if target["kind"] != "Section":
        return _Applied(rejection=reject("args.section_id", codes.WRONG_REFERENCE_KIND, "Referenced record is not a Section.", args.section_id))
    rule = get_rule(grid["generation_rule_version"])
    if rule is None or args.role not in rule.generated_roles:
        return _Applied(rejection=reject("args.role", codes.UNSUPPORTED_VALUE, "The frame's generation rule does not generate this role (D040).", args.role))
    frame["member_defaults"][args.role]["section_id"] = args.section_id
    return _Applied({spath(frame["id"], "member_defaults", args.role, "section_id"): "args.section_id"}, regenerate=True)


def _apply_add_section(draft: dict, ctx: _Context) -> _Applied:
    args = ctx.command.args
    section_id = ctx.mint("entity", "section")
    draft["entities"].append(
        {
            "id": section_id,
            "kind": "Section",
            "schema_version": RECORD_SCHEMA_VERSIONS["Section"],
            "shape": "rectangular",
            "actual_width_m": args.actual_width_m,
            "actual_depth_m": args.actual_depth_m,
            "nominal_label": args.nominal_label,
        }
    )
    return _Applied(
        {
            spath(section_id, "actual_width_m"): "args.actual_width_m",
            spath(section_id, "actual_depth_m"): "args.actual_depth_m",
            spath(section_id, "nominal_label"): "args.nominal_label",
        }
    )


def _apply_undo(draft: dict, ctx: _Context) -> _Applied:
    wanted = ctx.command.args.target_revision_id
    target = ctx.target
    if target is None or target.revision_id != wanted or target.project_id != ctx.base.project_id:
        return _Applied(rejection=reject("args.target_revision_id", codes.DANGLING_REFERENCE, "Target is not a revision of this project.", wanted))
    restored = target.model_dump(mode="json")
    draft["building"], draft["entities"] = restored["building"], restored["entities"]  # D044: original IDs
    return _Applied()


_APPLY: dict[str, Callable[[dict, _Context], _Applied]] = {
    "SetFootprintDimensions": _apply_footprint,
    "SetStoryHeights": _apply_story_heights,
    "SetGableRoofParameters": _apply_roof,
    "SetTimberGrid": _apply_grid,
    "SetMemberSection": _apply_member_section,
    "SetFrameParameters": _apply_frame_parameters,
    "AddSection": _apply_add_section,
    "UndoToRevision": _apply_undo,
}


# --- shared pipeline ---------------------------------------------------------


def _link_args(result: ValidationResult, field_map: dict[str, str]) -> ValidationResult:
    """interfaces.md §7.1: add the argument path when a failing field was set by an argument."""
    if not field_map:
        return result
    issues = []
    for issue in result.issues:
        extra = {field_map[p] for p in (issue.path, *issue.related_paths) if p in field_map}
        if extra:
            related = sorted((set(issue.related_paths) | extra) - {issue.path}, key=_utf16)
            issue = replace(issue, related_paths=tuple(related))
        issues.append(issue)
    return replace(result, issues=tuple(issues))


def _regenerate(draft: dict, base_members: dict[str, str], mint_entity: Callable[[str], str]) -> None:
    from homedesign.timber import get_rule

    snapshot = Snapshot.model_validate(draft)  # stages 1–4 already passed
    frame, grid = _frame_and_grid(draft)
    generated = get_rule(grid["generation_rule_version"]).generate(snapshot)
    members = [
        {
            "id": base_members.get(m.generation_key) or mint_entity("generation/" + m.generation_key),
            "kind": "TimberMember",
            "schema_version": RECORD_SCHEMA_VERSIONS["TimberMember"],
            **m.to_json(),
        }
        for m in generated
    ]
    draft["entities"] = [e for e in draft["entities"] if e["kind"] != "TimberMember"] + members
    frame["member_ids"] = [m["id"] for m in members]


def _content(value: dict | None) -> bytes:
    if value is None:
        return b""
    return canonical_json({"building": value["building"], "entities": sorted(value["entities"], key=lambda e: e["id"])})


def _diff(base: dict | None, cand: dict) -> tuple[tuple, tuple, tuple, tuple]:
    def records(value):
        if value is None:
            return {}, {}
        others = {value["building"]["id"]: value["building"]}
        members = {}
        for e in value["entities"]:
            (members if e["kind"] == "TimberMember" else others)[e["id"]] = e
        return others, members

    b_rec, b_mem = records(base)
    c_rec, c_mem = records(cand)
    changes = []
    for rid in b_rec.keys() | c_rec.keys():
        before, after = b_rec.get(rid), c_rec.get(rid)
        if before is None or after is None:
            record = after or before
            changes.append({"entity_kind": record["kind"], "entity_id": rid, "field": "", "before": before, "after": after})
            continue
        for name in sorted(before.keys() | after.keys()):
            if canonical_json(before.get(name)) != canonical_json(after.get(name)):
                changes.append({"entity_kind": after["kind"], "entity_id": rid, "field": name, "before": before.get(name), "after": after.get(name)})
    changes.sort(key=lambda c: (_utf16(c["entity_kind"]), c["entity_id"], _utf16(c["field"])))

    def summary(m):
        return {"id": m["id"], "generation_key": m["generation_key"]}

    by_key = lambda m: _utf16(m["generation_key"])  # noqa: E731
    added = tuple(summary(m) for m in sorted((c_mem[i] for i in c_mem.keys() - b_mem.keys()), key=by_key))
    removed = tuple(summary(m) for m in sorted((b_mem[i] for i in b_mem.keys() - c_mem.keys()), key=by_key))
    updated = tuple(sorted(i for i in b_mem.keys() & c_mem.keys() if canonical_json(b_mem[i]) != canonical_json(c_mem[i])))
    return tuple(changes), added, removed, updated


def _finish(
    *,
    base_value: dict | None,
    draft: dict,
    applied: _Applied,
    command: Any,
    command_hash: str,
    mint_fn: Callable[[str, str | None], str],
) -> ProposeResult:
    pre = validate_value(draft)
    if not pre.valid:
        stale_only = {codes.CATALOG[i.code] for i in pre.issues} == {Stage.CONFORMANCE}
        if not (applied.regenerate and stale_only):
            return _rejected(_link_args(pre, applied.field_map))
    if applied.regenerate:
        base_members = {}
        if base_value is not None:
            base_members = {e["generation_key"]: e["id"] for e in base_value["entities"] if e["kind"] == "TimberMember"}
        _regenerate(draft, base_members, lambda key: mint_fn("entity", key))
    final = validate_value(draft)
    if not final.valid:
        return _rejected(_link_args(final, applied.field_map))
    changes, added, removed, updated = _diff(base_value, draft)
    return ProposeResult(
        change=CandidateChange(
            candidate=final.snapshot,
            command_type=command.type,
            base_revision_id=None if base_value is None else base_value["revision_id"],
            revision_id=draft["revision_id"],
            operation_id=mint_fn("operation", None),
            command_hash=command_hash,
            is_noop=base_value is not None and _content(base_value) == _content(draft),
            classification=CLASSIFICATION[command.type],
            changes=changes,
            members_added=added,
            members_removed=removed,
            members_updated=updated,
        )
    )


def command_hash(command: Any) -> str:
    """SHA-256 of a parsed envelope's canonical form, unset optional fields omitted (interfaces.md §3)."""
    return fingerprint(command.model_dump(mode="json", exclude_unset=True))


# --- public API --------------------------------------------------------------


def propose(base: Snapshot, command: Any, *, actor_id: str, at: str, target: Snapshot | None = None) -> ProposeResult:
    """Apply a command to ``base`` and return the validated candidate or a rejection.

    ``command`` is the parsed JSON envelope. ``at`` (RFC 3339 UTC) becomes ``created_at``.
    ``target`` is the snapshot of ``args.target_revision_id`` for ``UndoToRevision``.
    Never raises for any ``command`` value.
    """
    # interfaces.md §7.1: a stale base is rejected before anything is computed.
    if isinstance(command, dict) and isinstance(command.get("base_revision_id"), str) and command["base_revision_id"] != base.revision_id:
        return _rejected(ValidationResult(False, "REVISION_CONFLICT", ()))
    parsed, error = parse_command(command)
    if error is not None:
        return _rejected(error)
    if parsed.type == "CreateReferenceProject":
        return _rejected(reject("type", codes.INVALID_ENUM, "CreateReferenceProject uses the creation envelope (propose_create).", parsed.type))
    if parsed.project_id != base.project_id:
        return _rejected(reject("project_id", codes.DANGLING_REFERENCE, "project_id does not match the base snapshot.", parsed.project_id))

    ctx = _Context(base, parsed, actor_id, target)
    draft = base.model_dump(mode="json")
    applied = _APPLY[parsed.type](draft, ctx)
    if applied.rejection is not None:
        return _rejected(applied.rejection)
    draft["revision_id"] = ctx.mint("revision", None)
    draft["parent_revision_id"] = base.revision_id
    draft["created_at"] = at
    return _finish(
        base_value=base.model_dump(mode="json"),
        draft=draft,
        applied=applied,
        command=parsed,
        command_hash=command_hash(parsed),
        mint_fn=ctx.mint,
    )


@cache
def _template_text() -> str:
    return resources.files(__package__).joinpath("templates/reference-house-001.json").read_text(encoding="utf-8")


def template_value() -> dict:
    """Reference House 001 v2, the CreateReferenceProject template (packaged copy of the fixture; TIMBER-002 §7)."""
    return json.loads(_template_text())


def propose_create(command: Any, *, project_id: str, actor_id: str, at: str) -> ProposeResult:
    """``CreateReferenceProject``: instantiate the template with fresh IDs (interfaces.md §2)."""
    parsed, error = parse_command(command)
    if error is not None:
        return _rejected(error)
    if parsed.type != "CreateReferenceProject":
        return _rejected(reject("type", codes.INVALID_ENUM, "Only CreateReferenceProject uses the creation envelope.", parsed.type))

    def mint_fn(purpose: str, key: str | None) -> str:
        return mint(purpose, project_id, actor_id, parsed.command_id, key)

    template = template_value()
    records = [template["building"], *(e for e in template["entities"] if e["kind"] not in ("TimberMember", "Connection"))]
    id_map = {r["id"]: mint_fn("entity", "template/" + r["id"]) for r in records}

    def remap(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: remap(v) for k, v in value.items()}
        if isinstance(value, list):
            return [remap(v) for v in value]
        return id_map.get(value, value) if isinstance(value, str) else value

    building, *entities = (remap(copy.deepcopy(r)) for r in records)
    frame = next(e for e in entities if e["kind"] == "FrameSystem")
    frame["member_ids"] = []
    frame["connection_ids"] = []
    draft = {
        "model_schema_version": template["model_schema_version"],
        "project_id": project_id,
        "revision_id": mint_fn("revision", None),
        "parent_revision_id": None,
        "created_at": at,
        "building": building,
        "entities": entities,
    }
    return _finish(
        base_value=None,
        draft=draft,
        applied=_Applied(regenerate=True),
        command=parsed,
        command_hash=command_hash(parsed),
        mint_fn=mint_fn,
    )
