from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "docs" / "reference-projects" / "vermont-timber-house" / "fixture.snapshot.json"
VECTORS_PATH = REPO_ROOT / "tests" / "vectors" / "jcs" / "vectors.json"
SCHEMA_PATH = REPO_ROOT / "docs" / "architecture" / "schemas" / "snapshot.v1.schema.json"
BUILDING_MODEL_DOC = REPO_ROOT / "docs" / "architecture" / "building-model.md"

FIXTURE_BYTES = FIXTURE_PATH.read_bytes()
FIXTURE: dict[str, Any] = json.loads(FIXTURE_BYTES)


def fresh_fixture() -> dict[str, Any]:
    return copy.deepcopy(FIXTURE)


def entities_of(doc: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [e for e in doc["entities"] if e["kind"] == kind]


def index_of(doc: dict[str, Any], entity_id: str) -> int:
    return next(i for i, e in enumerate(doc["entities"]) if e["id"] == entity_id)


def epath(entity: dict[str, Any], *rest: str | int) -> str:
    """D036 path for a fixture entity addressed by its (usable) ID."""
    text = f"entities[{entity['id']}]"
    for step in rest:
        text += f"[{step}]" if isinstance(step, int) else f".{step}"
    return text


@pytest.fixture
def doc() -> dict[str, Any]:
    return fresh_fixture()
