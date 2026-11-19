"""Stateless signed preview tokens (D047).

token = base64url(payload) "." base64url(HMAC-SHA-256(key, payload)), where payload is the
RFC 8785 form of {project_id, actor_id, base_revision_id, command_hash, expires_at}.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime

from homedesign.model.jcs import canonical_json

from .errors import PreviewExpired, PreviewInvalid
from .timefmt import format_timestamp, parse_timestamp


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue(key: bytes, *, project_id: str, actor_id: str, base_revision_id: str, command_hash: str, expires_at: datetime) -> str:
    payload = canonical_json(
        {
            "project_id": project_id,
            "actor_id": actor_id,
            "base_revision_id": base_revision_id,
            "command_hash": command_hash,
            "expires_at": format_timestamp(expires_at),
        }
    )
    return _b64(payload) + "." + _b64(hmac.new(key, payload, hashlib.sha256).digest())


def verify(token: str, key: bytes, *, project_id: str, actor_id: str, base_revision_id: str, command_hash: str, now: datetime) -> None:
    """Raise PreviewInvalid or PreviewExpired unless the token authorizes exactly this commit."""
    try:
        payload_b64, signature_b64 = token.split(".")
        payload, signature = _unb64(payload_b64), _unb64(signature_b64)
    except (ValueError, AttributeError) as exc:
        raise PreviewInvalid("Malformed preview token.") from exc
    if not hmac.compare_digest(hmac.new(key, payload, hashlib.sha256).digest(), signature):
        raise PreviewInvalid("Preview token signature does not verify.")
    claims = json.loads(payload)
    expected = {"project_id": project_id, "actor_id": actor_id, "base_revision_id": base_revision_id, "command_hash": command_hash}
    if any(claims.get(k) != v for k, v in expected.items()):
        raise PreviewInvalid("Preview token was issued for a different project, actor, base revision, or command.")
    if now > parse_timestamp(claims["expires_at"]):
        raise PreviewExpired("Preview token has expired; preview again.")
