"""Rule ``vs01-post-beam-1`` (generation-rules.md, as amended by D039 and D042).

Generates posts and beams only. Not a structural design procedure.

Numeric evaluation (generation-rules.md "Numeric evaluation"): coordinates are IEEE-754
doubles evaluated exactly as written, with no rounding or snapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homedesign.model import codes

from ..inventory import ConformanceIssue, GeneratedMember

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot

VERSION = "vs01-post-beam-1"
GENERATED_ROLES = frozenset({"POST", "BEAM"})
COORDINATE_EPSILON_M = 1e-6  # D026


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


class _Parameters:
    """The inputs the rule reads, resolved from a snapshot that passed stages 1–4."""

    def __init__(self, snapshot: "Snapshot") -> None:
        by_id: dict[str, Any] = {}
        for entity in snapshot.entities:
            by_id.setdefault(entity.id, entity)
        building = snapshot.building
        self.footprint = by_id[building.footprint_id]
        self.levels = [by_id[level_id] for level_id in building.level_ids]
        self.frame = by_id[building.frame_system_id]
        self.grid = by_id[self.frame.grid_id]
        self.defaults = self.frame.member_defaults


def generate(snapshot: "Snapshot") -> tuple[GeneratedMember, ...]:
    """All members the rule defines, sorted by generation_key (code-unit order).

    Defined only for snapshots that pass validation stages 1–4.
    """
    p = _Parameters(snapshot)
    fp = p.footprint
    # Evaluated exactly as written: origin + (length * fraction).
    xs = [(line.id, fp.origin_m[0] + fp.width_m * line.fraction) for line in p.grid.x_lines]
    ys = [(line.id, fp.origin_m[1] + fp.depth_m * line.fraction) for line in p.grid.y_lines]
    level0, level1 = p.levels
    z0 = level0.elevation_m
    z1 = level1.elevation_m
    z_eave = level1.elevation_m + level1.story_height_m

    post = p.defaults["POST"]
    beam = p.defaults["BEAM"]
    members: list[GeneratedMember] = []

    for x_id, x in xs:
        for y_id, y in ys:
            members.append(GeneratedMember(f"frame/{x_id}/{y_id}/level-0/post", "POST", (x, y, z0), (x, y, z1), post.section_id, post.material_id))
            members.append(GeneratedMember(f"frame/{x_id}/{y_id}/level-1/post", "POST", (x, y, z1), (x, y, z_eave), post.section_id, post.material_id))

    for plane, z in (("plane-L1", z1), ("plane-eave", z_eave)):
        for y_id, y in ys:
            for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
                members.append(GeneratedMember(f"frame/axis-x/{y_id}/{xa_id}-{xb_id}/{plane}/beam", "BEAM", (xa, y, z), (xb, y, z), beam.section_id, beam.material_id))
        for x_id, x in xs:
            for (ya_id, ya), (yb_id, yb) in zip(ys, ys[1:]):
                members.append(GeneratedMember(f"frame/axis-y/{x_id}/{ya_id}-{yb_id}/{plane}/beam", "BEAM", (x, ya, z), (x, yb, z), beam.section_id, beam.material_id))

    return tuple(sorted(members, key=lambda m: _utf16(m.generation_key)))


def _differs(a: tuple[float, ...] | list[float], b: tuple[float, ...]) -> bool:
    return any(abs(u - v) > COORDINATE_EPSILON_M for u, v in zip(a, b))


def conformance(snapshot: "Snapshot") -> list[ConformanceIssue]:
    """Compare the snapshot's members with the rule's output (D046)."""
    p = _Parameters(snapshot)
    expected = {m.generation_key: m for m in generate(snapshot)}
    actual = {e.generation_key: e for e in snapshot.entities if e.kind == "TimberMember"}
    issues: list[ConformanceIssue] = []

    for key in sorted(expected.keys() - actual.keys(), key=_utf16):
        issues.append(ConformanceIssue(
            codes.MISSING_GENERATED_MEMBER, p.frame.id, ("member_ids",),
            f"The rule generates {key}, but no member has that key.", key,
        ))
    for key in sorted(actual.keys() - expected.keys(), key=_utf16):
        issues.append(ConformanceIssue(
            codes.UNEXPECTED_MEMBER, actual[key].id, ("generation_key",),
            f"The rule does not generate {key}.", key,
        ))
    for key in sorted(expected.keys() & actual.keys(), key=_utf16):
        want, have = expected[key], actual[key]
        if have.member_role != want.member_role:
            issues.append(ConformanceIssue(
                codes.MEMBER_ASSIGNMENT_MISMATCH, have.id, ("member_role",),
                f"The rule assigns role {want.member_role} to {key}.", have.member_role,
            ))
        for field in ("section_id", "material_id"):
            if getattr(have, field) != getattr(want, field):
                issues.append(ConformanceIssue(
                    codes.MEMBER_ASSIGNMENT_MISMATCH, have.id, (field,),
                    f"{field} must equal member_defaults.{want.member_role}.{field} (D039).",
                    getattr(have, field),
                    ((p.frame.id, ("member_defaults", want.member_role, field)),),
                ))
        for field, point in (("start_m", want.start_m), ("end_m", want.end_m)):
            if _differs(getattr(have, field), point):
                issues.append(ConformanceIssue(
                    codes.MEMBER_GEOMETRY_MISMATCH, have.id, (field,),
                    f"{field} differs from the rule by more than 1e-6 m.",
                ))
    return issues


from . import Rule, register  # noqa: E402

register(Rule(VERSION, GENERATED_ROLES, generate, conformance))
