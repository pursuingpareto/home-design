"""Project service: create, preview, commit, and reads over a RevisionStore (MODEL-004 §4).

Commit order (D047): idempotency → base revision → command validation → preview token.
Every commit attempt that reaches a project is audited; rejected attempts are recorded in
the same transaction before the error is raised (MODEL-004 §4.5).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from homedesign.model.canonical import snapshot_fingerprint
from homedesign.model.commands import CandidateChange, command_hash, parse_command, propose, propose_create
from homedesign.model.paths import is_canonical_uuid
from homedesign.model.schema import Snapshot
from homedesign.model.validation import ValidationResult

from . import tokens
from .errors import (
    CommandRejected,
    CorruptRevision,
    IdempotencyConflict,
    NotFound,
    PreviewRequired,
    ProjectError,
    RevisionConflict,
)
from .store import DuplicateCommand, OperationRow, ProjectRow, RevisionRow, RevisionStore
from .loading import load_snapshot
from .timefmt import format_timestamp

ARTIFACT_TYPES = ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate")  # artifacts.md §1
PREVIEW_TTL = timedelta(minutes=15)  # D047


@dataclass(frozen=True)
class CommitResult:
    """interfaces.md §4 response for a commit or project creation."""

    http_status: int
    project_id: str
    revision_id: str
    parent_revision_id: str | None
    operation_id: str
    sequence: int
    is_noop: bool
    replayed: bool = False
    artifact_statuses: dict[str, str] | None = None  # filled by ART-001; MISSING until derived

    def body(self) -> dict[str, Any]:
        body = {
            "project_id": self.project_id,
            "revision_id": self.revision_id,
            "parent_revision_id": self.parent_revision_id,
            "operation_id": self.operation_id,
            "sequence": self.sequence,
            "is_noop": self.is_noop,
            "artifact_statuses": dict(self.artifact_statuses or {t: "MISSING" for t in ARTIFACT_TYPES}),
        }
        if self.replayed:
            body["replayed"] = True
        return body


@dataclass(frozen=True)
class PreviewResult:
    change: CandidateChange
    preview_token: str
    expires_at: str
    body: dict[str, Any] = field(repr=False)


@dataclass
class _Failure:
    error: ProjectError


class ProjectService:
    def __init__(
        self,
        store: RevisionStore,
        *,
        token_key: bytes,
        project_id_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
        preview_ttl: timedelta = PREVIEW_TTL,
        registry: Any = None,
    ) -> None:
        if not token_key:
            raise ValueError("token_key must be a non-empty secret (D047)")
        from homedesign.dependencies.artifacts import ArtifactService  # lazy: the packages import each other's modules

        self.store = store
        self.artifacts = ArtifactService(store, registry)
        self._key = token_key
        self._new_project_id = project_id_factory
        self._ttl = preview_ttl

    # --- create --------------------------------------------------------------

    def create_project(self, command: Any, *, actor_id: str, now: datetime) -> CommitResult:
        _check_actor(actor_id)
        try:
            with self.store.transaction() as tx:
                outcome = self._create_in(tx, command, actor_id, now)
        except DuplicateCommand:
            # A concurrent identical creation won the race; replay its result.
            return self.create_project(command, actor_id=actor_id, now=now)
        if isinstance(outcome, _Failure):
            raise outcome.error  # the audit row (project_id null) is already committed
        return self._with_artifacts(outcome, now)

    def _create_in(self, tx, command, actor_id, now) -> CommitResult | _Failure:
        def fail(error: ProjectError, parsed: Any = None) -> _Failure:
            tx.insert_operation(_rejected_row(None, actor_id, parsed, None, error.code, now))
            return _Failure(error)

        parsed, error = parse_command(command)
        if error is not None:
            return fail(CommandRejected(error))
        existing = tx.find_creation(actor_id, parsed.command_id)
        if existing is not None:
            if existing.command_hash != command_hash(parsed):
                return fail(IdempotencyConflict("command_id was already used for a different creation command."), parsed)
            return _replayed(tx, existing)
        project_id = self._new_project_id()
        proposed = propose_create(command, project_id=project_id, actor_id=actor_id, at=format_timestamp(now))
        if not proposed.accepted:
            return fail(CommandRejected(proposed.rejection), parsed)
        change = proposed.change
        tx.insert_project(ProjectRow(project_id, change.revision_id, 1, now, actor_id))
        tx.insert_revision(_revision_row(change, project_id, 1, now))
        tx.insert_operation(_operation_row(change, project_id, actor_id, parsed, None, "committed", now))
        return CommitResult(201, project_id, change.revision_id, None, change.operation_id, 1, False)

    # --- preview -------------------------------------------------------------

    def preview(self, project_id: str, command: Any, *, actor_id: str, now: datetime) -> PreviewResult:
        """Run the command against the head without writing anything (interfaces.md §9, test 2)."""
        _check_actor(actor_id)
        with self.store.transaction() as tx:
            project = _project(tx, project_id, lock=False)
            head = _load(tx, project_id, project.head_revision_id)
            target = _undo_target(tx, project_id, command)
        proposed = propose(head, command, actor_id=actor_id, at=format_timestamp(now), target=target)
        if not proposed.accepted:
            raise _rejection_error(proposed.rejection)
        change = proposed.change
        expires = now + self._ttl
        token = tokens.issue(
            self._key,
            project_id=project_id,
            actor_id=actor_id,
            base_revision_id=head.revision_id,
            command_hash=change.command_hash,
            expires_at=expires,
        )
        body = change.to_preview_dict() | {"preview_token": token, "expires_at": format_timestamp(expires)}
        return PreviewResult(change, token, format_timestamp(expires), body)

    # --- commit --------------------------------------------------------------

    def commit(
        self,
        project_id: str,
        command: Any,
        preview_token: str | None = None,
        *,
        actor_id: str,
        now: datetime,
    ) -> CommitResult:
        _check_actor(actor_id)
        try:
            with self.store.transaction() as tx:
                outcome = self._commit_in(tx, project_id, command, preview_token, actor_id, now)
        except DuplicateCommand:
            return self.commit(project_id, command, preview_token, actor_id=actor_id, now=now)
        if isinstance(outcome, _Failure):
            raise outcome.error  # the audit row is already committed
        return self._with_artifacts(outcome, now)

    def _with_artifacts(self, result: CommitResult, now: datetime) -> CommitResult:
        """Derive after a new revision (dependencies.md §6); otherwise report current statuses."""
        if result.http_status == 201:
            statuses = self.artifacts.derive_revision(result.project_id, result.revision_id, now=now)
        else:
            statuses = self.artifacts.statuses(result.project_id, result.revision_id)
        return replace(result, artifact_statuses=statuses)

    def _commit_in(self, tx, project_id, command, preview_token, actor_id, now) -> CommitResult | _Failure:
        project = _project(tx, project_id, lock=True)

        def fail(error: ProjectError, parsed: Any = None) -> _Failure:
            tx.insert_operation(_rejected_row(project_id, actor_id, parsed, project.head_revision_id, error.code, now))
            return _Failure(error)

        parsed, error = parse_command(command)
        if error is not None:
            return fail(CommandRejected(error))
        digest = command_hash(parsed)

        # 1. Idempotency.
        existing = tx.find_operation(project_id, actor_id, parsed.command_id)
        if existing is not None:
            if existing.command_hash != digest:
                return fail(IdempotencyConflict("command_id was already used for a different command."), parsed)
            return _replayed(tx, existing)

        # 2. Base revision.
        base = getattr(parsed, "base_revision_id", None)
        if base is not None and base != project.head_revision_id:
            return fail(RevisionConflict("base_revision_id is not the project head."), parsed)

        # 3. Command validation (deterministic: same IDs and diff as the preview, D041).
        head = _load(tx, project_id, project.head_revision_id)
        proposed = propose(head, command, actor_id=actor_id, at=format_timestamp(now), target=_undo_target(tx, project_id, command))
        if not proposed.accepted:
            return fail(_rejection_error(proposed.rejection), parsed)
        change = proposed.change

        # 4. Preview token (D047).
        try:
            if preview_token is not None:
                tokens.verify(
                    preview_token,
                    self._key,
                    project_id=project_id,
                    actor_id=actor_id,
                    base_revision_id=head.revision_id,
                    command_hash=change.command_hash,
                    now=now,
                )
            elif change.confirmation_required:
                raise PreviewRequired("Consequential commands need a preview token.")
        except ProjectError as exc:
            return fail(exc, parsed)

        if change.is_noop:  # D045: no revision
            tx.insert_operation(_operation_row(change, project_id, actor_id, parsed, head.revision_id, "noop", now))
            return CommitResult(200, project_id, head.revision_id, head.parent_revision_id, change.operation_id, project.head_sequence, True)

        sequence = project.head_sequence + 1
        tx.insert_revision(_revision_row(change, project_id, sequence, now))
        tx.insert_operation(_operation_row(change, project_id, actor_id, parsed, head.revision_id, "committed", now))
        tx.set_head(project_id, change.revision_id, sequence)
        return CommitResult(201, project_id, change.revision_id, head.revision_id, change.operation_id, sequence, False)

    # --- reads ---------------------------------------------------------------

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self.store.transaction() as tx:
            p = _project(tx, project_id, lock=False)
        return {"project_id": p.project_id, "head_revision_id": p.head_revision_id, "head_sequence": p.head_sequence, "created_at": format_timestamp(p.created_at)}

    def get_revision(self, project_id: str, revision_id: str) -> Snapshot:
        with self.store.transaction() as tx:
            _project(tx, project_id, lock=False)
            return _load(tx, project_id, revision_id)

    def list_revisions(self, project_id: str) -> list[dict[str, Any]]:
        with self.store.transaction() as tx:
            _project(tx, project_id, lock=False)
            rows = tx.list_revisions(project_id)
        return [
            {
                "revision_id": r.revision_id,
                "parent_revision_id": r.parent_revision_id,
                "sequence": r.sequence,
                "created_at": format_timestamp(r.created_at),
                "operation_id": op.operation_id if op else None,
                "command_type": op.command_type if op else None,
            }
            for r, op in rows
        ]

    def list_operations(self, project_id: str) -> list[OperationRow]:
        """The project's audit log, oldest first (used for audit views and replay)."""
        with self.store.transaction() as tx:
            _project(tx, project_id, lock=False)
            return tx.list_operations(project_id)


