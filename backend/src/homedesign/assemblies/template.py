"""Reference House 001 v3 template records for walls (ASM-001 §7–8; D072, D081).

Illustrative values for a test house, not a specification: nothing here is checked or claimed
(AC-08). Every property value is ``null`` (D071, D072). Lengths are exact conversions
(1 in = 0.0254 m, 1 ft = 0.3048 m; D026).

``timber/fixture.py`` composes these records with the frame and calls both rules (ASM-001 §8.3).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

WALL_RULE = "vs02b-walls-1"
DEFAULT_ASSEMBLY = "straw-bale"  # D072, D068

# (nominal_label, actual_width_m in the wall plane, actual_depth_m). The header's depth is vertical (D076).
SECTIONS = [
    ("2x6", 0.0381, 0.1397),  # studs, kings, jacks, cripples, rough sills, and girts
    ("2x8", 0.0381, 0.18415),  # headers
    ("1.5x18", 0.0381, 0.4572),  # bucks
]

# (slug for the fixture ID name, name, species). grade, density_kg_m3, and provenance are null.
MATERIALS = [
    ("lime-plaster", "Lime plaster", None),
    ("straw", "Straw", None),
    ("clay-plaster", "Clay plaster", None),
    ("wood-siding", "Wood siding", None),
    ("sheathing", "Sheathing", None),
    ("spruce-pine-fir", "Spruce-pine-fir", "spruce-pine-fir"),
    ("dense-pack-cellulose", "Dense-pack cellulose", None),
    ("gypsum-board", "Gypsum board", None),
]

# D081, stored exactly as written there.
STRAW_BALE_NOTE = (
    "Straw bales laid flat in courses between the posts, from sill to beam, with a 1½\" × 18\" buck at every opening. "
    "Lime plaster outside and clay plaster inside, applied to the bales. "
    "Illustrative build-up for a test house, not a specification."
)
STRAW_BALE_DETAILS = [
    "Bale moisture protection at the sill: a raised base and a capillary break below the first course.",
    "Exterior lime plaster and its rain protection (overhangs, splash zone, or a rain screen) for the site's exposure.",
    "Plaster junctions at posts, beams, and bucks (cracking and air leakage).",
    "Flashing and sill pans at window and door bucks.",
    "Bale moisture content at installation, and drying through both plasters.",
]
STUD_INFILL_NOTE = (
    "2×6 studs at 24\" on center between the posts, one mid-height girt let in across them, "
    "and kings and headers at every opening (jacks above 4'-0\"). "
    "Dense-pack cellulose between the studs, sheathing and wood siding outside, gypsum board inside. "
    "Illustrative build-up for a test house, not a specification."
)
STUD_INFILL_DETAILS = [
    "Water-resistive barrier and rain-screen gap behind the siding.",
    "Interior vapor control for the climate zone.",
    "Air barrier continuity where posts and beams interrupt the sheathing.",
    "Flashing and sill pans at rough openings.",
    "Dense-pack cellulose density and settling.",
]

FT = 0.3048
# D072 openings (rough openings, D069): (kind, width_m, height_m, sill_height_m, offset_m). Centered
# means offset_m = (W - w) / 2 in a 12' bay, stored as the exact decimal (ASM-001 §8.1).
DOOR = ("DOOR", 0.9144, 2.032, 0.0, 1.3716)  # 3'-0" × 6'-8"
WINDOW_5 = ("WINDOW", 1.524, 1.2192, 0.9144, 1.0668)  # 5'-0" × 4'-0", sill 3'-0"
WINDOW_3 = ("WINDOW", 0.9144, 1.2192, 0.9144, 1.3716)  # 3'-0" × 4'-0", sill 3'-0"
OPENING_AT = {
    "wall/axis-x/y0/x1-x2/level-0": DOOR,  # the middle Level 0 bay of the south wall
    "wall/axis-x/y0/x0-x1/level-0": WINDOW_5,  # the outer Level 0 bays of the south wall
    "wall/axis-x/y0/x2-x3/level-0": WINDOW_5,
}  # every other wall: WINDOW_3


def _null_values() -> dict[str, None]:
    return {"thermal_conductivity_w_m_k": None, "thermal_resistance_m2_k_w": None, "vapor_permeance_kg_pa_s_m2": None}


def _layer(name: str, function: str, material_id: str, thickness_m: float, framing: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"name": name, "function": function, "material_id": material_id, "thickness_m": thickness_m, **_null_values(), "framing": framing}


def records(record: Callable[..., dict[str, Any]], fixture_id: Callable[[str], str]) -> dict[str, Any]:
    """The template's sections, materials, and definitions, keyed for the fixture script.

    ``record(kind, id, **fields)`` builds a record; ``fixture_id(name)`` gives a fixed fixture ID.
    """
    sections = {
        label: record("Section", fixture_id("section/" + label), shape="rectangular", actual_width_m=width, actual_depth_m=depth, nominal_label=label)
        for label, width, depth in SECTIONS
    }
    materials = {
        slug: record("Material", fixture_id("material/" + slug), name=name, species=species, grade=None, density_kg_m3=None, provenance=None)
        for slug, name, species in MATERIALS
    }
    m = {slug: material["id"] for slug, material in materials.items()}
    s = {label: section["id"] for label, section in sections.items()}
    straw_bale = record(
        "AssemblyDefinition",
        fixture_id("assembly/straw-bale"),
        family="STRAW_BALE",
        label="straw-bale",
        installation_note=STRAW_BALE_NOTE,
        unverified_climate_details=list(STRAW_BALE_DETAILS),
        layers=[
            _layer("lime-plaster", "FINISH", m["lime-plaster"], 0.0381),
            _layer("bales", "FRAMING", m["straw"], 0.4572, {
                "type": "BUCK",
                "framing_material_id": m["spruce-pine-fir"],
                "framing_thermal_conductivity_w_m_k": None,
                "buck_section_id": s["1.5x18"],
                "girt_count": 0,
            }),
            _layer("clay-plaster", "FINISH", m["clay-plaster"], 0.0254),
        ],
    )
    stud_infill = record(
        "AssemblyDefinition",
        fixture_id("assembly/stud-infill"),
        family="STUD_INFILL",
        label="stud-infill",
        installation_note=STUD_INFILL_NOTE,
        unverified_climate_details=list(STUD_INFILL_DETAILS),
        layers=[
            _layer("siding", "FINISH", m["wood-siding"], 0.01905),
            _layer("sheathing", "SHEATHING", m["sheathing"], 0.0127),
            _layer("framing", "FRAMING", m["dense-pack-cellulose"], 0.1397, {
                "type": "STUD",
                "framing_material_id": m["spruce-pine-fir"],
                "framing_thermal_conductivity_w_m_k": None,
                "stud_section_id": s["2x6"],
                "stud_spacing_m": 0.6096,  # 24"
                "girt_count": 1,
                "girt_section_id": s["2x6"],
                "header_section_id": s["2x8"],
                "jack_threshold_width_m": 1.2192,  # 4'-0"
            }),
            _layer("gypsum-board", "FINISH", m["gypsum-board"], 0.0127),
        ],
    )
    return {"sections": sections, "materials": materials, "definitions": {"straw-bale": straw_bale, "stud-infill": stud_infill}}


def opening_for(wall_key: str) -> tuple[str, float, float, float, float]:
    """The D072 opening of a reference-house wall: (kind, width, height, sill, offset)."""
    return OPENING_AT.get(wall_key, WINDOW_3)
