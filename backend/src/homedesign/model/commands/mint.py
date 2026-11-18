"""Deterministic ID minting from the command (D041)."""

from __future__ import annotations

import uuid

from ..jcs import canonical_json

# Fixed platform constant (D041). Never change: replay depends on it.
NAMESPACE = uuid.UUID("6652101f-3d1d-4a2b-bd82-9d87e0207354")


def mint(purpose: str, project_id: str, actor_id: str, command_id: str, creation_key: str | None) -> str:
    """UUIDv5 over the RFC 8785 form of [purpose, project_id, actor_id, command_id, creation_key]."""
    name = canonical_json([purpose, project_id, actor_id, command_id, creation_key]).decode("utf-8")
    return str(uuid.uuid5(NAMESPACE, name))