# --- helpers ---------------------------------------------------------------------


def _check_actor(actor_id: str) -> None:
    if not is_canonical_uuid(actor_id):
        raise ValueError("actor_id must be the authenticated actor's canonical UUID")


def _project(tx, project_id: str, *, lock: bool) -> ProjectRow:
    row = tx.get_project(project_id, lock=lock) if is_canonical_uuid(project_id) else None
    if row is None:
        raise NotFound("Project not found.")
    return row


_load = load_snapshot


def _undo_target(tx, project_id: str, command: Any) -> Snapshot | None:
    if not (isinstance(command, dict) and command.get("type") == "UndoToRevision" and isinstance(command.get("args"), dict)):
        return None
    target_id = command["args"].get("target_revision_id")
    if not (isinstance(target_id, str) and is_canonical_uuid(target_id)):
        return None
    try:
        return _load(tx, project_id, target_id)
    except NotFound:
        return None  # propose reports DANGLING_REFERENCE at args.target_revision_id


def _rejection_error(result: ValidationResult) -> ProjectError:
    if result.code == "REVISION_CONFLICT":
        return RevisionConflict("base_revision_id is not the project head.")
    return CommandRejected(result)


def _revision_row(change: CandidateChange, project_id: str, sequence: int, now: datetime) -> RevisionRow:
    snapshot = change.candidate
    return RevisionRow(
        revision_id=change.revision_id,
        project_id=project_id,
        parent_revision_id=snapshot.parent_revision_id,
        sequence=sequence,
        model_schema_version=snapshot.model_schema_version,
        snapshot=snapshot.model_dump(mode="json"),
        fingerprint=snapshot_fingerprint(snapshot),
        created_at=now,
    )


