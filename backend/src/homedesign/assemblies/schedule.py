"""`assembly_schedule` payload, selector, and builder (artifacts.md §7A; ART-003 §4, §8.1; D070, D071, D082).

One row per wall, opening, and wall framing piece; aggregates per definition, layer, framing kind and
section, and opening kind; the assumption lines; and D071's thermal figures (method `parallel-path-1`).
Areas are reference areas and lengths reference-axis lengths, evaluated exactly as written in IEEE-754
doubles. The builder reads only its selection (D061): framing face areas are computed by the selector,
which reads piece positions without selecting them.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from homedesign.dependencies.registry import Derivation, DerivationContext, Outcome
from homedesign.model.schema import AssemblyFamily, DeclaredValue, LayerFunction, OpeningKind, PieceKind, SafeInt, Snapshot, Uuid
from homedesign.timber.schedule import Assumption, reference_length

from .thermal import Paths, path_resistances, thermal_section, wall_figures
from .walls import FacePiece, along_index, elevation_side, framing_face_area, in_plane_m

# ART-003 §4.7, in this order. The thermal method's labels are in `thermal.method.notes`, not here, so the
# estimate, which copies these, carries no thermal text.
ASSUMPTIONS = (
    {"code": "WALLS_ONLY",
     "message": "Walls only: perimeter infill walls between the frame's posts. Gable-end walls, roof, and floor assemblies are not included."},
    {"code": "REFERENCE_AREA",
     "message": "Wall areas are reference areas: bay length between grid stations times story height between datums, less rough openings. "
                "Member faces, knee braces, and the framing around openings are not deducted."},
    {"code": "REFERENCE_AXIS_LENGTH", "message": "Wall framing lengths are reference-axis distances, not cut lengths."},
    {"code": "FILL_NET_OF_FRAMING",
     "message": "The framing layer's fill (bales or cellulose) is quantified as each wall's net area less its framing's face area. "
                "Bale counts are not given."},
    {"code": "NO_PLATES_OR_NOTCHES",
     "message": "No bottom or top plates are generated, and the let-in notches where girts cross studs are not modeled."},
    {"code": "FASTENINGS_NOT_COUNTED",
     "message": "Wall framing fastenings and attachments (stud ends, girt to post, headers, and opening framing) are not modeled or counted."},
    {"code": "JACK_THRESHOLD_DECLARED",
     "message": "Jack studs follow the definition's declared jack threshold width, which is not derived from any building code."},
    {"code": "OPENINGS_ARE_VOIDS",
     "message": "Doors and windows are rough openings: no unit, frame, glazing, or hardware is counted, and the estimate does not price them."},
    {"code": "FIT_TO_AXES_ONLY",
     "message": "Openings are checked for fit against member axes and datums only; clearance to member faces is not checked."},
)

ElevationSide = Literal["south", "north", "west", "east"]


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


# --- payload -------------------------------------------------------------------------------


class AssemblyUnits(_Strict):
    length: Literal["m"] = "m"
    area: Literal["m2"] = "m2"
    volume: Literal["m3"] = "m3"
    count: Literal["1"] = "1"
    thermal_transmittance: Literal["W/(m2.K)"] = "W/(m2.K)"
    thermal_resistance: Literal["m2.K/W"] = "m2.K/W"
    heat_flow: Literal["W/K"] = "W/K"


class StudFramingSummary(_Strict):
    type: Literal["STUD"]
    framing_material_id: Uuid
    framing_material_name: str
    framing_thermal_conductivity_w_m_k: DeclaredValue | None
    stud_section: str
    stud_spacing_m: float
    girt_count: SafeInt
    girt_section: str | None
    header_section: str
    jack_threshold_width_m: float


class BuckFramingSummary(_Strict):
    type: Literal["BUCK"]
    framing_material_id: Uuid
    framing_material_name: str
    framing_thermal_conductivity_w_m_k: DeclaredValue | None
    buck_section: str
    girt_count: SafeInt


class DefinitionLayer(_Strict):
    """A layer as stored, with its material's name and, for the framing layer, its framing by section label."""

    name: str
    function: LayerFunction
    material_id: Uuid
    material_name: str
    thickness_m: float
    thermal_conductivity_w_m_k: DeclaredValue | None
    thermal_resistance_m2_k_w: DeclaredValue | None
    vapor_permeance_kg_pa_s_m2: DeclaredValue | None
    framing: Annotated[Union[StudFramingSummary, BuckFramingSummary], Field(discriminator="type")] | None


