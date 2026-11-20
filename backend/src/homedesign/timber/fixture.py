"""Build Reference House 001 v2: the fixture and the packaged template (TIMBER-002 §7).

Usage (from backend/):
    uv run python -m homedesign.timber.fixture          # write both files
    uv run python -m homedesign.timber.fixture --check  # exit 1 if either is stale

The non-generated records hold the D025 and D053 values, with fixed IDs. Members are the
exact output of ``vs02-frame-1`` (no hand-entered decimals), with IDs derived from their keys.
Not an engineered design: every value is illustrative design intent (D025, D053, AC-08).
"""

from __future__ import annotations

import json
import math
import sys
import uuid
from pathlib import Path
from typing import Any

from homedesign.model.connections import DEFAULTS as CONNECTION_DEFAULTS
from homedesign.model.limits import MODEL_SCHEMA_VERSION, RECORD_SCHEMA_VERSIONS
from homedesign.model.schema import Snapshot
from homedesign.model.validation import validate_value

from .rules import get_rule

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = REPO_ROOT / "docs" / "reference-projects" / "vermont-timber-house" / "fixture.snapshot.json"
TEMPLATE_PATH = REPO_ROOT / "backend" / "src" / "homedesign" / "model" / "commands" / "templates" / "reference-house-001.json"

# IDs for records added in version 2 (and for members) are UUIDv5 names under this fixed namespace.
FIXTURE_NAMESPACE = uuid.UUID("2f0c9d34-6a1e-4b7f-9c2d-5e8a1b3f7c60")

RULE = "vs02-frame-1"
MATERIAL_ID = "d0055c4c-1014-56ac-95ed-86f72b05df37"


def _id(name: str) -> str:
    return str(uuid.uuid5(FIXTURE_NAMESPACE, "reference-house-001/" + name))


# D025 sections keep their IDs; D053 adds four.
SECTIONS = [
    ("bf84459d-6300-5def-9665-e7ee995d816f", "8x8", 0.2032, 0.2032),
    ("e87a56f9-76cb-58a8-b8ee-4722c031a40b", "8x12", 0.2032, 0.3048),
    (_id("section/4x8"), "4x8", 0.1016, 0.2032),
    (_id("section/8x10"), "8x10", 0.2032, 0.254),
    (_id("section/6x8"), "6x8", 0.1524, 0.2032),
    (_id("section/4x6"), "4x6", 0.1016, 0.1524),
]
ROLE_SECTION = {  # D025, D053
    "POST": "8x8",
    "BEAM": "8x12",
    "SILL": "8x8",
    "FLOOR_JOIST": "4x8",
    "PRINCIPAL_RAFTER": "8x10",
    "PURLIN": "6x8",
    "KNEE_BRACE": "4x6",
}


def _record(kind: str, record_id: str, **fields: Any) -> dict[str, Any]:
    return {"id": record_id, "kind": kind, "schema_version": RECORD_SCHEMA_VERSIONS[kind], **fields}


def build() -> dict[str, Any]:
    section_ids = {label: section_id for section_id, label, _, _ in SECTIONS}
    footprint = _record("Footprint", "9ba359f1-6354-5019-9b3f-d15f8e53523b", origin_m=[0.0, 0.0], width_m=10.9728, depth_m=7.3152, rotation_rad=0.0)
    level0 = _record("Level", "bb53ff6a-c109-5f1a-a6fb-e16fd8d7f4ed", index=0, elevation_m=0.0, story_height_m=3.048)
    level1 = _record("Level", "85281672-fc1f-5723-a2e1-f85e25b1d336", index=1, elevation_m=3.048, story_height_m=2.7432)
    roof = _record("GableRoof", "488040a1-800d-5b05-a1d6-84d22c8f3929", ridge_axis="X", pitch_rad=math.atan(0.75), eave_overhang_m=0.6096, ridge_offset_m=0.0)
    grid = _record(
        "TimberGrid",
        "4223b175-1758-59fc-95fc-073ee00eaf99",
        x_lines=[{"id": "x0", "fraction": 0.0}, {"id": "x1", "fraction": 1 / 3}, {"id": "x2", "fraction": 2 / 3}, {"id": "x3", "fraction": 1.0}],
        y_lines=[{"id": "y0", "fraction": 0.0}, {"id": "y1", "fraction": 0.5}, {"id": "y2", "fraction": 1.0}],
        generation_rule_version=RULE,
    )
    sections = [
        _record("Section", section_id, shape="rectangular", actual_width_m=width, actual_depth_m=depth, nominal_label=label)
        for section_id, label, width, depth in SECTIONS
    ]
    material = _record("Material", MATERIAL_ID, name="Eastern white pine", species="eastern-white-pine", grade=None, density_kg_m3=None, provenance=None)
    frame = _record(
        "FrameSystem",
        "00f66257-d812-58c6-8b69-f90baae2e70e",
        grid_id=grid["id"],
        member_ids=[],
        generation_mode="DETERMINISTIC_RULE",
        member_defaults={role: {"section_id": section_ids[label], "material_id": MATERIAL_ID} for role, label in ROLE_SECTION.items()},
        parameters={  # D053
            "joist_spacing_m": 0.6096,  # 24"
            "purlins_per_slope": 2,
            "knee_brace_leg_m": 0.9144,  # 3'-0"
            "knee_braces_level_1": True,
            "knee_braces_eave": True,
        },
        connection_ids=[],
        connection_defaults=dict(CONNECTION_DEFAULTS),  # D054
    )
    doc = {
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "project_id": "17ac32e0-0b3b-518e-b568-adf98f41bcd0",
        "revision_id": "01b311c6-7a51-528d-befe-b2e592819b66",
        "parent_revision_id": None,
        "created_at": "2026-11-16T00:00:00Z",
        "building": _record(
            "Building",
            "b4d57ae8-a2e8-568d-a2d8-0f83ef42682f",
            name="Reference House 001",
            footprint_id=footprint["id"],
            level_ids=[level0["id"], level1["id"]],
            roof_id=roof["id"],
            frame_system_id=frame["id"],
        ),
        "entities": [footprint, level0, level1, roof, grid, *sections, material, frame],
    }
    generated = get_rule(RULE).generate(Snapshot.model_validate(doc))
    members = [_record("TimberMember", _id("member/" + m.generation_key), **m.to_json()) for m in generated]
    frame["member_ids"] = [m["id"] for m in members]
    doc["entities"].extend(members)
    result = validate_value(doc)
    if not result.valid:
        raise SystemExit(f"generated fixture does not validate: {result.to_dict()}")
    return doc


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render(build())
    paths = (FIXTURE_PATH, TEMPLATE_PATH)
    if "--check" in argv:
        stale = [p for p in paths if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"stale: {p.relative_to(REPO_ROOT)} (run: uv run python -m homedesign.timber.fixture)", file=sys.stderr)
        return 1 if stale else 0
    for p in paths:
        p.write_text(text, encoding="utf-8")
        print(f"wrote {p.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
