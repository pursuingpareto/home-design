"""Request and response DTOs for the OpenAPI document (API-001 §8).

Handlers parse bodies strictly (body.py) and return the service dictionaries; these models describe
those shapes for clients. Contract tests validate real responses against the generated document.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from homedesign.estimating.pricebook import PriceBook
from homedesign.model.commands.envelope import AnyCommand, CreateReferenceProject

ArtifactStatus = Literal["CURRENT", "STALE", "MISSING", "UNAVAILABLE", "FAILED"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- requests ------------------------------------------------------------------------


class Command(RootModel[AnyCommand]):
    """Any VS-01 command envelope, discriminated by `type` (interfaces.md §2)."""


class CreateProjectRequest(RootModel[CreateReferenceProject]):
    """The creation envelope (interfaces.md §2): `CreateReferenceProject` without project or base revision."""


class CommitRequest(_Strict):
    command: AnyCommand
    preview_token: str | None = Field(default=None, description="Required for consequential commands that are not no-ops (D047).")


# --- responses ------------------------------------------------------------------------


class ErrorDetail(_Strict):
    path: str = Field(description="D036 path from the root of the validated document.")
    code: str = Field(description="Detail code from building-model.md §6.1.")
    value: Any = None
    related_paths: list[str] | None = Field(default=None, description="D037; omitted when empty.")


class ErrorBody(_Strict):
    code: str
    message: str = Field(description="Human-readable; not part of the contract.")
    details: list[ErrorDetail]
    request_id: str


class ErrorEnvelope(_Strict):
    error: ErrorBody


class ProjectResponse(_Strict):
    project_id: str
    head_revision_id: str
    head_sequence: int
    created_at: str
    permissions: list[Literal["read", "write"]]


class ProjectSummary(_Strict):
    project_id: str
    head_revision_id: str
    head_sequence: int
    created_at: str


class ProjectList(_Strict):
    projects: list[ProjectSummary] = Field(description="The caller's own projects, newest first (UI-001 §8.1).")


class CommitResponse(_Strict):
    project_id: str
    revision_id: str
    parent_revision_id: str | None
    operation_id: str
    sequence: int
    is_noop: bool
    artifact_statuses: dict[str, ArtifactStatus]
    replayed: Literal[True] | None = Field(default=None, description="Present (true) only for an idempotent retry.")


class FieldChange(_Strict):
    entity_kind: str
    entity_id: str
    field: str
    before: Any
    after: Any


class MemberRef(_Strict):
    id: str
    generation_key: str


class MemberChanges(_Strict):
    added: list[MemberRef]
    removed: list[MemberRef]
    updated: list[str]


class PreviewWarning(_Strict):
    code: str
    message: str


class PreviewResponse(_Strict):
    preview_token: str
    expires_at: str
    base_revision_id: str
    revision_id: str | None
    command_hash: str
    classification: str
    classification_version: str
    confirmation_required: bool
    is_noop: bool
    changes: list[FieldChange]
    members: MemberChanges
    impacted_artifacts: list[str]
    warnings: list[PreviewWarning]


class RevisionSummary(_Strict):
    revision_id: str
    parent_revision_id: str | None
    sequence: int
    created_at: str
    operation_id: str | None
    command_type: str | None


class RevisionList(_Strict):
    revisions: list[RevisionSummary]


class PriceBookSet(_Strict):
    price_book_id: str
    version: int
    set_at: str


class StoredPriceBook(_Strict):
    price_book_id: str
    version: int
    book: PriceBook
    set_by: str
    set_at: str


class PriceBookResponse(_Strict):
    price_book: StoredPriceBook | None
