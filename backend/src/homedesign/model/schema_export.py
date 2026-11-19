"""Export the snapshot JSON Schema committed under docs/ (D028).

Usage (from backend/):
    uv run python -m homedesign.model.schema_export          # write snapshot, command, and artifact schemas
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
SCHEMA_PATH = SCHEMA_DIR / "snapshot.v1.schema.json"
COMMANDS_SCHEMA_PATH = SCHEMA_DIR / "commands.v1.schema.json"
ARTIFACTS_SCHEMA_PATH = SCHEMA_DIR / "artifacts.v1.schema.json"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def snapshot_json_schema() -> dict[str, Any]:
    schema = Snapshot.model_json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["description"] = (
        "Stage 1 (syntactic) contract for VS-01 snapshots. Generated from the Pydantic "
        "models in backend/src/homedesign/model/schema.py; do not edit by hand. "
        "Referential, geometric, and domain rules are in docs/architecture/building-model.md §6."
    )
    return schema


def commands_json_schema() -> dict[str, Any]:
    from .commands.envelope import COMMAND_ADAPTER

    schema = COMMAND_ADAPTER.json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["title"] = "VS-01 command envelopes (MODEL-003)"
    schema["description"] = (
        "Stage 1 (syntactic) contract for VS-01 command envelopes, discriminated by `type`. "
        "Generated from backend/src/homedesign/model/commands/envelope.py; do not edit by hand. "
        "Semantics: docs/architecture/interfaces.md §2–4 and §7.1."
    )
    return schema


def artifacts_json_schema() -> dict[str, Any]:
    """Envelope and manifest (ART-001), the four payloads (GEOM-001, EST-001), and the price book."""
    from pydantic.json_schema import models_json_schema

    from homedesign.dependencies.envelope import ArtifactEnvelope, Manifest
    from homedesign.estimating.estimate import PreliminaryEstimatePayload
    from homedesign.estimating.pricebook import PriceBook
    from homedesign.geometry.payloads import Mesh3dPayload, Plan2dPayload
    from homedesign.timber.schedule import TimberSchedulePayload

    models = (ArtifactEnvelope, Manifest, Plan2dPayload, Mesh3dPayload, TimberSchedulePayload, PreliminaryEstimatePayload, PriceBook)
    _, schema = models_json_schema([(m, "validation") for m in models])
    schema["$schema"] = JSON_SCHEMA_DIALECT
    schema["title"] = "VS-01 artifact envelope and manifest (ART-001)"
    schema["description"] = (
        "Definitions for artifacts.md §2-3, generated from backend/src/homedesign/dependencies/envelope.py; "
        "do not edit by hand. Validate an envelope against #/$defs/ArtifactEnvelope, a manifest against #/$defs/Manifest, payloads against #/$defs/Plan2dPayload, Mesh3dPayload, TimberSchedulePayload, and PreliminaryEstimatePayload, and price books against #/$defs/PriceBook."
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


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    outputs = {SCHEMA_PATH: render_schema(), COMMANDS_SCHEMA_PATH: render_commands_schema(), ARTIFACTS_SCHEMA_PATH: render_artifacts_schema()}
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
