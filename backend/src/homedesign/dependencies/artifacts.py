"""Artifact derivation, reuse, impact, storage, status, and manifest (ART-001; DEP-001).

Execution model (dependencies.md §6): derive synchronously after commit; derive on read when
no stored row matches the expected fingerprint. VS-02 never produces QUEUED/COMPUTING/SUPERSEDED.

Fingerprints (DEP-001 §5, D056) hash each derivation's selection, its generator, the model schema
version, and its external inputs, never the revision. An artifact whose fingerprint has a stored
CURRENT or UNAVAILABLE row anywhere in the project is reused: the row is copied for the new
revision, payload and `generated_at` included, and the derivation does not run (DEP-001 §7).
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import datetime
from typing import Any

from homedesign.model.canonical import fingerprint
from homedesign.model.jcs import CanonicalizationError, canonical_json
from homedesign.model.paths import is_canonical_uuid
from homedesign.model.schema import Snapshot
from homedesign.project.errors import NotFound
from homedesign.project.loading import load_snapshot
from homedesign.project.store import ArtifactRow, RevisionStore
from homedesign.project.timefmt import format_timestamp

from .envelope import PRELIMINARY_WARNING, STANDING_WARNINGS, ArtifactEnvelope, Manifest, ManifestEntry
from .registry import ARTIFACT_TYPES, Derivation, DerivationContext, Outcome, Registry, default_registry

log = logging.getLogger("homedesign.dependencies")


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


class _SelectorFailed:
    """A selector raised for this snapshot (DEP-001 §15). Fingerprinted as a null selection."""

    def __init__(self, exc: Exception) -> None:
        self.name = type(exc).__name__


class ArtifactService:
    def __init__(self, store: RevisionStore, registry: Registry | None = None) -> None:
        self.store = store
        self.registry = registry if registry is not None else default_registry()

    # --- selections and fingerprints (DEP-001 §4–5) ----------------------------------

    @staticmethod
    def _source(derivation: Derivation, snapshot: Snapshot, upstream: dict[str, Outcome]) -> Any:
        """A selector reads the snapshot, or, with dependencies, only their outcomes (registry.Selector)."""
        if derivation.depends_on:
            return {d: upstream.get(d) for d in derivation.depends_on}
        return snapshot

    def _select(self, derivation: Derivation, snapshot: Snapshot, upstream: dict[str, Outcome]) -> Any:
        try:
            return derivation.select(self._source(derivation, snapshot, upstream))
        except Exception as exc:  # noqa: BLE001 - becomes FAILED (DERIVATION_FAILED), never a broken revision
            return _SelectorFailed(exc)

    @staticmethod
    def _fingerprint(derivation: Derivation, snapshot: Snapshot, selection: Any, external: dict[str, Any]) -> str:
        return fingerprint({
            "selection": None if isinstance(selection, _SelectorFailed) else selection,
            "generator_id": derivation.generator_id,
            "generator_version": derivation.generator_version,
            "model_schema_version": snapshot.model_schema_version,
            # Keys starting with "_" reach the derivation but are not fingerprinted; they must be
            # fully determined by the fingerprinted keys (e.g. a price book's rows by its version).
            **{k: v for k, v in external.items() if not k.startswith("_")},
        })

    @staticmethod
    def _external(tx, project_id: str, derivation: Derivation) -> dict[str, Any]:
        return derivation.external_inputs(tx, project_id) if derivation.external_inputs else {}

    # --- impact (DEP-001 §6) -------------------------------------------------------

    def impact(self, project_id: str, base: Snapshot, candidate: Snapshot) -> list[str]:
        """Artifact types whose fingerprint differs between base and candidate, sorted. Writes nothing.

        Both sides use the project's current external inputs, so a price book never makes an artifact
        impacted. A derivation with dependencies selects only from their outcomes: when none of them is
        impacted, its selections are equal, and nothing is built. Otherwise the upstream outcomes are
        read from a reusable stored row, or derived without being stored. Selector errors propagate.
        """
        derivations = self.registry.ordered()
        registered = self.registry.derivations
        with self.store.transaction() as tx:
            externals = {d.artifact_type: self._external(tx, project_id, d) for d in derivations}
        sides = {"base": base, "candidate": candidate}
        computed: dict[tuple[str, str], tuple[Any, str, dict[str, Outcome]]] = {}  # (side, type) -> selection, fingerprint, upstream
        outcomes: dict[tuple[str, str], Outcome] = {}

        def selected(side: str, kind: str) -> tuple[Any, str, dict[str, Outcome]]:
            if (side, kind) not in computed:
                derivation = registered[kind]
                upstream = {d: outcome(side, d) for d in derivation.depends_on if d in registered}
                selection = derivation.select(self._source(derivation, sides[side], upstream))
                computed[side, kind] = (selection, self._fingerprint(derivation, sides[side], selection, externals[kind]), upstream)
            return computed[side, kind]

        def outcome(side: str, kind: str) -> Outcome:
            if (side, kind) not in outcomes:
                selection, input_fingerprint, upstream = selected(side, kind)
                outcomes[side, kind] = self._peek(project_id, registered[kind], selection, input_fingerprint, externals[kind], upstream)
            return outcomes[side, kind]

        impacted: set[str] = set()
        for derivation in derivations:
            kind = derivation.artifact_type
            if derivation.depends_on and not impacted.intersection(derivation.depends_on):
                continue  # equal upstream fingerprints give equal upstream outcomes, so equal selections
            if selected("base", kind)[1] != selected("candidate", kind)[1]:
                impacted.add(kind)
        return sorted(impacted, key=_utf16)

    def _peek(self, project_id, derivation, selection, input_fingerprint, external, upstream) -> Outcome:
        """An outcome for a fingerprint, from a reusable stored row or derived now, without storing it."""
        with self.store.transaction() as tx:
            hit = tx.find_reusable_artifact(project_id, derivation.artifact_type, input_fingerprint, derivation.generator_version)
        return _outcome(hit) if hit is not None else self._run(derivation, project_id, selection, external, upstream)

    # --- derivation and reuse (DEP-001 §7) -------------------------------------------------

    def derive_revision(self, project_id: str, revision_id: str, *, now: datetime) -> dict[str, str]:
        """Store every registered artifact for one revision (after commit), reusing unchanged ones."""
        with self.store.transaction() as tx:
            snapshot = load_snapshot(tx, project_id, revision_id)
            plans = [(d, self._external(tx, project_id, d)) for d in self.registry.ordered()]
        outcomes: dict[str, Outcome] = {}
        for derivation, external in plans:  # dependency order: the estimate sees this revision's schedule
            upstream = {d: outcomes[d] for d in derivation.depends_on if d in outcomes}
            outcomes[derivation.artifact_type] = self._obtain(project_id, snapshot, derivation, external, upstream, now)
        return {kind: (outcomes[kind].status if kind in outcomes else "MISSING") for kind in ARTIFACT_TYPES}

    def _obtain(self, project_id, snapshot, derivation, external, upstream, now) -> Outcome:
        """Copy a reusable row of the same project, type, fingerprint, and generator version, or derive."""
        selection = self._select(derivation, snapshot, upstream)
        input_fingerprint = self._fingerprint(derivation, snapshot, selection, external)
        kind = derivation.artifact_type
        with self.store.transaction() as tx:
            hit = tx.find_reusable_artifact(project_id, kind, input_fingerprint, derivation.generator_version)
            if hit is not None:  # same status, payload, warnings, and generated_at; this revision's own row
                tx.put_artifact(replace(hit, revision_id=snapshot.revision_id))
        if hit is not None:
            log.info("artifact cache hit: project=%s revision=%s type=%s generator=%s", project_id, snapshot.revision_id, kind,
                     derivation.generator_version)
            return _outcome(hit)
        started = time.perf_counter()
        outcome = self._run(derivation, project_id, selection, external, upstream)
        log.info("artifact cache miss: project=%s revision=%s type=%s generator=%s status=%s duration_ms=%.1f%s", project_id,
                 snapshot.revision_id, kind, derivation.generator_version, outcome.status, (time.perf_counter() - started) * 1000,
                 f" error={outcome.error['code']}" if outcome.error else "")
        with self.store.transaction() as tx:  # one transaction per artifact (ART-001 §4)
            tx.put_artifact(self._row(project_id, snapshot.revision_id, derivation, input_fingerprint, outcome, now))
        return outcome

    def _run(self, derivation, project_id, selection, external, upstream) -> Outcome:
        blocked = [d for d in derivation.depends_on if upstream.get(d) is None or upstream[d].status != "CURRENT"]
        if blocked:
            return Outcome("FAILED", error={"code": "UPSTREAM_NOT_CURRENT", "message": f"Depends on {', '.join(blocked)}, which is not CURRENT."})
        if isinstance(selection, _SelectorFailed):
            return Outcome("FAILED", error={"code": "DERIVATION_FAILED", "message": f"Derivation raised {selection.name}."})
        try:
            outcome = derivation.derive(DerivationContext(project_id, selection, external))
            if outcome.payload is not None:
                canonical_json(outcome.payload)  # payloads must be I-JSON (storable, fingerprintable)
            return outcome
        except CanonicalizationError:
            return Outcome("FAILED", error={"code": "DERIVATION_FAILED", "message": "Derivation produced a payload that is not I-JSON."})
        except Exception as exc:  # noqa: BLE001 - a failed derivation must never affect the revision
            return Outcome("FAILED", error={"code": "DERIVATION_FAILED", "message": f"Derivation raised {type(exc).__name__}."})

    @staticmethod
    def _row(project_id, revision_id, derivation, input_fingerprint, outcome, now) -> ArtifactRow:
        return ArtifactRow(
            project_id=project_id,
            revision_id=revision_id,
            artifact_type=derivation.artifact_type,
            input_fingerprint=input_fingerprint,
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

    def _state(self, tx, project_id: str, snapshot: Snapshot, kind: str, memo: dict | None = None):
        """(status, matching row or None, derivation or None) per ART-001 §6.

        A dependent's expected fingerprint uses its dependencies' stored outcomes for the same
        revision. A dependency without a matching row is not CURRENT, so the dependent's stored row
        reads as STALE until reading it derives the dependency first.
        """
        memo = {} if memo is None else memo
        if kind in memo:
            return memo[kind]
        derivation = self.registry.derivations.get(kind)
        if derivation is None:
            memo[kind] = ("MISSING", None, None)
            return memo[kind]
        upstream = {}
        for dependency in derivation.depends_on:
            status, row, _ = self._state(tx, project_id, snapshot, dependency, memo)
            upstream[dependency] = Outcome(status, row.payload if row else None)  # type: ignore[arg-type]
        selection = self._select(derivation, snapshot, upstream)
        expected = self._fingerprint(derivation, snapshot, selection, self._external(tx, project_id, derivation))
        rows = tx.get_artifacts(snapshot.revision_id, kind)
        match = next((r for r in rows if r.input_fingerprint == expected), None)
        if match is not None:
            memo[kind] = (match.status, match, derivation)
        else:
            memo[kind] = ("STALE" if rows else "MISSING", None, derivation)
        return memo[kind]

    def manifest(self, project_id: str, revision_id: str | None = None) -> dict[str, Any]:
        """Read-only manifest of all five types (artifacts.md §3). Never derives or copies."""
        with self.store.transaction() as tx:
            snapshot, head = self._resolve(tx, project_id, revision_id)
            memo: dict = {}
            entries = []
            for kind in ARTIFACT_TYPES:
                status, row, derivation = self._state(tx, project_id, snapshot, kind, memo)
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
        """Envelope for one artifact; when missing or stale, reused or derived on demand (ART-001 §4, §6; DEP-001 §7.3)."""
        if artifact_type not in ARTIFACT_TYPES:
            raise NotFound("Unknown artifact type.")
        with self.store.transaction() as tx:
            snapshot, head = self._resolve(tx, project_id, revision_id)
            status, row, derivation = self._state(tx, project_id, snapshot, artifact_type)
        if derivation is None:
            return self._envelope(project_id, snapshot, head, artifact_type, None, None, "MISSING")
        if row is None:  # MISSING or STALE: reuse or derive now (lazy recompute)
            self._derive_one(project_id, snapshot, derivation, now)
            with self.store.transaction() as tx:
                status, row, derivation = self._state(tx, project_id, snapshot, artifact_type)
        return self._envelope(project_id, snapshot, head, artifact_type, derivation, row, status)

    def _derive_one(self, project_id: str, snapshot: Snapshot, derivation: Derivation, now: datetime) -> None:
        upstream: dict[str, Outcome] = {}
        for dependency in derivation.depends_on:
            envelope = self.get_artifact(project_id, dependency, snapshot.revision_id, now=now)
            upstream[dependency] = Outcome(envelope["status"], envelope.get("payload"))
        with self.store.transaction() as tx:
            external = self._external(tx, project_id, derivation)
        self._obtain(project_id, snapshot, derivation, external, upstream, now)

    @staticmethod
    def _envelope(project_id, snapshot, head, kind, derivation, row, status) -> dict[str, Any]:
        standing = STANDING_WARNINGS.get(kind, (PRELIMINARY_WARNING,))  # AC-08 (and ART-003 §4.9): always present
        warnings = [*standing, *(row.warnings if row else [])]
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


def _outcome(row: ArtifactRow) -> Outcome:
    return Outcome(row.status, row.payload, tuple(dict(w) for w in row.warnings), row.error)  # type: ignore[arg-type]