class DefinitionEntry(_Strict):
    assembly_definition_id: Uuid
    label: str
    family: AssemblyFamily
    installation_note: str
    unverified_climate_details: list[str]
    total_thickness_m: float
    layers: Annotated[list[DefinitionLayer], Field(min_length=1)]  # exterior to interior


class AssemblyWallRow(_Strict):
    wall_id: Uuid
    generation_key: str
    level_id: Uuid
    level_index: SafeInt
    elevation_side: ElevationSide
    assembly_definition_id: Uuid
    assembly_label: str
    length_m: float
    height_m: float
    gross_area_m2: float
    opening_area_m2: float
    net_area_m2: float
    framing_face_area_m2: float
    framing_fraction: float
    u_value_w_m2_k: float | None
    r_value_m2_k_w: float | None
    ua_w_k: float | None


class AssemblyOpeningRow(_Strict):
    """No position (ART-003 §4.3): positions belong to the views."""

    opening_id: Uuid
    opening_kind: OpeningKind
    wall_id: Uuid
    wall_key: str
    width_m: float
    height_m: float
    area_m2: float
    has_jacks: bool


class WallFramingRow(_Strict):
    piece_id: Uuid
    generation_key: str
    wall_id: Uuid
    piece_kind: PieceKind
    opening_id: Uuid | None
    nominal_section: str
    section_id: Uuid
    material_id: Uuid
    species: str | None
    grade: str | None
    length_m: float
    quantity: Literal[1] = 1


class DefinitionAggregate(_Strict):
    assembly_label: str
    wall_count: SafeInt
    opening_count: SafeInt
    gross_area_m2: float
    opening_area_m2: float
    net_area_m2: float


class LayerAggregate(_Strict):
    assembly_label: str
    layer: str
    function: LayerFunction
    material_name: str
    thickness_m: float
    area_m2: float
    volume_m3: float


class FramingAggregate(_Strict):
    piece_kind: PieceKind
    nominal_section: str
    count: Annotated[SafeInt, Field(ge=1)]
    total_length_m: float


class OpeningAggregate(_Strict):
    opening_kind: OpeningKind
    count: Annotated[SafeInt, Field(ge=1)]
    area_m2: float


class AssemblyTotals(_Strict):
    wall_count: SafeInt
    opening_count: SafeInt
    gross_area_m2: float
    opening_area_m2: float
    net_area_m2: float
    framing_face_area_m2: float


class MissingInput(_Strict):
    assembly_label: str
    layer: str
    fields: Annotated[list[str], Field(min_length=1)]


class PathFigure(_Strict):
    r_value_m2_k_w: float | None
    u_value_w_m2_k: float | None
    missing_inputs: list[MissingInput]


class AreaWeightedFigure(_Strict):
    net_area_m2: float
    ua_w_k: float | None
    u_value_w_m2_k: float | None
    r_value_m2_k_w: float | None
    missing_inputs: list[MissingInput]


class ThermalDefinition(_Strict):
    assembly_label: str
    center_of_cavity: PathFigure
    framing_path: PathFigure
    parallel_path: AreaWeightedFigure


class ThermalMethod(_Strict):
    id: Literal["parallel-path-1"]
    notes: list[str]


class ThermalFigures(_Strict):
    method: ThermalMethod
    definitions: list[ThermalDefinition]
    all_walls: AreaWeightedFigure


class AssemblySchedulePayload(_Strict):
    model_config = ConfigDict(title="assembly_schedule payload (artifacts.md §7A)")

    units: AssemblyUnits = AssemblyUnits()
    quantity_basis: Literal["reference"] = "reference"
    assumptions: list[Assumption]
    definitions: list[DefinitionEntry]
    walls: list[AssemblyWallRow]
    openings: list[AssemblyOpeningRow]
    wall_framing: list[WallFramingRow]
    definition_aggregates: list[DefinitionAggregate]
    layer_aggregates: list[LayerAggregate]
    framing_aggregates: list[FramingAggregate]
    opening_aggregates: list[OpeningAggregate]
    totals: AssemblyTotals
    thermal: ThermalFigures


