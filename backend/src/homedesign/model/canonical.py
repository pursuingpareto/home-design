"""Canonical snapshot bytes and fingerprints (D029, D030)."""

from __future__ import annotations

import hashlib
from typing import Any

from .jcs import canonical_json
from .schema import Snapshot


def canonical_snapshot_value(snapshot: Snapshot) -> dict[str, Any]:
    """The snapshot as a JSON value with ``entities`` sorted by ``id`` (D030)."""
    value = snapshot.model_dump(mode="json")
    value["entities"] = sorted(value["entities"], key=lambda entity: entity["id"])
    return value


def canonical_snapshot(snapshot: Snapshot) -> bytes:
    """RFC 8785 bytes of the canonical snapshot."""
    return canonical_json(canonical_snapshot_value(snapshot))


def fingerprint(value: Any) -> str:
    """``sha256:`` + lowercase hex SHA-256 of the RFC 8785 bytes of ``value``."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def snapshot_fingerprint(snapshot: Snapshot) -> str:
    return "sha256:" + hashlib.sha256(canonical_snapshot(snapshot)).hexdigest()
