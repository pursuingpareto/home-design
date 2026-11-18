from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from homedesign.model.schema import Snapshot
from homedesign.timber import get_rule

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


_TEST_ID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-0000000000aa")


def regenerate(doc: dict[str, Any]) -> dict[str, Any]:
    """Test helper: replace the members with the rule's output for the doc's parameters.

    Keeps a member's ID when its key survives and gives new keys a test-only UUIDv5.
    (Production ID assignment is MODEL-003's job, D041.)
    """
    snapshot = Snapshot.model_validate(doc)
    grid = next(e for e in snapshot.entities if e.kind == "TimberGrid")
    generated = get_rule(grid.generation_rule_version).generate(snapshot)
    existing = {e["generation_key"]: e["id"] for e in doc["entities"] if e["kind"] == "TimberMember"}
    members = [
        {
            "id": existing.get(m.generation_key) or str(uuid.uuid5(_TEST_ID_NAMESPACE, m.generation_key)),
            "kind": "TimberMember",
            "schema_version": 1,
            **m.to_json(),
        }
        for m in generated
    ]
    doc["entities"] = [e for e in doc["entities"] if e["kind"] != "TimberMember"] + members
    frame = next(e for e in doc["entities"] if e["kind"] == "FrameSystem")
    frame["member_ids"] = [m["id"] for m in members]
    return doc