# --- selector ------------------------------------------------------------------------------


def _framing_summary(framing: Any, by_id: dict[str, Any]) -> dict[str, Any]:
    label = lambda section_id: None if section_id is None else by_id[section_id].nominal_label  # noqa: E731
    common = {
        "type": framing.type,
        "framing_material_id": framing.framing_material_id,
        "framing_material_name": by_id[framing.framing_material_id].name,
        "framing_thermal_conductivity_w_m_k": _declared(framing.framing_thermal_conductivity_w_m_k),
    }
    if framing.type == "STUD":
        return common | {
            "stud_section": label(framing.stud_section_id),
            "stud_spacing_m": framing.stud_spacing_m,
            "girt_count": framing.girt_count,
            "girt_section": label(framing.girt_section_id),
            "header_section": label(framing.header_section_id),
            "jack_threshold_width_m": framing.jack_threshold_width_m,
        }
    return common | {"buck_section": label(framing.buck_section_id), "girt_count": framing.girt_count}


def _declared(value: Any) -> dict[str, Any] | None:
    return None if value is None else value.model_dump(mode="json")


def select_definition(definition: Any, by_id: dict[str, Any]) -> dict[str, Any]:
    """Everything §4.5 prints of a definition, with material names and section labels resolved."""
    return {
        "assembly_definition_id": definition.id,
        "label": definition.label,
        "family": definition.family,
        "installation_note": definition.installation_note,
        "unverified_climate_details": list(definition.unverified_climate_details),
        "layers": [
            {
                "name": layer.name,
                "function": layer.function,
                "material_id": layer.material_id,
                "material_name": by_id[layer.material_id].name,
                "thickness_m": layer.thickness_m,
                "thermal_conductivity_w_m_k": _declared(layer.thermal_conductivity_w_m_k),
                "thermal_resistance_m2_k_w": _declared(layer.thermal_resistance_m2_k_w),
                "vapor_permeance_kg_pa_s_m2": _declared(layer.vapor_permeance_kg_pa_s_m2),
                "framing": None if layer.framing is None else _framing_summary(layer.framing, by_id),
            }
            for layer in definition.layers
        ],
    }


class WallRecords:
    """The wall records the selectors resolve, from a snapshot that passed validation (shared by the views)."""

    def __init__(self, snapshot: Snapshot) -> None:
        by_id: dict[str, Any] = {e.id: e for e in snapshot.entities}
        self.by_id = by_id
        frame = by_id[snapshot.building.frame_system_id]
        grid = by_id[frame.grid_id]
        self.x_line_ids = [line.id for line in grid.x_lines]
        self.y_line_ids = [line.id for line in grid.y_lines]
        self.walls = sorted((e for e in snapshot.entities if e.kind == "Wall"), key=lambda w: _utf16(w.generation_key))
        self.pieces = sorted((e for e in snapshot.entities if e.kind == "WallFramingPiece"), key=lambda p: _utf16(p.generation_key))
        self.wall_of_piece = {piece_id: wall for wall in self.walls for piece_id in wall.framing_ids}
        self.pieces_of_wall: dict[str, list[Any]] = {wall.id: [] for wall in self.walls}
        for piece in self.pieces:  # key order
            self.pieces_of_wall[self.wall_of_piece[piece.id].id].append(piece)
        wall_by_id = {wall.id: wall for wall in self.walls}
        self.wall_by_id = wall_by_id
        self.openings = sorted(
            (e for e in snapshot.entities if e.kind == "Opening"), key=lambda o: (_utf16(wall_by_id[o.wall_id].generation_key), o.id)
        )

    def side(self, wall: Any) -> str:
        return elevation_side(wall.generation_key, self.x_line_ids, self.y_line_ids)

    def definition(self, wall: Any) -> Any:
        return self.by_id[wall.assembly_definition_id]

    def face_area(self, wall: Any) -> float:
        pieces = []
        for piece in self.pieces_of_wall[wall.id]:
            section = self.by_id[piece.section_id]
            pieces.append(FacePiece(
                piece.piece_kind, piece.start_m, piece.end_m,
                in_plane_m(piece.piece_kind, section.actual_width_m, section.actual_depth_m),
                reference_length(piece.start_m, piece.end_m),
            ))
        return framing_face_area(pieces, along_index(wall.generation_key))


