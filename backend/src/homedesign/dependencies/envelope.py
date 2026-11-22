"""Artifact envelope and manifest DTOs (artifacts.md §2–3; Pydantic-authoritative per D028)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from homedesign.model.schema import Uuid

Status = Literal["MISSING", "QUEUED", "COMPUTING", "CURRENT", "FAILED", "STALE", "UNAVAILABLE", "SUPERSEDED"]

PRELIMINARY_WARNING = {
    "code": "PRELIMINARY_UNVERIFIED",
    "message": "Framing and estimates are preliminary. Structural adequacy has not been assessed.",
}

# ART-003 §4.9 (routine item 13 of vs-02b.md §6): every assembly_schedule envelope, whatever its status,
# carries this after PRELIMINARY_UNVERIFIED, because only that artifact reports assembly properties.
CLIMATE_WARNING = {
    "code": "CLIMATE_DETAILS_UNVERIFIED",
    "message": "Climate-specific details of the wall assemblies have not been verified for this site. Each definition lists them.",
}
STANDING_WARNINGS: dict[str, tuple[dict[str, str], ...]] = {"assembly_schedule": (PRELIMINARY_WARNING, CLIMATE_WARNING)}


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


class Claims(_Strict):
    structurally_verified: Literal[False] = False
    construction_approved: Literal[False] = False
    permit_ready: Literal[False] = False


class Message(_Strict):
    code: str
    message: str


class ArtifactEnvelope(_Strict):
    """Common envelope for every artifact response (artifacts.md §2)."""

    model_config = ConfigDict(title="VS-01 artifact envelope (artifacts.md §2)")

    artifact_type: Literal["plan2d", "mesh3d", "timber_schedule", "assembly_schedule", "preliminary_estimate"]
    schema_version: Literal[1] = 1
    project_id: Uuid
    source_revision_id: Uuid
    head: bool
    generator_id: str | None
    generator_version: str | None
    input_fingerprint: str | None
    generated_at: str | None
    status: Status
    suitability: Literal["preliminary"] = "preliminary"
    claims: Claims = Claims()
    warnings: list[Message]
    error: Message | None
    payload: dict[str, Any] | None = None


class ManifestEntry(_Strict):
    artifact_type: str
    status: Status
    source_revision_id: Uuid
    generator_version: str | None
    input_fingerprint: str | None


class Manifest(_Strict):
    project_id: Uuid
    revision_id: Uuid
    head: bool
    artifacts: list[ManifestEntry]