def _command_fields(parsed: Any) -> dict[str, Any]:
    if parsed is None:
        return {"command_id": None, "command_type": None, "command": None, "command_hash": None}
    return {
        "command_id": parsed.command_id,
        "command_type": parsed.type,
        "command": parsed.model_dump(mode="json", exclude_unset=True),
        "command_hash": command_hash(parsed),
    }


def _operation_row(change, project_id, actor_id, parsed, base_revision_id, result, now) -> OperationRow:
    return OperationRow(
        operation_id=change.operation_id,
        project_id=project_id,
        actor_id=actor_id,
        base_revision_id=base_revision_id,
        result=result,
        rejection_code=None,
        revision_id=None if result == "noop" else change.revision_id,
        classification=change.classification,
        classification_version=change.classification_version,
        created_at=now,
        **_command_fields(parsed),
    )


def _rejected_row(project_id, actor_id, parsed, base_revision_id, code, now) -> OperationRow:
    # Rejected attempts get a random ID: a later successful retry under the same command_id
    # mints its own deterministic operation ID (D041) and must not collide.
    return OperationRow(
        operation_id=str(uuid.uuid4()),
        project_id=project_id,
        actor_id=actor_id,
        base_revision_id=base_revision_id,
        result="rejected",
        rejection_code=code,
        revision_id=None,
        classification=None,
        classification_version=None,
        created_at=now,
        **_command_fields(parsed),
    )


def _replayed(tx, op: OperationRow) -> CommitResult:
    """Rebuild the original result from the stored operation (interfaces.md §4: 200, replayed)."""
    if op.result == "noop":
        rev = tx.get_revision(op.project_id, op.base_revision_id)
        return CommitResult(200, op.project_id, rev.revision_id, rev.parent_revision_id, op.operation_id, rev.sequence, True, True)
    rev = tx.get_revision(op.project_id, op.revision_id)
    return CommitResult(200, op.project_id, rev.revision_id, rev.parent_revision_id, op.operation_id, rev.sequence, False, True)
