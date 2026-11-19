"""Typed service errors; the API task maps ``code`` and ``http_status`` to responses (interfaces.md §7)."""

from __future__ import annotations

from homedesign.model.validation import ValidationResult


class ProjectError(Exception):
    code = "INTERNAL"
    http_status = 500

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)


class NotFound(ProjectError):
    code, http_status = "NOT_FOUND", 404


class RevisionConflict(ProjectError):
    code, http_status = "REVISION_CONFLICT", 409


class IdempotencyConflict(ProjectError):
    code, http_status = "IDEMPOTENCY_CONFLICT", 409


class PreviewRequired(ProjectError):
    code, http_status = "PREVIEW_REQUIRED", 428


class PreviewInvalid(ProjectError):
    code, http_status = "PREVIEW_INVALID", 409


class PreviewExpired(ProjectError):
    code, http_status = "PREVIEW_EXPIRED", 409


class CommandRejected(ProjectError):
    """The command failed validation; ``result`` carries the D035 details."""

    http_status = 422

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        self.code = result.code or "VALIDATION_FAILED"
        if self.code == "REVISION_CONFLICT":
            self.http_status = 409
        super().__init__(self.code)


class CorruptRevision(ProjectError):
    """A stored snapshot no longer matches its fingerprint. Never served (MODEL-004 §4.6)."""

    code, http_status = "INTERNAL", 500
