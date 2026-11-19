"""VS-01 routes (interfaces.md §5; API-001 §4). Parse, authenticate, authorize, call, map: no business logic."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from homedesign.dependencies.envelope import ArtifactEnvelope, Manifest
from homedesign.model import codes
from homedesign.model.canonical import canonical_snapshot
from homedesign.model.codes import Stage
from homedesign.model.paths import render
from homedesign.model.schema import Snapshot
from homedesign.model.validation import ValidationResult, _Collector
from homedesign.project import ProjectService
from homedesign.project.errors import CommandRejected

from .body import read_json
from .models import (
    CommitRequest,
    CommitResponse,
    CreateProjectRequest,
    Command,
    ErrorEnvelope,
    PriceBookResponse,
    PriceBookSet,
    PreviewResponse,
    ProjectList,
    ProjectResponse,
    RevisionList,
)

router = APIRouter(prefix="/api/v1")
T = TypeVar("T")

# --- OpenAPI helpers ------------------------------------------------------------------


def _errors(*statuses: int) -> dict[int | str, dict[str, Any]]:
    described = {
        401: "Missing or unknown bearer token (UNAUTHORIZED).",
        404: "Project, revision, or artifact type not found, or not visible to the caller (D050).",
        409: "REVISION_CONFLICT, IDEMPOTENCY_CONFLICT, PREVIEW_INVALID, or PREVIEW_EXPIRED.",
        415: "The body is not application/json.",
        422: "VALIDATION_FAILED or UNSUPPORTED_CONFIGURATION, with details.",
        428: "PREVIEW_REQUIRED: a consequential command needs a preview token.",
    }
    responses: dict[int | str, dict[str, Any]] = {s: {"model": ErrorEnvelope, "description": described[s]} for s in statuses}
    responses["default"] = {"model": ErrorEnvelope, "description": "Any other error, including 500 INTERNAL."}
    return responses


def _body(component: str, description: str) -> dict[str, Any]:
    schema = {"$ref": f"#/components/schemas/{component}"}
    return {"requestBody": {"required": True, "description": description, "content": {"application/json": {"schema": schema}}}}


REQUEST_COMPONENTS = (Command, CreateProjectRequest, CommitRequest)  # added to components by openapi.py

# --- plumbing -------------------------------------------------------------------------


def _service(request: Request) -> ProjectService:
    return request.app.state.service


async def _run(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Services are synchronous (psycopg 3 sync); keep them off the event loop."""
    return await run_in_threadpool(fn, *args, **kwargs)


def _actor(request: Request) -> str:
    return request.app.state.authenticator.authenticate(request)


async def _owner(request: Request, project_id: str) -> str:
    """Authenticate, then authorize before any other service call (D050)."""
    actor = _actor(request)
    await _run(_service(request).require_owner, project_id, actor)
    return actor


def _now(request: Request):
    return request.app.state.clock()


def _commit_body(value: Any) -> tuple[Any, str | None]:
    """`{command, preview_token?}`. Wrapper paths are body-relative; command paths stay envelope-relative (§7.1)."""
    out = _Collector()
    if not isinstance(value, dict):
        out.add("", codes.WRONG_TYPE, "The body must be an object.")
    else:
        if "command" not in value:
            out.add("command", codes.MISSING_FIELD, "Field is required.")
        token = value.get("preview_token")
        if token is not None and not isinstance(token, str):
            out.add("preview_token", codes.WRONG_TYPE, "Expected a string.", token)
        for key in value:
            if key not in ("command", "preview_token"):
                out.add(render([key]), codes.UNKNOWN_FIELD, "Unknown field.")
    result: ValidationResult | None = out.result(Stage.SYNTACTIC)
    if result is not None:
        raise CommandRejected(result)
    return value["command"], value.get("preview_token")


# --- routes ---------------------------------------------------------------------------


@router.post(
    "/projects",
    status_code=201,
    operation_id="createProject",
    summary="Create a reference project (interfaces.md §2, §4)",
    responses={201: {"model": CommitResponse, "description": "Created."}, 200: {"model": CommitResponse, "description": "Idempotent retry (`replayed: true`)."}, **_errors(401, 409, 415, 422)},
    openapi_extra=_body("CreateProjectRequest", "The creation envelope."),
)
async def create_project(request: Request) -> Response:
    actor = _actor(request)
    command = await read_json(request)
    result = await _run(_service(request).create_project, command, actor_id=actor, now=_now(request))
    return JSONResponse(result.body(), status_code=result.http_status)


@router.get(
    "/projects",
    operation_id="listProjects",
    summary="The caller's own projects, newest first (UI-001 §8.1)",
    responses={200: {"model": ProjectList, "description": "The projects."}, **_errors(401)},
)
async def list_projects(request: Request) -> Response:
    actor = _actor(request)
    return JSONResponse({"projects": await _run(_service(request).list_projects, actor)})


