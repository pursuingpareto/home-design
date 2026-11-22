"""Export the JSON Schemas and the OpenAPI document committed under docs/ (D028).

Usage (from backend/):
    uv run python -m homedesign.model.schema_export          # write snapshot, command, artifact schemas, openapi.v1.json, and the connection catalog
    uv run python -m homedesign.model.schema_export --check  # exit 1 if it is stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .schema import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "docs" / "architecture" / "schemas"
SCHEMA_PATH = SCHEMA_DIR / "snapshot.v3.schema.json"  # named after the model schema version (MODEL-005 §4.5)
COMMANDS_SCHEMA_PATH = SCHEMA_DIR / "commands.v1.schema.json"
ARTIFACTS_SCHEMA_PATH = SCHEMA_DIR / "artifacts.v1.schema.json"
OPENAPI_PATH = SCHEMA_DIR / "openapi.v1.json"
CONNECTION_CATALOG_PATH = SCHEMA_DIR / "connection-catalog.json"  # D062: the editor's catalog (UI-003 §10)
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def snapshot_json_schema() -> dict[str, Any]:
    schema = Snapshot.model_json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["description"] = (
        "Stage 1 (syntactic) contract for model schema version 3 snapshots. Generated from the Pydantic "
        "models in backend/src/homedesign/model/schema.py; do not edit by hand. "
        "Referential, geometric, and domain rules are in docs/architecture/building-model.md §6."
    )
    return schema


def commands_json_schema() -> dict[str, Any]:
    from .commands.envelope import COMMAND_ADAPTER

    schema = COMMAND_ADAPTER.json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["title"] = "Command envelopes, model schema version 3 (MODEL-003, MODEL-005, MODEL-006)"
    schema["description"] = (
        "Stage 1 (syntactic) contract for command envelopes, discriminated by `type`. "
        "Generated from backend/src/homedesign/model/commands/envelope.py; do not edit by hand. "
        "Semantics: docs/architecture/interfaces.md §2–4 and §7.1."
    )
    return schema


def artifacts_json_schema() -> dict[str, Any]:
    """Envelope and manifest (ART-001), the five payloads (GEOM-001, EST-001, ART-003), and the price book."""
    from pydantic.json_schema import models_json_schema

    from homedesign.assemblies.schedule import AssemblySchedulePayload
    from homedesign.dependencies.envelope import ArtifactEnvelope, Manifest
    from homedesign.estimating.estimate import PreliminaryEstimatePayload
    from homedesign.estimating.pricebook import PriceBook
    from homedesign.geometry.payloads import Mesh3dPayload, Plan2dPayload
    from homedesign.timber.schedule import TimberSchedulePayload

    models = (ArtifactEnvelope, Manifest, Plan2dPayload, Mesh3dPayload, TimberSchedulePayload, AssemblySchedulePayload, PreliminaryEstimatePayload, PriceBook)
    _, schema = models_json_schema([(m, "validation") for m in models])
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["title"] = "VS-01 artifact envelope and manifest (ART-001)"
    schema["description"] = (
        "Definitions for artifacts.md §2-3, generated from backend/src/homedesign/dependencies/envelope.py; "
        "do not edit by hand. Validate an envelope against #/$defs/ArtifactEnvelope, a manifest against #/$defs/Manifest, payloads against #/$defs/Plan2dPayload, Mesh3dPayload, TimberSchedulePayload, AssemblySchedulePayload, and PreliminaryEstimatePayload, and price books against #/$defs/PriceBook."
    )
    return schema


def _render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_schema() -> str:
    return _render(snapshot_json_schema())


def render_commands_schema() -> str:
    return _render(commands_json_schema())


def render_artifacts_schema() -> str:
    return _render(artifacts_json_schema())


def openapi_document() -> dict[str, Any]:
    """The API-001 OpenAPI document. Built from an app with throwaway settings; nothing is served."""
    from homedesign.api.app import create_app
    from homedesign.api.settings import Settings

    return create_app(Settings(preview_key=bytes(32), store="memory")).openapi()


def render_openapi() -> str:
    return _render(openapi_document())


def connection_catalog() -> dict[str, Any]:
    """The D054 catalog for clients (D062, UI-003 §10): the version, each class's default and
    alternative in D054 order, and each type's family and description. The server still validates
    every command (D028); this only limits what an editor offers."""
    from . import connections as c

    return {
        "description": (
            "The VS-02 connection catalog (D054), generated from backend/src/homedesign/model/connections.py "
            "by homedesign.model.schema_export; do not edit by hand. Types are representational only (AC2-07)."
        ),
        "catalog_version": c.CATALOG_VERSION,
        "junction_classes": [
            {"junction_class": jc, "default": c.DEFAULTS[jc], "alternative": c.ALTERNATIVES[jc]} for jc in c.JUNCTION_CLASSES
        ],
        "connection_types": [
            {"connection_type": t, "family": c.FAMILIES[t], "description": c.DESCRIPTIONS[t]} for t in c.CONNECTION_TYPES
        ],
    }


def render_connection_catalog() -> str:
    return _render(connection_catalog())


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    outputs = {
        SCHEMA_PATH: render_schema(),
        COMMANDS_SCHEMA_PATH: render_commands_schema(),
        ARTIFACTS_SCHEMA_PATH: render_artifacts_schema(),
        OPENAPI_PATH: render_openapi(),
        CONNECTION_CATALOG_PATH: render_connection_catalog(),
    }
    if "--check" in args:
        stale = [p for p, text in outputs.items() if (p.read_text(encoding="utf-8") if p.exists() else "") != text]
        for path in stale:
            print(f"{path} is out of date; run without --check to regenerate.", file=sys.stderr)
        return 1 if stale else 0
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
