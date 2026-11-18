"""Export the snapshot JSON Schema committed under docs/ (D028).

Usage (from backend/):
    uv run python -m homedesign.model.schema_export          # write the file
    uv run python -m homedesign.model.schema_export --check  # exit 1 if it is stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .schema import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "docs" / "architecture" / "schemas" / "snapshot.v1.schema.json"
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


def render_schema() -> str:
    return json.dumps(snapshot_json_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    rendered = render_schema()
    if "--check" in args:
        current = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else ""
        if current != rendered:
            print(f"{SCHEMA_PATH} is out of date; run without --check to regenerate.", file=sys.stderr)
            return 1
        return 0
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {SCHEMA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