@router.get(
    "/projects/{project_id}",
    operation_id="getProject",
    summary="Project metadata, head, and the caller's permissions",
    responses={200: {"model": ProjectResponse, "description": "The project."}, **_errors(401, 404)},
)
async def get_project(request: Request, project_id: str) -> Response:
    await _owner(request, project_id)
    project = await _run(_service(request).get_project, project_id)
    return JSONResponse(project | {"permissions": ["read", "write"]})  # owner in VS-01 (D050)


@router.post(
    "/projects/{project_id}/commands/preview",
    operation_id="previewCommand",
    summary="Preview a command without writing anything (interfaces.md §3)",
    responses={200: {"model": PreviewResponse, "description": "The proposed change and a preview token."}, **_errors(401, 404, 409, 415, 422)},
    openapi_extra=_body("Command", "A command envelope."),
)
async def preview_command(request: Request, project_id: str) -> Response:
    actor = await _owner(request, project_id)
    command = await read_json(request)
    result = await _run(_service(request).preview, project_id, command, actor_id=actor, now=_now(request))
    return JSONResponse(result.body)


@router.post(
    "/projects/{project_id}/commands/commit",
    status_code=201,
    operation_id="commitCommand",
    summary="Commit a command (interfaces.md §4)",
    responses={
        201: {"model": CommitResponse, "description": "A new revision."},
        200: {"model": CommitResponse, "description": "A no-op (D045) or an idempotent retry (`replayed: true`)."},
        **_errors(401, 404, 409, 415, 422, 428),
    },
    openapi_extra=_body("CommitRequest", "The command and, when required, its preview token."),
)
async def commit_command(request: Request, project_id: str) -> Response:
    actor = await _owner(request, project_id)
    command, token = _commit_body(await read_json(request))
    result = await _run(_service(request).commit, project_id, command, token, actor_id=actor, now=_now(request))
    return JSONResponse(result.body(), status_code=result.http_status)


@router.get(
    "/projects/{project_id}/revisions",
    operation_id="listRevisions",
    summary="Revision history, ordered by sequence",
    responses={200: {"model": RevisionList, "description": "The revisions."}, **_errors(401, 404)},
)
async def list_revisions(request: Request, project_id: str) -> Response:
    await _owner(request, project_id)
    return JSONResponse({"revisions": await _run(_service(request).list_revisions, project_id)})


@router.get(
    "/projects/{project_id}/revisions/{revision_id}",
    operation_id="getRevision",
    summary="An immutable snapshot, as its RFC 8785 canonical bytes (D029, D030)",
    responses={200: {"model": Snapshot, "description": "The snapshot."}, **_errors(401, 404)},
)
async def get_revision(request: Request, project_id: str, revision_id: str) -> Response:
    await _owner(request, project_id)
    snapshot = await _run(_service(request).get_revision, project_id, revision_id)
    return Response(canonical_snapshot(snapshot), media_type="application/json")


@router.get(
    "/projects/{project_id}/artifacts",
    operation_id="getArtifactManifest",
    summary="Artifact status manifest (artifacts.md §3); the head when revision_id is omitted",
    responses={200: {"model": Manifest, "description": "The manifest."}, **_errors(401, 404)},
)
async def get_manifest(request: Request, project_id: str, revision_id: str | None = None) -> Response:
    await _owner(request, project_id)
    return JSONResponse(await _run(_service(request).artifacts.manifest, project_id, revision_id))


@router.get(
    "/projects/{project_id}/artifacts/{artifact_type}",
    operation_id="getArtifact",
    summary="One derived artifact (artifacts.md §2); derived on read when missing or stale",
    responses={
        200: {"model": ArtifactEnvelope, "description": "CURRENT, UNAVAILABLE (partial payload when provided), or FAILED (with error)."},
        202: {"model": ArtifactEnvelope, "description": "MISSING: no registered derivation; no payload."},
        **_errors(401, 404),
    },
)
async def get_artifact(request: Request, project_id: str, artifact_type: str, revision_id: str | None = None) -> Response:
    await _owner(request, project_id)
    envelope = await _run(_service(request).artifacts.get_artifact, project_id, artifact_type, revision_id, now=_now(request))
    return JSONResponse(envelope, status_code=202 if envelope["status"] == "MISSING" else 200)


@router.put(
    "/projects/{project_id}/price-book",
    status_code=201,
    operation_id="setPriceBook",
    summary="Set a new price-book version (artifacts.md §8.2)",
    responses={201: {"model": PriceBookSet, "description": "The new version."}, **_errors(401, 404, 415, 422)},
    openapi_extra=_body("PriceBook", "The price book."),
)
async def set_price_book(request: Request, project_id: str) -> Response:
    actor = await _owner(request, project_id)
    book = await read_json(request)
    result = await _run(_service(request).set_price_book, project_id, book, actor_id=actor, now=_now(request))
    return JSONResponse(result, status_code=201)


@router.get(
    "/projects/{project_id}/price-book",
    operation_id="getPriceBook",
    summary="The current price book, or null",
    responses={200: {"model": PriceBookResponse, "description": "The current version."}, **_errors(401, 404)},
)
async def get_price_book(request: Request, project_id: str) -> Response:
    await _owner(request, project_id)
    return JSONResponse({"price_book": await _run(_service(request).get_price_book, project_id)})
