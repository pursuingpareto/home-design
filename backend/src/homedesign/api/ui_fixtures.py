"""Frontend test fixtures captured from the real services (UI-001 §9, item 4).

The browser client's component tests render these payloads, so they must be exactly what the API
serves for Reference House 001. Regenerate and drift-check like the schemas:

    uv run python -m homedesign.api.ui_fixtures          # write frontend/tests/fixtures/reference-house-001.json
    uv run python -m homedesign.api.ui_fixtures --check  # exit 1 if it is stale
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from homedesign.assemblies.schedule import build_assembly_schedule, select_assembly_schedule
from homedesign.dependencies.registry import ARTIFACT_TYPES
from homedesign.model.canonical import canonical_snapshot
from homedesign.project import MemoryStore, ProjectService

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = REPO_ROOT / "frontend" / "tests" / "fixtures" / "reference-house-001.json"

PROJECT_ID = "6f1e2d3c-4b5a-4987-8a6b-5c4d3e2f1a0b"
PRICE_BOOK_ID = "7a2b3c4d-5e6f-4a1b-9c2d-3e4f5a6b7c8d"
ACTOR_ID = "00000000-0000-4000-8000-000000000001"
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
KEY = bytes(32)  # fixture-only signing key; tokens in the file are never valid on a real server
BOOK = {
    "currency": "USD", "as_of": "2026-11-01", "source": "Fixture supplier quote", "geography": "Chittenden County, VT",
    # One row per timber line (D053), connection type (ART-002 §7), wall layer, and wall framing line (ART-003 §7) of
    # Reference House 001 v3, so this estimate is complete. Assembly rows are priced per square meter.
    "rows": [
        {"key": key, "unit": "each" if key.startswith("connection.") else "m2" if key.startswith("assembly.") else "m", "unit_price_minor": price}
        for key, price in (
            ("assembly.straw-bale.bales", 2200), ("assembly.straw-bale.clay-plaster", 3500), ("assembly.straw-bale.lime-plaster", 4200),
            ("connection.BRIDLE", 6500), ("connection.HOUSED_DOVETAIL", 3800), ("connection.PEGGED_MORTISE_TENON", 4500),
            ("timber.BEAM.8x12", 4725), ("timber.FLOOR_JOIST.4x8", 1200), ("timber.KNEE_BRACE.4x6", 900), ("timber.POST.8x8", 3150),
            ("timber.PRINCIPAL_RAFTER.8x10", 3900), ("timber.PURLIN.6x8", 2350), ("timber.SILL.8x8", 3150),
            ("wallframing.BUCK_HEAD.1.5x18", 1900), ("wallframing.BUCK_JAMB.1.5x18", 1900), ("wallframing.BUCK_SILL.1.5x18", 1900),
        )
    ],
}


# UI-004 §14: test-only declared values, so the browser's thermal display is tested on figures the backend's
# own builder computes. Nothing in a project or the template changes; no value here describes a real material.
TEST_ONLY = {"source": "TEST ONLY: UI-004 fixture value", "date": "2026-11-22", "note": "Not a property of any material."}
TEST_DECLARED = {
    # layer name: (conductivity W/(m·K), resistance m²·K/W, vapor permeance kg/(Pa·s·m²)); one of the first two
    "lime-plaster": (0.7, None, 1.5e-10),
    "bales": (0.06, None, 5.0e-10),
    "clay-plaster": (None, 0.03, 2.0e-10),
}
TEST_FRAMING_CONDUCTIVITY = 0.12


def _declared(value: float | None) -> dict[str, Any] | None:
    return None if value is None else {"value": value} | TEST_ONLY


def declared_schedule(snapshot: Any) -> dict[str, Any]:
    """The created house's assembly schedule with test-only declared values on every layer and framing material."""
    selection = select_assembly_schedule(snapshot)
    for definition in selection["definitions"]:
        for layer in definition["layers"]:
            k, r, permeance = TEST_DECLARED[layer["name"]]
            layer["thermal_conductivity_w_m_k"] = _declared(k)
            layer["thermal_resistance_m2_k_w"] = _declared(r)
            layer["vapor_permeance_kg_pa_s_m2"] = _declared(permeance)
            if layer["framing"] is not None:
                layer["framing"]["framing_thermal_conductivity_w_m_k"] = _declared(TEST_FRAMING_CONDUCTIVITY)
    return build_assembly_schedule(selection)


def _created(project_id: str = PROJECT_ID) -> tuple[ProjectService, str]:
    svc = ProjectService(MemoryStore(), token_key=KEY, project_id_factory=lambda: project_id)
    created = svc.create_project({"command_id": "00000000-0000-4000-8000-0000000000c1", "type": "CreateReferenceProject", "args": {}}, actor_id=ACTOR_ID, now=NOW)
    return svc, created.revision_id


