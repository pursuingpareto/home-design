"""Revision store interface and an in-memory implementation (MODEL-004 §3).

Both implementations must pass the same contract tests. Rows are plain value objects;
snapshots are stored as JSON values (``Snapshot.model_dump(mode="json")``).
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ProjectRow:
    project_id: str
    head_revision_id: str
    head_sequence: int
    created_at: datetime
    created_by: str


@dataclass(frozen=True)
class RevisionRow:
    revision_id: str
    project_id: str
    parent_revision_id: str | None
    sequence: int
    model_schema_version: int
    snapshot: dict[str, Any]
    fingerprint: str
    created_at: datetime


@dataclass(frozen=True)
class OperationRow:
    operation_id: str
    project_id: str | None
    actor_id: str
    command_id: str | None
    command_type: str | None
    command: Any
    command_hash: str | None
    base_revision_id: str | None
    result: str  # committed | noop | rejected
    rejection_code: str | None
    revision_id: str | None
    classification: str | None
    classification_version: str | None
    created_at: datetime


@dataclass(frozen=True)
class ArtifactRow:
    """A derived artifact (ART-001 §5). Recomputable; not part of the audit trail."""

    project_id: str
    revision_id: str
    artifact_type: str
    input_fingerprint: str
    generator_id: str
    generator_version: str
    status: str  # CURRENT | UNAVAILABLE | FAILED
    payload: Any
    error: Any
    warnings: list
    generated_at: datetime


class StoreTx(Protocol):
    def get_project(self, project_id: str, *, lock: bool = False) -> ProjectRow | None: ...
    def list_projects(self, created_by: str) -> list[ProjectRow]: ...  # newest first, then project_id
    def get_revision(self, project_id: str, revision_id: str) -> RevisionRow | None: ...
    def list_revisions(self, project_id: str) -> list[tuple[RevisionRow, OperationRow | None]]: ...
    def find_operation(self, project_id: str, actor_id: str, command_id: str) -> OperationRow | None: ...
    def find_creation(self, actor_id: str, command_id: str) -> OperationRow | None: ...
    def list_operations(self, project_id: str) -> list[OperationRow]: ...  # append order
    def insert_project(self, row: ProjectRow) -> None: ...
    def insert_revision(self, row: RevisionRow) -> None: ...
    def insert_operation(self, row: OperationRow) -> None: ...
    def set_head(self, project_id: str, revision_id: str, sequence: int) -> None: ...
    def get_artifacts(self, revision_id: str, artifact_type: str) -> list[ArtifactRow]: ...
    def put_artifact(self, row: ArtifactRow) -> None: ...  # keeps an existing row with the same key
    def delete_artifacts(self, revision_id: str) -> None: ...  # derived data may be discarded
    def get_price_book(self, project_id: str) -> dict | None: ...  # latest version, or None
    def insert_price_book(self, row: dict) -> None: ...  # append-only versions


class RevisionStore(Protocol):
    def transaction(self) -> Any:  # context manager yielding StoreTx; commits on success
        ...


class DuplicateCommand(Exception):
    """A concurrent transaction committed the same idempotency key first."""


# --- in-memory -------------------------------------------------------------------


class _MemoryTx:
    def __init__(self, store: "MemoryStore") -> None:
        self.store = store
        self.projects = dict(store.projects)
        self.revisions = dict(store.revisions)
        self.operations = list(store.operations)
        self.artifacts = dict(store.artifacts)
        self.price_books = dict(store.price_books)

    def get_project(self, project_id, *, lock=False):
        return self.projects.get(project_id)

    def list_projects(self, created_by):
        rows = sorted((p for p in self.projects.values() if p.created_by == created_by), key=lambda p: p.project_id)
        return sorted(rows, key=lambda p: p.created_at, reverse=True)  # stable: ties stay in project_id order

    def get_revision(self, project_id, revision_id):
        row = self.revisions.get(revision_id)
        return copy.deepcopy(row) if row is not None and row.project_id == project_id else None

    def list_revisions(self, project_id):
        rows = sorted((r for r in self.revisions.values() if r.project_id == project_id), key=lambda r: r.sequence)
        by_revision = {o.revision_id: o for o in self.operations if o.result == "committed"}
        return [(copy.deepcopy(r), by_revision.get(r.revision_id)) for r in rows]

    def find_operation(self, project_id, actor_id, command_id):
        return next(
            (o for o in self.operations if o.result in ("committed", "noop") and o.command_type != "CreateReferenceProject"
             and (o.project_id, o.actor_id, o.command_id) == (project_id, actor_id, command_id)),
            None,
        )

    def find_creation(self, actor_id, command_id):
        return next(
            (o for o in self.operations if o.result == "committed" and o.command_type == "CreateReferenceProject"
             and (o.actor_id, o.command_id) == (actor_id, command_id)),
            None,
        )

    def list_operations(self, project_id):
        return [o for o in self.operations if o.project_id == project_id]

    def insert_project(self, row):
        if row.project_id in self.projects:
            raise ValueError("duplicate project")
        self.projects[row.project_id] = row

    def insert_revision(self, row):
        if row.revision_id in self.revisions:
            raise ValueError("revisions are append-only")
        if any(r.project_id == row.project_id and r.sequence == row.sequence for r in self.revisions.values()):
            raise ValueError("duplicate sequence")
        self.revisions[row.revision_id] = copy.deepcopy(row)

    def insert_operation(self, row):
        if any(o.operation_id == row.operation_id for o in self.operations):
            raise ValueError("operations are append-only")
        if row.result in ("committed", "noop") and row.command_type != "CreateReferenceProject":
            if self.find_operation(row.project_id, row.actor_id, row.command_id):
                raise DuplicateCommand()
        if row.result == "committed" and row.command_type == "CreateReferenceProject":
            if self.find_creation(row.actor_id, row.command_id):
                raise DuplicateCommand()
        self.operations.append(copy.deepcopy(row))

    def set_head(self, project_id, revision_id, sequence):
        self.projects[project_id] = replace(self.projects[project_id], head_revision_id=revision_id, head_sequence=sequence)

    def get_artifacts(self, revision_id, artifact_type):
        return [copy.deepcopy(r) for (rev, kind, _), r in self.artifacts.items() if (rev, kind) == (revision_id, artifact_type)]

    def put_artifact(self, row):
        self.artifacts.setdefault((row.revision_id, row.artifact_type, row.input_fingerprint), copy.deepcopy(row))

    def delete_artifacts(self, revision_id):
        self.artifacts = {k: v for k, v in self.artifacts.items() if k[0] != revision_id}

    def get_price_book(self, project_id):
        versions = [v for (pid, _), v in self.price_books.items() if pid == project_id]
        return copy.deepcopy(max(versions, key=lambda r: r["version"])) if versions else None

    def insert_price_book(self, row):
        key = (row["project_id"], row["version"])
        if key in self.price_books:
            raise ValueError("price books are append-only")
        self.price_books[key] = copy.deepcopy(row)


class MemoryStore:
    """Serializable in-memory store: one transaction at a time, applied atomically on success."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.projects: dict[str, ProjectRow] = {}
        self.revisions: dict[str, RevisionRow] = {}
        self.operations: list[OperationRow] = []
        self.artifacts: dict[tuple[str, str, str], ArtifactRow] = {}
        self.price_books: dict[tuple[str, int], dict] = {}

    @contextmanager
    def transaction(self) -> Iterator[_MemoryTx]:
        with self._lock:
            tx = _MemoryTx(self)
            yield tx
            self.projects, self.revisions, self.operations = tx.projects, tx.revisions, tx.operations
            self.artifacts = tx.artifacts
            self.price_books = tx.price_books

    def corrupt_for_test(self, revision_id: str, snapshot: dict[str, Any]) -> None:
        """Test hook: replace a stored snapshot without updating its fingerprint (§8 test 14)."""
        self.revisions[revision_id] = replace(self.revisions[revision_id], snapshot=snapshot)
