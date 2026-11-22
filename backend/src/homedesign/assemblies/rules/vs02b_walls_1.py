"""Rule ``vs02b-walls-1`` (wall-rules.md; ASM-001 §4–6; D065, D066, D076, D078–D080).

Generates one wall in every perimeter bay of each story, and each wall's framing: layout studs and
girts, kings, jacks above the threshold, headers, rough sills, and cripples with stud infill, and
bucks with straw bale. Also reports each opening's framed rectangle and each wall's girt heights,
which MODEL-006's fit rules read. Geometric inventory only, not a structural design procedure.

Numeric evaluation (ASM-001 §4.1): IEEE-754 doubles evaluated exactly as written, left to right,
with no rounding or snapping. The rule reads no roof value, so every coordinate is bit-identical
across implementations (no tan exception).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..inventory import FramedOpening, GeneratedFramingPiece, GeneratedWall, WallInventory

if TYPE_CHECKING:
    from homedesign.model.schema import Snapshot

VERSION = "vs02b-walls-1"
EPSILON_M = 1e-6  # D026
# Totality guard (ASM-001 §5.6): stages 1–3 allow any positive spacing and any girt count, which
# stage 4 then rejects (D077). Beyond this many layout positions or girts the rule generates none,
# so it stays fast on such snapshots; its output there is unspecified (MODEL-006 rejects them).
_PIECE_CAP = 1000


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


def wall_key(axis: str, line_id: str, a_id: str, b_id: str, level_index: int) -> str:
    """D080: ``wall/axis-x/{y}/{xa}-{xb}/level-{i}`` or ``wall/axis-y/{x}/{ya}-{yb}/level-{i}``."""
    return f"wall/axis-{axis}/{line_id}/{a_id}-{b_id}/level-{level_index}"


def _overlap(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> float:
    return min(hi_a, hi_b) - max(lo_a, lo_b)


class _Framing:
    """The default definition's framing layer, read defensively: the rule is total on any snapshot
    that passes stages 1–3, so a definition that stage 4 will reject yields no pieces."""

    def __init__(self, definition: Any, by_id: dict[str, Any]) -> None:
        self.kind: str | None = None
        self.definition_id = definition.id if definition is not None else ""
        framing = None
        if definition is not None:
            framing = next((layer.framing for layer in definition.layers if layer.framing is not None), None)
        if framing is None:
            return
        self.kind = framing.type
        self.material_id = framing.framing_material_id

        def section(section_id: str | None) -> Any:
            record = by_id.get(section_id) if section_id is not None else None
            return record if record is not None and record.kind == "Section" else None

        if framing.type == "STUD":
            self.stud = section(framing.stud_section_id)
            self.girt = section(framing.girt_section_id)
            self.header = section(framing.header_section_id)
            if self.stud is None or self.header is None:
                self.kind = None
                return
            self.spacing = framing.stud_spacing_m
            self.girt_count = framing.girt_count if self.girt is not None else 0
            self.t = self.stud.actual_width_m
            self.t_g = self.girt.actual_width_m if self.girt is not None else 0.0
            self.d = self.header.actual_depth_m  # vertical (D076)
            self.threshold = framing.jack_threshold_width_m
        else:
            self.buck = section(framing.buck_section_id)
            if self.buck is None:
                self.kind = None
                return
            self.b = self.buck.actual_width_m


def _rectangle(f: _Framing, opening: Any) -> tuple[float, float, float, float, int]:
    """D076's framed rectangle ``(u0, u1, v0, v1)`` and ``j`` (1 with jacks): the one helper that both
    the pieces and ``framed_openings`` read (ASM-001 §5.7)."""
    o, w, s, h = opening.offset_m, opening.width_m, opening.sill_height_m, opening.height_m
    window = opening.opening_kind == "WINDOW"
    if f.kind == "STUD":
        t = f.t
        j = 1 if w > f.threshold + EPSILON_M else 0
        u0 = o - (1 + j) * t
        u1 = o + w + (1 + j) * t
        v1 = s + h + f.d
        v0 = s - t if window else 0.0
        return u0, u1, v0, v1, j
    b = f.b
    return o - b, o + w + b, (s - b if window else 0.0), s + h + b, 0


def _build(snapshot: "Snapshot") -> WallInventory:
    by_id: dict[str, Any] = {}
    for entity in snapshot.entities:
        by_id.setdefault(entity.id, entity)
    building = snapshot.building
    fp = by_id[building.footprint_id]
    levels = [by_id[level_id] for level_id in building.level_ids]
    frame = by_id[building.frame_system_id]
    grid = by_id[frame.grid_id]
    system = by_id[building.wall_system_id]
    params = frame.parameters
    definition_id = system.default_assembly_definition_id
    definition = by_id.get(definition_id)
    if definition is not None and definition.kind != "AssemblyDefinition":
        definition = None
    f = _Framing(definition, by_id)

    # Evaluated exactly as the frame rule: origin + (length * fraction).
    xs = [(line.id, fp.origin_m[0] + fp.width_m * line.fraction) for line in grid.x_lines]
    ys = [(line.id, fp.origin_m[1] + fp.depth_m * line.fraction) for line in grid.y_lines]
    L = params.knee_brace_leg_m
    plane_braced = (params.knee_braces_level_1, params.knee_braces_eave)

    # Openings follow their wall's stored record (MODEL-006 §8.5): opening.wall_id -> wall key.
    stored_keys = {e.id: e.generation_key for e in snapshot.entities if e.kind == "Wall"}
    openings_by_wall: dict[str, list[Any]] = {}
    for opening in sorted((e for e in snapshot.entities if e.kind == "Opening"), key=lambda e: e.id):
        key = stored_keys.get(opening.wall_id)
        if key is not None:
            openings_by_wall.setdefault(key, []).append(opening)

    walls: list[GeneratedWall] = []
    framing: list[GeneratedFramingPiece] = []
    framed: dict[str, FramedOpening] = {}
    girts: dict[str, tuple[float, ...]] = {}

    for i, level in enumerate(levels):
        z_lo = level.elevation_m
        H = level.story_height_m
        braced = plane_braced[i] if i < len(plane_braced) else False
        bays: list[tuple[str, str, str, str, float, float, float]] = []  # (axis, line, a, b, A, B, fixed)
        for y_id, y in (ys[0], ys[-1]):
            for (xa_id, xa), (xb_id, xb) in zip(xs, xs[1:]):
                bays.append(("x", y_id, xa_id, xb_id, xa, xb, y))
        for x_id, x in (xs[0], xs[-1]):
            for (ya_id, ya), (yb_id, yb) in zip(ys, ys[1:]):
                bays.append(("y", x_id, ya_id, yb_id, ya, yb, x))
        for axis, line_id, a_id, b_id, A, B, fixed in bays:
            key = wall_key(axis, line_id, a_id, b_id, i)
            if axis == "x":
                def point(along: float, z: float, fixed: float = fixed) -> tuple[float, float, float]:
                    return (along, fixed, z)
            else:
                def point(along: float, z: float, fixed: float = fixed) -> tuple[float, float, float]:
                    return (fixed, along, z)
            walls.append(GeneratedWall(key, level.id, i, axis, point(A, z_lo), point(B, z_lo), H, definition_id))
            W = B - A
            pieces = _wall_pieces(f, key, A, B, W, H, z_lo, L, braced, openings_by_wall.get(key, []), point, framed, girts)
            framing.extend(sorted(pieces, key=lambda p: _utf16(p.generation_key)))

    return WallInventory(
        walls=tuple(sorted(walls, key=lambda w: _utf16(w.generation_key))),
        framing=tuple(sorted(framing, key=lambda p: _utf16(p.generation_key))),
        framed_openings=framed,
        girt_heights=girts,
    )


def _wall_pieces(
    f: _Framing,
    key: str,
    A: float,
    B: float,
    W: float,
    H: float,
    z_lo: float,
    L: float,
    braced: bool,
    openings: list[Any],
    point: Any,
    framed: dict[str, FramedOpening],
    girts: dict[str, tuple[float, ...]],
) -> list[GeneratedFramingPiece]:
    """One wall's pieces (ASM-001 §5), with its openings' rectangles and its girt heights recorded."""
    if f.kind is None:
        girts[key] = ()
        return []
    pieces: list[GeneratedFramingPiece] = []

    def section_for(kind: str) -> str:
        if f.kind == "BUCK":
            return f.buck.id
        if kind == "GIRT":
            return f.girt.id
        if kind == "HEADER":
            return f.header.id
        return f.stud.id

    def vertical(piece_key: str, kind: str, opening_id: str | None, u: float, v_start: float, v_end: float) -> None:
        if v_end - v_start > EPSILON_M:  # no zero-length or negative pieces (ASM-001 §5.6)
            pieces.append(GeneratedFramingPiece(
                piece_key, key, kind, opening_id, point(A + u, z_lo + v_start), point(A + u, z_lo + v_end), section_for(kind), f.material_id,
            ))

    def horizontal(piece_key: str, kind: str, opening_id: str | None, along_start: float, along_end: float, v: float) -> None:
        """``along_*`` are global stations (A + u, or A and B on the post axes)."""
        if along_end - along_start > EPSILON_M:
            pieces.append(GeneratedFramingPiece(
                piece_key, key, kind, opening_id, point(along_start, z_lo + v), point(along_end, z_lo + v), section_for(kind), f.material_id,
            ))

    def top(u: float) -> float:
        """Where a vertical piece ends: on a brace axis near a braced post, else the upper datum (§5.1)."""
        if braced and u < L - EPSILON_M:
            return (H - L) + u
        if braced and u > W - L + EPSILON_M:
            return (H - L) + (W - u)
        return H

    rects: list[tuple[Any, float, float, float, float, int]] = []
    for opening in openings:
        u0, u1, v0, v1, j = _rectangle(f, opening)
        framed[opening.id] = FramedOpening(opening.id, key, u0, u1, v0, v1)
        rects.append((opening, u0, u1, v0, v1, j))

    if f.kind == "BUCK":
        girts[key] = ()
        b = f.b
        for opening, u0, u1, v0, v1, _ in rects:
            o, w, s, h = opening.offset_m, opening.width_m, opening.sill_height_m, opening.height_m
            prefix = f"{key}/opening/{opening.id}/"
            vertical(prefix + "buck-jamb/start", "BUCK_JAMB", opening.id, o - b / 2, v0, v1)
            vertical(prefix + "buck-jamb/end", "BUCK_JAMB", opening.id, o + w + b / 2, v0, v1)
            horizontal(prefix + "buck-head", "BUCK_HEAD", opening.id, A + o, A + (o + w), s + h + b / 2)
            if opening.opening_kind == "WINDOW":
                horizontal(prefix + "buck-sill", "BUCK_SILL", opening.id, A + o, A + (o + w), s - b / 2)
        return pieces

    t, d, S = f.t, f.d, f.spacing
    # Opening framing (§5.3).
    for opening, u0, u1, v0, v1, j in rects:
        o, w, s, h = opening.offset_m, opening.width_m, opening.sill_height_m, opening.height_m
        prefix = f"{key}/opening/{opening.id}/"
        king_start = o - t / 2 if j == 0 else o - 3 * t / 2
        king_end = o + w + t / 2 if j == 0 else o + w + 3 * t / 2
        vertical(prefix + "king/start", "KING", opening.id, king_start, 0.0, top(king_start))
        vertical(prefix + "king/end", "KING", opening.id, king_end, 0.0, top(king_end))
        if j == 1:
            vertical(prefix + "jack/start", "JACK", opening.id, o - t / 2, 0.0, s + h)
            vertical(prefix + "jack/end", "JACK", opening.id, o + w + t / 2, 0.0, s + h)
            horizontal(prefix + "header", "HEADER", opening.id, A + (o - t), A + (o + w + t), s + h + d / 2)
        else:
            horizontal(prefix + "header", "HEADER", opening.id, A + o, A + (o + w), s + h + d / 2)
        if opening.opening_kind == "WINDOW":
            horizontal(prefix + "rough-sill", "ROUGH_SILL", opening.id, A + o, A + (o + w), s - t / 2)

    # Layout studs and cripples (§5.2, §5.4: the band rule).
    k = 1 if W < S * _PIECE_CAP else 0
    while k and A + k * S < B - EPSILON_M:
        p = k * S
        lo, hi = p - t / 2, p + t / 2
        claim = next(((opening, u0, u1, v0, v1, j) for opening, u0, u1, v0, v1, j in rects if _overlap(lo, hi, u0, u1) > EPSILON_M), None)
        if claim is None:
            vertical(f"{key}/stud/s{k}", "STUD", None, p, 0.0, top(p))
        else:
            opening, u0, u1, v0, v1, j = claim
            on_king = _overlap(lo, hi, u0, u0 + t) > EPSILON_M or _overlap(lo, hi, u1 - t, u1) > EPSILON_M
            if not on_king:
                prefix = f"{key}/opening/{opening.id}/cripple/s{k}/"
                vertical(prefix + "above", "CRIPPLE", opening.id, p, v1, top(p))
                on_jack = j == 1 and (_overlap(lo, hi, u0 + t, u0 + 2 * t) > EPSILON_M or _overlap(lo, hi, u1 - 2 * t, u1 - t) > EPSILON_M)
                if opening.opening_kind == "WINDOW" and not on_jack:
                    vertical(prefix + "below", "CRIPPLE", opening.id, p, 0.0, v0)
        k += 1

    # Girts (§5.2, §5.5): at H * (i / (n + 1)), cut where their band overlaps a framed height.
    n = f.girt_count if 0 <= f.girt_count <= _PIECE_CAP else 0
    heights = tuple(H * (i / (n + 1)) for i in range(1, n + 1))
    girts[key] = heights
    for i, v in enumerate(heights, start=1):
        cuts = sorted(
            ((u0, u1, opening.id) for opening, u0, u1, v0, v1, _ in rects if _overlap(v - f.t_g / 2, v + f.t_g / 2, v0, v1) > EPSILON_M),
            key=lambda cut: (cut[0], cut[2]),
        )
        start, name = A, f"{key}/girt/g{i}/start"
        for u0, u1, opening_id in cuts:
            horizontal(name, "GIRT", None, start, A + u0, v)
            start, name = A + u1, f"{key}/girt/g{i}/after/{opening_id}"
        horizontal(name, "GIRT", None, start, B, v)
    return pieces


from . import WallRule, register  # noqa: E402

register(WallRule(VERSION, _build))