def build() -> dict[str, Any]:
    svc, head = _created()
    art = lambda kind: svc.artifacts.get_artifact(PROJECT_ID, kind, now=NOW)  # noqa: E731
    envelopes = {kind: art(kind) for kind in ARTIFACT_TYPES}
    snapshot = json.loads(canonical_snapshot(svc.get_revision(PROJECT_ID, head)))
    footprint = next(e for e in snapshot["entities"] if e["kind"] == "Footprint")
    width_command = {
        "command_id": "00000000-0000-4000-8000-0000000000c2", "project_id": PROJECT_ID, "base_revision_id": head,
        "type": "SetFootprintDimensions", "args": {"width_m": 12.192, "depth_m": footprint["depth_m"]},
    }
    preview = svc.preview(PROJECT_ID, width_command, actor_id=ACTOR_ID, now=NOW).body
    # UI-003 §11: a frame change (eave braces off) and a connection-type change, from the created house.
    frame = next(e for e in snapshot["entities"] if e["kind"] == "FrameSystem")
    frame_command = {
        "command_id": "00000000-0000-4000-8000-0000000000c3", "project_id": PROJECT_ID, "base_revision_id": head,
        "type": "SetFrameParameters", "args": frame["parameters"] | {"knee_braces_eave": False},
    }
    frame_preview = svc.preview(PROJECT_ID, frame_command, actor_id=ACTOR_ID, now=NOW).body
    type_command = {
        "command_id": "00000000-0000-4000-8000-0000000000c4", "project_id": PROJECT_ID, "base_revision_id": head,
        "type": "SetConnectionType", "args": {"junction_class": "joist-beam", "connection_type": "JOIST_HANGER"},
    }
    type_preview = svc.preview(PROJECT_ID, type_command, actor_id=ACTOR_ID, now=NOW).body
    # UI-004 §14: SetWallAssembly to stud infill, and re-identifying y1 (removed, then a new line at 0.5).
    systems = [e for e in snapshot["entities"] if e["kind"] == "WallSystem"]
    stud = next(e for e in snapshot["entities"] if e["kind"] == "AssemblyDefinition" and e["family"] == "STUD_INFILL")
    assert systems and systems[0]["default_assembly_definition_id"] != stud["id"]
    assembly_command = {
        "command_id": "00000000-0000-4000-8000-0000000000c5", "project_id": PROJECT_ID, "base_revision_id": head,
        "type": "SetWallAssembly", "args": {"assembly_definition_id": stud["id"]},
    }
    assembly_preview = svc.preview(PROJECT_ID, assembly_command, actor_id=ACTOR_ID, now=NOW).body
    grid = next(e for e in snapshot["entities"] if e["kind"] == "TimberGrid")
    y_first, y_last = grid["y_lines"][0], grid["y_lines"][-1]
    reidentify_command = {
        "command_id": "00000000-0000-4000-8000-0000000000c6", "project_id": PROJECT_ID, "base_revision_id": head,
        "type": "SetTimberGrid",
        "args": {"x_lines": grid["x_lines"], "y_lines": [y_first, {"fraction": 0.5}, y_last]},
    }
    reidentify_preview = svc.preview(PROJECT_ID, reidentify_command, actor_id=ACTOR_ID, now=NOW).body
    declared = declared_schedule(svc.get_revision(PROJECT_ID, head))
    # The stud infill envelopes come from a second, identical project, so this one's head and history stay as captured.
    studs, studs_head = _created()
    token = studs.preview(PROJECT_ID, assembly_command, actor_id=ACTOR_ID, now=NOW).body["preview_token"]
    studs.commit(PROJECT_ID, assembly_command, token, actor_id=ACTOR_ID, now=NOW)
    assert studs_head == head
    stud_infill_envelopes = {kind: studs.artifacts.get_artifact(PROJECT_ID, kind, now=NOW) for kind in ARTIFACT_TYPES}
    manifest = svc.artifacts.manifest(PROJECT_ID)
    with patch("homedesign.project.service.uuid.uuid4", return_value=uuid.UUID(PRICE_BOOK_ID)):  # random in production
        svc.set_price_book(PROJECT_ID, BOOK, actor_id=ACTOR_ID, now=NOW)
    return {
        "_note": "Generated by `uv run python -m homedesign.api.ui_fixtures` (UI-001 §9). Do not edit by hand.",
        "project": svc.get_project(PROJECT_ID) | {"permissions": ["read", "write"]},
        "revisions": svc.list_revisions(PROJECT_ID),
        "snapshot": snapshot,
        "manifest": manifest,
        "envelopes": envelopes,
        "estimate_complete": art("preliminary_estimate"),
        "price_book": svc.get_price_book(PROJECT_ID),
        "width_command": width_command,
        "width_preview": preview,
        "frame_command": frame_command,
        "frame_preview": frame_preview,
        "type_command": type_command,
        "type_preview": type_preview,
        "assembly_command": assembly_command,
        "assembly_preview": assembly_preview,
        "stud_infill_envelopes": stud_infill_envelopes,
        "reidentify_command": reidentify_command,
        "reidentify_preview": reidentify_preview,
        "assembly_schedule_declared": {
            "_note": "TEST ONLY (UI-004 §14): the created house's assembly schedule payload, built by the backend's builder with "
                     "test-only declared values on every layer and framing material. No project or template carries these values.",
            "payload": declared,
        },
    }


def render() -> str:
    return json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = render()
    if "--check" in args:
        current = FIXTURE_PATH.read_text(encoding="utf-8") if FIXTURE_PATH.exists() else ""
        if current != text:
            print(f"{FIXTURE_PATH} is out of date; run without --check to regenerate.", file=sys.stderr)
            return 1
        return 0
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {FIXTURE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