def select_assembly_schedule(snapshot: Snapshot) -> dict[str, Any]:
    """ART-003 §8.1: per wall its length (not its axis) and framing face area; per opening its size and
    `has_jacks`; per piece its length, section, and material; per definition in use what §4.5 prints."""
    r = WallRecords(snapshot)
    levels = {level_id: r.by_id[level_id].index for level_id in snapshot.building.level_ids}
    walls = [
        {
            "id": wall.id,
            "generation_key": wall.generation_key,
            "level_id": wall.level_id,
            "level_index": levels[wall.level_id],
            "elevation_side": r.side(wall),
            "assembly_definition_id": wall.assembly_definition_id,
            "length_m": reference_length(wall.start_m, wall.end_m),
            "height_m": wall.height_m,
            "framing_face_area_m2": r.face_area(wall),
        }
        for wall in r.walls
    ]
    jacked = {p.opening_id for p in r.pieces if p.piece_kind == "JACK"}
    openings = [
        {"id": o.id, "opening_kind": o.opening_kind, "wall_id": o.wall_id, "width_m": o.width_m, "height_m": o.height_m, "has_jacks": o.id in jacked}
        for o in r.openings
    ]
    pieces = []
    for piece in r.pieces:
        section, material = r.by_id[piece.section_id], r.by_id[piece.material_id]
        pieces.append({
            "id": piece.id,
            "generation_key": piece.generation_key,
            "wall_id": r.wall_of_piece[piece.id].id,
            "piece_kind": piece.piece_kind,
            "opening_id": piece.opening_id,
            "section_id": section.id,
            "nominal_label": section.nominal_label,
            "material_id": material.id,
            "species": material.species,
            "grade": material.grade,
            "length_m": reference_length(piece.start_m, piece.end_m),
        })
    in_use = {wall.assembly_definition_id for wall in r.walls}
    definitions = sorted((select_definition(r.by_id[i], r.by_id) for i in in_use), key=lambda d: _utf16(d["label"]))
    return {"walls": walls, "openings": openings, "wall_framing": pieces, "definitions": definitions}


# --- builder -------------------------------------------------------------------------------


