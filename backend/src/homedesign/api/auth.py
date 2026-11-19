"""Authentication (D050): a pluggable authenticator; VS-01 ships a development bearer-token one."""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from typing import Protocol

from starlette.requests import Request

from homedesign.project.errors import ProjectError


class Unauthorized(ProjectError):
    code, http_status = "UNAUTHORIZED", 401


class Authenticator(Protocol):
    def authenticate(self, request: Request) -> str:
        """Return the authenticated actor's UUID, or raise Unauthorized."""
        ...


class DevTokenAuthenticator:
    """`Authorization: Bearer <token>` with tokens from configuration. Development and tests only."""

    def __init__(self, tokens: Mapping[str, str]) -> None:
        self._tokens = dict(tokens)

    def authenticate(self, request: Request) -> str:
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise Unauthorized("A bearer token is required.")
        for known, actor in self._tokens.items():  # constant-time comparison per entry
            if hmac.compare_digest(known.encode(), token.strip().encode()):
                return actor
        raise Unauthorized("Unknown bearer token.")
