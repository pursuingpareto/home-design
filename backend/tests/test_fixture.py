"""Reference House 001 fixture: validation, round trip, golden fingerprint, schema (MODEL-001 §7.1)."""

from __future__ import annotations

import json
import random

import jsonschema
import pytest

from conftest import FIXTURE, FIXTURE_BYTES, SCHEMA_PATH, VECTORS_PATH, fresh_fixture
from homedesign.model import (
    Snapshot,
    canonical_json,
    canonical_snapshot,
    snapshot_fingerprint,
    validate_bytes,
    validate_value,
)
from homedesign.model.schema_export import render_schema

GOLDEN = next(s for s in json.loads(VECTORS_PATH.read_text())["snapshots"] if s["name"] == "reference-house-001")


def _sorted_raw(doc):
    doc = json.loads(json.dumps(doc))
    doc["entities"].sort(key=lambda e: e["id"])
    return doc


def test_fixture_is_valid():
    result = validate_bytes(FIXTURE_BYTES)
    assert result.to_dict() == {"valid": True, "code": None, "issues": []}
    assert isinstance(result.snapshot, Snapshot)
    # 13 non-generated records (D025 plus four D053 sections), 193 members (TIMBER-002 §7),
    # and 312 connections (CONN-001 §6).
    assert len(result.snapshot.entities) == 518


def test_round_trip_is_lossless():
    snapshot = validate_bytes(FIXTURE_BYTES).snapshot
    expected = canonical_json(_sorted_raw(FIXTURE))
    assert canonical_snapshot(snapshot) == expected
    # dump -> parse -> canonical is a fixed point (MODEL-001 §5.4)
    redumped = validate_value(snapshot.model_dump(mode="json")).snapshot
    assert canonical_snapshot(redumped) == expected
    # every double survives unchanged
    for raw, model in zip(sorted(FIXTURE["entities"], key=lambda e: e["id"]),
                          sorted(snapshot.model_dump(mode="json")["entities"], key=lambda e: e["id"])):
        assert raw == model


@pytest.mark.parametrize("seed", [1, 2, 3, 42, 2026])
def test_entity_order_does_not_change_canonical_form(seed):
    doc = fresh_fixture()
    random.Random(seed).shuffle(doc["entities"])
    shuffled = validate_value(doc).snapshot
    original = validate_bytes(FIXTURE_BYTES).snapshot
    assert canonical_snapshot(shuffled) == canonical_snapshot(original)
    assert snapshot_fingerprint(shuffled) == snapshot_fingerprint(original)


def test_golden_fingerprint_matches_independent_engine():
    """The fingerprint must equal the one computed by the ECMAScript reference generator.

    A change here means the fixture or canonicalization changed and needs a decision.
    """
    snapshot = validate_bytes(FIXTURE_BYTES).snapshot
    assert len(canonical_snapshot(snapshot)) == GOLDEN["canonical_bytes"]
    assert snapshot_fingerprint(snapshot) == GOLDEN["fingerprint"]


def test_committed_schema_is_current():
    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_schema(), (
        "Run `uv run python -m homedesign.model.schema_export` and commit the result."
    )


def test_fixture_validates_against_committed_schema_independently():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(FIXTURE)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["building"].pop("footprint_id"),
        lambda d: d.__setitem__("model_schema_version", 1),  # version 1 is retired (D055)
        lambda d: d["entities"][0].__setitem__("color", "red"),
        lambda d: d.__setitem__("project_id", d["project_id"].upper()),
        lambda d: d["entities"][0].__setitem__("width_m", "36"),
    ],
    ids=["missing-field", "schema-version", "unknown-field", "uppercase-uuid", "wrong-type"],
)
def test_committed_schema_rejects_stage1_errors(mutate):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    doc = fresh_fixture()
    mutate(doc)
    assert not jsonschema.Draft202012Validator(schema).is_valid(doc)
