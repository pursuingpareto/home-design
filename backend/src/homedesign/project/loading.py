"""Load a stored snapshot, verifying its fingerprint (MODEL-004 §4.6)."""

from __future__ import annotations

from homedesign.model.canonical import snapshot_fingerprint
from homedesign.model.paths import is_canonical_uuid
from homedesign.model.schema import Snapshot

from .errors import CorruptRevision, NotFound


def load_snapshot(tx, project_id: str, revision_id: str) -> Snapshot:
    row = tx.get_revision(project_id, revision_id) if is_canonical_uuid(revision_id) else None
    if row is None:
        raise NotFound("Revision not found.")
    snapshot = Snapshot.model_validate(row.snapshot)
    if snapshot_fingerprint(snapshot) != row.fingerprint:
        raise CorruptRevision(f"Stored revision {revision_id} does not match its fingerprint.")
    return snapshot
