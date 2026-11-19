"""App factory, request IDs, and the error envelope (API-001 §5, §7).

Run locally (from backend/):
    uv run uvicorn homedesign.api.app:create_app --factory
"""

from __future__ import annotations

import logging
import traceback
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from homedesign.model.validation import Issue
from homedesign.project import MemoryStore, ProjectService
from homedesign.project.errors import ProjectError

from .auth import Authenticator, DevTokenAuthenticator
from .settings import Settings

log = logging.getLogger("homedesign.api")

REQUEST_ID_HEADER = "X-Request-ID"


def _detail(issue: Issue) -> dict[str, Any]:
    """interfaces.md §7: `{path, code, value?, related_paths?}`; per-issue messages are left out."""
    detail = issue.to_dict()
    detail.pop("message", None)
    return detail


def error_response(request_id: str, status: int, code: str, message: str, details: list[dict[str, Any]] | None = None, headers: dict[str, str] | None = None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details or [], "request_id": request_id}}
    return JSONResponse(body, status_code=status, headers={REQUEST_ID_HEADER: request_id, **(headers or {})})


def _request_id(request: Request) -> str:
    return request.scope.get("state", {}).get("request_id") or str(uuid.uuid4())


def _log_internal(request_id: str, exc: BaseException) -> None:
    # Type and stack frames only: exception messages may quote project content (dependencies.md §9).
    frames = "\n".join(f"  {f.filename}:{f.lineno} in {f.name}" for f in traceback.extract_tb(exc.__traceback__))
    log.error("Unhandled %s (request_id=%s)\n%s", type(exc).__name__, request_id, frames)


class RequestContextMiddleware:
    """Assigns a server-generated request ID, sets X-Request-ID on every response, and turns any
    unexpected exception into 500 INTERNAL without internals."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())  # never taken from the client
        scope.setdefault("state", {})["request_id"] = request_id
        started = False

        async def send_with_id(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                message = {**message, "headers": [*headers, (b"x-request-id", request_id.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as exc:  # noqa: BLE001 - the last line of defense
            _log_internal(request_id, exc)
            if started:
                raise
            await error_response(request_id, 500, "INTERNAL", "Internal server error.")(scope, receive, send)


async def _project_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProjectError)
    request_id = _request_id(request)
    if exc.http_status >= 500:
        _log_internal(request_id, exc)
        return error_response(request_id, 500, "INTERNAL", "Internal server error.")
    result = getattr(exc, "result", None)
    if result is not None:
        details = [_detail(i) for i in result.issues]
        message = result.issues[0].message if result.issues else str(exc)
    else:
        details, message = [], str(exc)
    headers = {"WWW-Authenticate": "Bearer"} if exc.http_status == 401 else None
    return error_response(request_id, exc.http_status, exc.code, message, details, headers)


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    request_id = _request_id(request)
    if exc.status_code == 404:
        return error_response(request_id, 404, "NOT_FOUND", "Not found.")
    if exc.status_code == 405:
        return error_response(request_id, 405, "METHOD_NOT_ALLOWED", "Method not allowed.", headers=dict(exc.headers or {}))
    return error_response(request_id, exc.status_code, "INTERNAL" if exc.status_code >= 500 else "VALIDATION_FAILED", str(exc.detail))


async def _request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    # Bodies never reach FastAPI's validation (handlers parse them strictly); only parameters can.
    return error_response(_request_id(request), 422, "VALIDATION_FAILED", "Invalid request parameters.")


def create_app(
    settings: Settings | None = None,
    *,
    store: Any = None,
    registry: Any = None,
    authenticator: Authenticator | None = None,
    clock: Callable[[], datetime] | None = None,
    project_id_factory: Callable[[], str] | None = None,  # tests: deterministic project IDs (TEST-001)
) -> FastAPI:
    """Build the API. Settings come from the environment unless given; startup fails on invalid ones."""
    from .openapi import install_openapi
    from .routes import router

    settings = settings or Settings.from_env()
    if store is None:
        if settings.store == "memory":
            store = MemoryStore()
        else:
            from homedesign.project.postgres import PostgresStore

            store = PostgresStore(settings.database_url)
    app = FastAPI(
        title="Home Design Platform API",
        version="1.0.0",
        summary="VS-01 HTTP API (API-001). Generated from the Pydantic models; do not edit the exported document by hand.",
        separate_input_output_schemas=False,
        docs_url="/docs",  # outside /api/v1, whose routes all require authentication (interfaces.md §5)
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    extra = {"project_id_factory": project_id_factory} if project_id_factory else {}
    app.state.service = ProjectService(store, token_key=settings.preview_key, registry=registry, **extra)
    app.state.authenticator = authenticator or DevTokenAuthenticator(settings.dev_tokens)
    app.state.clock = clock or (lambda: datetime.now(UTC))
    app.include_router(router)
    app.add_exception_handler(ProjectError, _project_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _request_validation_error)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    app.add_middleware(RequestContextMiddleware)  # outermost of the app's middleware
    install_openapi(app)
    return app

