"""Artifact derivation, storage, status, and manifest (ART-001).

Execution model (dependencies.md §6): derive synchronously after commit; derive on read when
no stored row matches the expected fingerprint. VS-01 never produces QUEUED/COMPUTING/SUPERSEDED.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homedesign.model.canonical import canonical_snapshot_value, fingerprint
from homedesign.model.jcs import CanonicalizationError, canonical_json
from homedesign.model.paths import is_canonical_uuid
from homedesign.model.schema import Snapshot
from homedesign.project.errors import NotFound
from homedesign.project.loading import load_snapshot
from homedesign.project.store import ArtifactRow, RevisionStore
from homedesign.project.timefmt import format_timestamp

from .envelope import PRELIMINARY_WARNING, ArtifactEnvelope, Manifest, ManifestEntry
from .registry import ARTIFACT_TYPES, Derivation, DerivationContext, Outcome, Registry, default_registry


class ArtifactService:
    def __init__(self, store: RevisionStore, registry: Registry | None = None) -> None:
        self.store = store
        self.registry = registry if registry is not None else default_registry()

    # --- inputs and fingerprints -------------------------------------------------

    def _inputs(self, tx, project_id: str, snapshot: Snapshot, derivation: Derivation) -> tuple[dict, dict]:
        external = derivation.external_inputs(tx, project_id) if derivation.external_inputs else {}
        inputs = {
            "revision_id": snapshot.revision_id,
            "model_schema_version": snapshot.model_schema_version,
            "generator_id": derivation.generator_id,
            "generator_version": derivation.generator_version,
            "snapshot": canonical_snapshot_value(snapshot),
            **external,
        }
        return inputs, external

    # --- derivation --------------------------------------------------------------

    def derive_revision(self, project_id: str, revision_id: str, *, now: datetime) -> dict[str, str]:
        """Derive and store every registered artifact for one revision (after commit)."""
        with self.store.transaction() as tx:
            snapshot = load_snapshot(tx, project_id, revision_id)
            plans = [(d, *self._inputs(tx, project_id, snapshot, d)) for d in self.registry.ordered()]
        outcomes: dict[str, Outcome] = {}
        for derivation, inputs, external in plans:
            outcome = self._run(derivation, project_id, snapshot, external, outcomes)
            outcomes[derivation.artifact_type] = outcome
            with self.store.transaction() as tx:  # one transaction per artifact (ART-001 §4)
                tx.put_artifact(self._row(project_id, revision_id, derivation, inputs, outcome, now))
        return {kind: (outcomes[kind].status if kind in outcomes else "MISSING") for kind in ARTIFACT_TYPES}

    def _run(self, derivation, project_id, snapshot, external, upstream) -> Outcome:
        blocked = [d for d in derivation.depends_on if upstream.get(d) is None or upstream[d].status != "CURRENT"]
        if blocked:
            return Outcome("FAILED", error={"code": "UPSTREAM_NOT_CURRENT", "message": f"Depends on {', '.join(blocked)}, which is not CURRENT."})
        context = DerivationContext(project_id, snapshot, external, {d: upstream[d] for d in derivation.depends_on})
        try:
            outcome = derivation.derive(context)
            if outcome.payload is not None:
                canonical_json(outcome.payload)  # payloads must be I-JSON (storable, fingerprintable)
            return outcome
        except CanonicalizationError:
            return Outcome("FAILED", error={"code": "DERIVATION_FAILED", "message": "Derivation produced a payload that is not I-JSON."})
        except Exception as exc:  # noqa: BLE001 - a failed derivation must never affect the revision
            return Outcome("FAILED", error={"code": "DERIVATION_FAILED", "message": f"Derivation raised {type(exc).__name__}."})

    @staticmethod
    def _row(project_id, revision_id, derivation, inputs, outcome, now) -> ArtifactRow:
        return ArtifactRow(
            project_id=project_id,
            revision_id=revision_id,
            artifact_type=derivation.artifact_type,
            input_fingerprint=fingerprint(inputs),
            generator_id=derivation.generator_id,
            generator_version=derivation.generator_version,
            status=outcome.status,
            payload=outcome.payload,
            error=outcome.error,
            warnings=[dict(w) for w in outcome.warnings],
            generated_at=now,
        )

    # --- status -----------------------------------------------------------------

    def _resolve(self, tx, project_id: str, revision_id: str | None) -> tuple[Snapshot, bool]:
        project = tx.get_project(project_id) if is_canonical_uuid(project_id) else None
        if project is None:
            raise NotFound("Project not found.")
        target = revision_id or project.head_revision_id
        return load_snapshot(tx, project_id, target), target == project.head_revision_id

    def _state(self, tx, project_id: str, snapshot: Snapshot, kind: str):
        """(status, matching row or None, derivation or None, inputs or None) per ART-001 §6."""
        derivation = self.registry.derivations.get(kind)
        if derivation is None:
            return "MISSING", None, None, None
        inputs, _ = self._inputs(tx, project_id, snapshot, derivation)
        expected = fingerprint(inputs)
        rows = tx.get_artifacts(snapshot.revision_id, kind)
        match = next((r for r in rows if r.input_fingerprint == expected), None)
        if match is not None:
            return match.status, match, derivation, inputs
        return ("STALE" if rows else "MISSING"), None, derivation, inputs

    def manifest(self, project_id: str, revision_id: str | None = None) -> dict[str, Any]:
        """Read-only manifest of all four types (artifacts.md §3). Never derives."""
        with self.store.transaction() as tx:
            snapshot, head = self._resolve(tx, project_id, revision_id)
            entries = []
            for kind in ARTIFACT_TYPES:
                status, row, derivation, _ = self._state(tx, project_id, snapshot, kind)
                entries.append(
                    ManifestEntry(
                        artifact_type=kind,
                        status=status,
                        source_revision_id=snapshot.revision_id,
                        generator_version=derivation.generator_version if derivation else None,
                        input_fingerprint=row.input_fingerprint if row else None,
                    )
                )
        return Manifest(project_id=project_id, revision_id=snapshot.revision_id, head=head, artifacts=entries).model_dump(mode="json")

    def statuses(self, project_id: str, revision_id: str) -> dict[str, str]:
        return {e["artifact_type"]: e["status"] for e in self.manifest(project_id, revision_id)["artifacts"]}

    def get_artifact(self, project_id: str, artifact_type: str, revision_id: str | None = None, *, now: datetime) -> dict[str, Any]:
        """Envelope for one artifact, deriving it on demand when missing or stale (ART-001 §4, §6)."""
        if artifact_type not in ARTIFACT_TYPES:
            raise NotFound("Unknown artifact type.")
        with self.store.transaction() as tx:
            snapshot, head = self._resolve(tx, project_id, revision_id)
            status, row, derivation, inputs = self._state(tx, project_id, snapshot, artifact_type)
        if derivation is None:
            return self._envelope(project_id, snapshot, head, artifact_type, None, None, "MISSING")
        if row is None:  # MISSING or STALE: derive now (lazy recompute)
            self._derive_one(project_id, snapshot, derivation, now)
            with self.store.transaction() as tx:
                status, row, derivation, inputs = self._state(tx, project_id, snapshot, artifact_type)
        return self._envelope(project_id, snapshot, head, artifact_type, derivation, row, status)

    def _derive_one(self, project_id: str, snapshot: Snapshot, derivation: Derivation, now: datetime) -> None:
        upstream: dict[str, Outcome] = {}
        for dependency in derivation.depends_on:
            envelope = self.get_artifact(project_id, dependency, snapshot.revision_id, now=now)
            upstream[dependency] = Outcome(envelope["status"], envelope.get("payload"))
        with self.store.transaction() as tx:
            inputs, external = self._inputs(tx, project_id, snapshot, derivation)
        outcome = self._run(derivation, project_id, snapshot, external, upstream)
        with self.store.transaction() as tx:
            tx.put_artifact(self._row(project_id, snapshot.revision_id, derivation, inputs, outcome, now))

    @staticmethod
    def _envelope(project_id, snapshot, head, kind, derivation, row, status) -> dict[str, Any]:
        warnings = [PRELIMINARY_WARNING, *(row.warnings if row else [])]  # AC-08: always present
        serve_payload = row is not None and status in ("CURRENT", "UNAVAILABLE")
        return ArtifactEnvelope(
            artifact_type=kind,
            project_id=project_id,
            source_revision_id=snapshot.revision_id,
            head=head,
            generator_id=derivation.generator_id if derivation else None,
            generator_version=derivation.generator_version if derivation else None,
            input_fingerprint=row.input_fingerprint if row else None,
            generated_at=format_timestamp(row.generated_at) if row else None,
            status=status,
            warnings=warnings,
            error=row.error if row else None,
            payload=row.payload if serve_payload else None,
        ).model_dump(mode="json")
