"""Wall quantities shared by the assembly schedule and the views (ART-003 §4.4, §5.1, §8.1).

The selectors of `plan2d`, `mesh3d`, and `assembly_schedule` call these helpers, so the views and the
schedule cannot disagree about where a wall faces, where its layers sit, or what its framing covers.

Numeric evaluation: IEEE-754 doubles evaluated exactly as written, left to right (as the wall rule,
ASM-001 §4.1). Nothing here reads a roof value, so every result is bit-identical across implementations;
the ECMAScript oracle (`tests/vectors/jcs/generate.mjs`) reproduces it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

EPSILON_M = 1e-6  # D026

# ART-003 §5.3: vertical pieces are drawn in plan at a point; every other kind is horizontal.
VERTICAL_KINDS = frozenset({"STUD", "KING", "JACK", "CRIPPLE", "BUCK_JAMB"})

# ART-003 §4.2: (axis, first or last line) -> elevation side. +Y is north (D026); footprints are unrotated (D031).
OUTWARD_XY = {"south": [0.0, -1.0], "north": [0.0, 1.0], "west": [-1.0, 0.0], "east": [1.0, 0.0]}


def wall_axis(generation_key: str) -> str:
    """``"x"`` or ``"y"``: the axis a wall runs along, from its D080 key (``wall/axis-x/…``)."""
    segment = generation_key.split("/")[1]
    if segment not in ("axis-x", "axis-y"):
        raise ValueError(f"not a D080 wall key: {generation_key!r}")
    return segment[-1]


def along_index(generation_key: str) -> int:
    """The coordinate index (0 for x, 1 for y) that runs along the wall."""
    return 0 if wall_axis(generation_key) == "x" else 1


def elevation_side(generation_key: str, x_line_ids: Sequence[str], y_line_ids: Sequence[str]) -> str:
    """ART-003 §4.2: walls along X on the first or last Y line are south or north; walls along Y on the
    first or last X line are west or east. Raises for a wall on no perimeter line (none conforms)."""
    line_id = generation_key.split("/")[2]
    if wall_axis(generation_key) == "x":
        if line_id == y_line_ids[0]:
            return "south"
        if line_id == y_line_ids[-1]:
            return "north"
    else:
        if line_id == x_line_ids[0]:
            return "west"
        if line_id == x_line_ids[-1]:
            return "east"
    raise ValueError(f"wall {generation_key!r} is on no perimeter grid line")


def outward_xy(side: str) -> list[float]:
    """The wall's outward unit normal in plan: away from the footprint."""
    return list(OUTWARD_XY[side])


# --- layer placement (ART-003 §5.1; D083) ------------------------------------------------------


@dataclass(frozen=True)
class LayerSpan:
    """A layer's signed interval along the wall's outward normal; 0 is the reference plane."""

    inner_m: float
    outer_m: float


def layer_spans(thicknesses: Sequence[float], framing_index: int) -> list[LayerSpan]:
    """D083: the framing layer is centered on the reference plane; earlier layers stack outward and later
    ones inward, in build-up order, evaluated from the framing layer outward exactly as ART-003 §5.1 writes it."""
    n = len(thicknesses)
    k = framing_index
    spans: list[LayerSpan | None] = [None] * n
    spans[k] = LayerSpan(-(thicknesses[k] / 2), thicknesses[k] / 2)
    for j in range(k - 1, -1, -1):
        inner = spans[j + 1].outer_m  # type: ignore[union-attr]
        spans[j] = LayerSpan(inner, inner + thicknesses[j])
    for j in range(k + 1, n):
        outer = spans[j - 1].inner_m  # type: ignore[union-attr]
        spans[j] = LayerSpan(outer - thicknesses[j], outer)
    return spans  # type: ignore[return-value]


def build_up_extents(thicknesses: Sequence[float], framing_index: int) -> tuple[float, float]:
    """(exterior_m, interior_m): how far the build-up extends outside and inside the reference plane."""
    spans = layer_spans(thicknesses, framing_index)
    return spans[0].outer_m, -spans[-1].inner_m


# --- framing faces (ART-003 §4.4; D071; ASM-001 §5.6) -------------------------------------------


def in_plane_m(piece_kind: str, actual_width_m: float, actual_depth_m: float) -> float:
    """D076: a piece's dimension in the wall plane, across its axis. A header's depth is vertical, in the plane."""
    return actual_depth_m if piece_kind == "HEADER" else actual_width_m


def through_wall_m(piece_kind: str, actual_width_m: float, actual_depth_m: float) -> float:
    """D076: a piece's dimension through the wall (along its outward normal)."""
    return actual_width_m if piece_kind == "HEADER" else actual_depth_m


@dataclass(frozen=True)
class FramingFace:
    """The rectangle a piece covers in its wall's plane: ``[u_lo, u_hi]`` along the wall (the global
    coordinate along the wall's axis) by ``[v_lo, v_hi]`` up it (global z)."""

    piece_kind: str
    u_lo: float
    u_hi: float
    v_lo: float
    v_hi: float


def framing_face(piece_kind: str, start_m: Sequence[float], end_m: Sequence[float], in_plane: float, along: int) -> FramingFace:
    """The piece's in-plane dimension centered on its axis, times its axis."""
    half = in_plane / 2
    if piece_kind in VERTICAL_KINDS:
        a = start_m[along]
        return FramingFace(piece_kind, a - half, a + half, min(start_m[2], end_m[2]), max(start_m[2], end_m[2]))
    z = start_m[2]
    return FramingFace(piece_kind, min(start_m[along], end_m[along]), max(start_m[along], end_m[along]), z - half, z + half)


def overlap_area(a: FramingFace, b: FramingFace) -> float | None:
    """The overlap of two faces, ``(min(hi) − max(lo))`` along times the same up, or None unless both exceed ε."""
    du = min(a.u_hi, b.u_hi) - max(a.u_lo, b.u_lo)
    dv = min(a.v_hi, b.v_hi) - max(a.v_lo, b.v_lo)
    if du > EPSILON_M and dv > EPSILON_M:
        return du * dv
    return None


@dataclass(frozen=True)
class FacePiece:
    """What the face-area rule reads of one piece (in the wall's piece key order)."""

    piece_kind: str
    start_m: Sequence[float]
    end_m: Sequence[float]
    in_plane_m: float
    length_m: float  # reference_length(start_m, end_m)


def framing_face_area(pieces: Sequence[FacePiece], along: int) -> float:
    """ART-003 §4.4: the wall's framing face area, with girt crossings counted once.

    1. The sum, in piece key order, of ``in_plane * length_m``;
    2. minus, in the order (girt piece, vertical piece), each overlap of a girt's face with a vertical
       piece's face where both the overlap's width and height exceed ε. ASM-001 §5.6 guarantees that
       no other two faces overlap.
    """
    total = 0.0
    for piece in pieces:
        total += piece.in_plane_m * piece.length_m
    faces = [framing_face(p.piece_kind, p.start_m, p.end_m, p.in_plane_m, along) for p in pieces]
    girts = [f for f in faces if f.piece_kind == "GIRT"]
    verticals = [f for f in faces if f.piece_kind in VERTICAL_KINDS]
    for girt in girts:
        for vertical in verticals:
            area = overlap_area(girt, vertical)
            if area is not None:
                total -= area
    return total