def build_assembly_schedule(selection: dict[str, Any]) -> dict[str, Any]:
    """The `assembly_schedule` payload from `select_assembly_schedule`'s selection (its only model input, D061)."""
    definitions = []
    for d in selection["definitions"]:  # sorted by label
        total = 0.0
        for layer in d["layers"]:
            total += layer["thickness_m"]
        definitions.append({**d, "total_thickness_m": total, "layers": [dict(layer) for layer in d["layers"]]})
    definition_by_id = {d["assembly_definition_id"]: d for d in definitions}
    wall_by_id = {w["id"]: w for w in selection["walls"]}
    paths: dict[str, Paths] = {d["label"]: path_resistances(d) for d in definitions}

    openings = []
    opening_area: dict[str, float] = {w["id"]: 0.0 for w in selection["walls"]}
    opening_count: dict[str, int] = {w["id"]: 0 for w in selection["walls"]}
    for o in selection["openings"]:  # by wall key, then ID
        area = o["width_m"] * o["height_m"]
        openings.append({
            "opening_id": o["id"],
            "opening_kind": o["opening_kind"],
            "wall_id": o["wall_id"],
            "wall_key": wall_by_id[o["wall_id"]]["generation_key"],
            "width_m": o["width_m"],
            "height_m": o["height_m"],
            "area_m2": area,
            "has_jacks": o["has_jacks"],
        })
        opening_area[o["wall_id"]] += area
        opening_count[o["wall_id"]] += 1

    walls = []
    for w in selection["walls"]:  # by key
        definition = definition_by_id[w["assembly_definition_id"]]
        gross = w["length_m"] * w["height_m"]
        net = gross - opening_area[w["id"]]
        face = w["framing_face_area_m2"]
        f = face / net
        walls.append({
            "wall_id": w["id"],
            "generation_key": w["generation_key"],
            "level_id": w["level_id"],
            "level_index": w["level_index"],
            "elevation_side": w["elevation_side"],
            "assembly_definition_id": w["assembly_definition_id"],
            "assembly_label": definition["label"],
            "length_m": w["length_m"],
            "height_m": w["height_m"],
            "gross_area_m2": gross,
            "opening_area_m2": opening_area[w["id"]],
            "net_area_m2": net,
            "framing_face_area_m2": face,
            "framing_fraction": f,
            **wall_figures(paths[definition["label"]], f, net),
        })

    framing_rows = []
    framing_totals: dict[tuple[str, str], list] = {}
    for p in selection["wall_framing"]:  # by key
        framing_rows.append({
            "piece_id": p["id"],
            "generation_key": p["generation_key"],
            "wall_id": p["wall_id"],
            "piece_kind": p["piece_kind"],
            "opening_id": p["opening_id"],
            "nominal_section": p["nominal_label"],
            "section_id": p["section_id"],
            "material_id": p["material_id"],
            "species": p["species"],
            "grade": p["grade"],
            "length_m": p["length_m"],
            "quantity": 1,
        })
        entry = framing_totals.setdefault((p["piece_kind"], p["nominal_label"]), [0, 0.0])
        entry[0] += 1
        entry[1] += p["length_m"]  # summed in piece row order

    definition_aggregates = []
    layer_aggregates = []
    for d in definitions:
        own = [w for w in walls if w["assembly_definition_id"] == d["assembly_definition_id"]]
        gross = opening = net = fill = 0.0
        count = 0
        for w in own:  # row order
            gross += w["gross_area_m2"]
            opening += w["opening_area_m2"]
            net += w["net_area_m2"]
            fill += w["net_area_m2"] - w["framing_face_area_m2"]  # D082: the fill, net of framing
            count += opening_count[w["wall_id"]]
        definition_aggregates.append({"assembly_label": d["label"], "wall_count": len(own), "opening_count": count,
                                      "gross_area_m2": gross, "opening_area_m2": opening, "net_area_m2": net})
        for layer in d["layers"]:  # build-up order, exterior to interior
            area = fill if layer["framing"] is not None else net
            layer_aggregates.append({
                "assembly_label": d["label"],
                "layer": layer["name"],
                "function": layer["function"],
                "material_name": layer["material_name"],
                "thickness_m": layer["thickness_m"],
                "area_m2": area,
                "volume_m3": area * layer["thickness_m"],
            })

    framing_aggregates = [
        {"piece_kind": kind, "nominal_section": label, "count": count, "total_length_m": total}
        for (kind, label), (count, total) in sorted(framing_totals.items(), key=lambda kv: (_utf16(kv[0][0]), _utf16(kv[0][1])))
    ]
    by_kind: dict[str, list] = {}
    for o in openings:  # row order
        entry = by_kind.setdefault(o["opening_kind"], [0, 0.0])
        entry[0] += 1
        entry[1] += o["area_m2"]
    opening_aggregates = [{"opening_kind": kind, "count": n, "area_m2": area} for kind, (n, area) in sorted(by_kind.items(), key=lambda kv: _utf16(kv[0]))]

    gross = opening = net = face = 0.0
    for w in walls:
        gross += w["gross_area_m2"]
        opening += w["opening_area_m2"]
        net += w["net_area_m2"]
        face += w["framing_face_area_m2"]
    payload = {
        "assumptions": [dict(a) for a in ASSUMPTIONS],
        "definitions": definitions,
        "walls": walls,
        "openings": openings,
        "wall_framing": framing_rows,
        "definition_aggregates": definition_aggregates,
        "layer_aggregates": layer_aggregates,
        "framing_aggregates": framing_aggregates,
        "opening_aggregates": opening_aggregates,
        "totals": {"wall_count": len(walls), "opening_count": len(openings), "gross_area_m2": gross, "opening_area_m2": opening,
                   "net_area_m2": net, "framing_face_area_m2": face},
        "thermal": thermal_section(paths, definitions, walls),
    }
    return AssemblySchedulePayload.model_validate(payload).model_dump(mode="json")


def _derive(context: DerivationContext) -> Outcome:
    return Outcome("CURRENT", build_assembly_schedule(context.selection))


ASSEMBLY_SCHEDULE = Derivation("assembly_schedule", "assembly-schedule-vs02b", "1", select_assembly_schedule, _derive)
