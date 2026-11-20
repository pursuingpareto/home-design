"""Strict JSON request bodies (interfaces.md §7 "HTTP request handling")."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from homedesign.model import codes
from homedesign.model.codes import Stage
from homedesign.model.paths import EntityAddresser
from homedesign.model.strict_json import parse
from homedesign.model.limits import DEFAULT_MAX_BYTES
from homedesign.model.validation import Issue, ValidationResult, _Collector, _scan_raw
from homedesign.project.errors import CommandRejected, ProjectError


class UnsupportedMediaType(ProjectError):
    """Not application/json. Reported as VALIDATION_FAILED / MALFORMED_JSON with HTTP 415."""

    code, http_status = "VALIDATION_FAILED", 415

    def __init__(self) -> None:
        super().__init__("Request bodies must be application/json.")
        self.result = ValidationResult(False, "VALIDATION_FAILED", (Issue("", codes.MALFORMED_JSON, "Request bodies must be application/json."),))


async def _read_capped(request: Request, max_bytes: int) -> bytes:
    """Stop reading once the body exceeds the limit; `parse` then reports PAYLOAD_LIMIT_EXCEEDED."""
    chunks, size = [], 0
    async for chunk in request.stream():
        chunks.append(chunk)
        size += len(chunk)
        if size > max_bytes:
            break
    return b"".join(chunks)


async def read_json(request: Request) -> Any:
    """Parse the body strictly; raise CommandRejected (422) or UnsupportedMediaType (415)."""
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json":
        raise UnsupportedMediaType()
    outcome = parse(await _read_capped(request, DEFAULT_MAX_BYTES))
    if outcome.fatal is not None:
        raise CommandRejected(ValidationResult(False, "VALIDATION_FAILED", (Issue("", outcome.fatal.code, outcome.fatal.message),)))
    out = _Collector()
    _scan_raw(outcome.value, [], EntityAddresser(None, []), out, set())  # same checks as snapshots
    if (result := out.result(Stage.SYNTACTIC)) is not None:
        raise CommandRejected(result)
    return outcome.value
