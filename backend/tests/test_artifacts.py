"""ART-001 acceptance tests (§7) with stub derivations, against both stores."""

from __future__ import annotations

import json
from collections import Counter

import jsonschema
import pytest

from conftest import REPO_ROOT
from homedesign.dependencies import ARTIFACT_TYPES, ArtifactService, Derivation, Outcome, Registry, registry_of
from homedesign.model.canonical import fingerprint
from homedesign.project import NotFound, ProjectService
from test_project import ACTOR, KEY, T0, at, cid, create, head, preview_commit, routine_cmd, width_cmd

SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())


def _validator(name):
    return jsonschema.Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"})


CALLS: Counter = Counter()  # derive calls per stub type, for the reuse tests


def select_stub(snapshot):
    """An exact stub selection (DEP-001 §4.1): the payload is a function of it, and of nothing else."""
    width = next(e.width_m for e in snapshot.entities if e.kind == "Footprint")
    return {"members": sum(e.kind == "TimberMember" for e in snapshot.entities), "width_m": width}


def stub(kind, version="1", *, fail=False, nan=False):
    def derive(ctx):
        CALLS[kind] += 1
        if fail:
            raise ValueError("boom")
        return Outcome("CURRENT", {"kind": kind, "members": float("nan") if nan else ctx.selection["members"], "width_m": ctx.selection["width_m"]})

    return Derivation(kind, f"{kind}-stub", version, select_stub, derive)


def estimate_stub(book: dict):
    def external(tx, project_id):
        return {"price_book": book.get("value")}

    def select(upstream):
        schedule = upstream["timber_schedule"]
        return {"members": schedule.payload["members"] if schedule is not None and schedule.status == "CURRENT" else None}

    def derive(ctx):
        CALLS["preliminary_estimate"] += 1
        if ctx.external["price_book"] is None:
            return Outcome("UNAVAILABLE", {"coverage": "none"}, ({"code": "COST_INPUTS_MISSING", "message": "No prices."},))
        return Outcome("CURRENT", {"coverage": "complete", "members": ctx.selection["members"]})

    return Derivation("preliminary_estimate", "estimate-stub", "1", select, derive, depends_on=("timber_schedule",), external_inputs=external)


def registry(book=None, **overrides):
    book = {} if book is None else book
    parts = {k: stub(k) for k in ("plan2d", "mesh3d", "timber_schedule")} | {"preliminary_estimate": estimate_stub(book)}
    parts.update(overrides)
    return registry_of(parts.values())


def service(store, reg=None):
    return ProjectService(store, token_key=KEY, registry=reg if reg is not None else registry())


EXPECTED = {"plan2d": "CURRENT", "mesh3d": "CURRENT", "timber_schedule": "CURRENT", "preliminary_estimate": "UNAVAILABLE"}


# 1. every revision has artifacts ---------------------------------------------------------


def test_create_and_commit_report_stored_statuses(store):
    svc = service(store)
    created = create(svc)
    assert created.body()["artifact_statuses"] == EXPECTED
    manifest = svc.artifacts.manifest(created.project_id)
    assert [e["artifact_type"] for e in manifest["artifacts"]] == list(ARTIFACT_TYPES)
    assert {e["artifact_type"]: e["status"] for e in manifest["artifacts"]} == EXPECTED
    committed = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
    assert committed.http_status == 201 and committed.body()["artifact_statuses"] == EXPECTED
    assert svc.artifacts.manifest(created.project_id)["revision_id"] == committed.revision_id
    _validator("Manifest").validate(manifest)


# 2. envelope contract ----------------------------------------------------------------------


def test_envelope_contract_and_fingerprint(store):
    svc = service(store)
    pid = create(svc).project_id
    envelope = svc.artifacts.get_artifact(pid, "plan2d", now=T0)
    assert (envelope["status"], envelope["head"], envelope["suitability"]) == ("CURRENT", True, "preliminary")
    assert envelope["claims"] == {"structurally_verified": False, "construction_approved": False, "permit_ready": False}
    assert envelope["warnings"][0]["code"] == "PRELIMINARY_UNVERIFIED"
    snapshot = head(svc, pid)
    expected = fingerprint({  # DEP-001 §5: the selection and the generator, never the revision
        "selection": select_stub(snapshot),
        "generator_id": "plan2d-stub",
        "generator_version": "1",
        "model_schema_version": snapshot.model_schema_version,
    })
    assert envelope["input_fingerprint"] == expected
    assert envelope["payload"] == {"kind": "plan2d", "members": 193, "width_m": 10.9728}
    _validator("ArtifactEnvelope").validate(envelope)
    unavailable = svc.artifacts.get_artifact(pid, "preliminary_estimate", now=T0)
    assert unavailable["status"] == "UNAVAILABLE" and unavailable["payload"] == {"coverage": "none"}
    assert [w["code"] for w in unavailable["warnings"]] == ["PRELIMINARY_UNVERIFIED", "COST_INPUTS_MISSING"]


# 3. freshness --------------------------------------------------------------------------------


def test_old_head_artifacts_never_current_for_new_head(store):
    """artifacts.md §10 test 5 (AC-07), with a command that changes the mesh's inputs (DEP-001 §12)."""
    svc = service(store)
    created = create(svc)
    old = svc.artifacts.get_artifact(created.project_id, "mesh3d", now=T0)
    new_head = preview_commit(svc, created.project_id, width_cmd(svc, created.project_id, 12.192), now=at(1)).revision_id
    current = svc.artifacts.get_artifact(created.project_id, "mesh3d", now=at(1))
    assert current["source_revision_id"] == new_head != old["source_revision_id"]
    assert current["input_fingerprint"] != old["input_fingerprint"]
    assert svc.artifacts.get_artifact(created.project_id, "mesh3d", created.revision_id, now=at(1))["head"] is False
    # Reuse (D056 item 3): after AddSection the envelope names the new revision, with the base's fingerprint.
    reused_head = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(2)).revision_id
    reused = svc.artifacts.get_artifact(created.project_id, "mesh3d", now=at(2))
    assert (reused["source_revision_id"], reused["head"], reused["status"]) == (reused_head, True, "CURRENT")
    assert reused["input_fingerprint"] == current["input_fingerprint"] and reused["generated_at"] == current["generated_at"]


# 4. failure isolation ----------------------------------------------------------------------------


def test_failed_derivation_does_not_affect_revision(store):
    svc = service(store, registry(mesh3d=stub("mesh3d", fail=True)))
    created = create(svc)
    statuses = created.body()["artifact_statuses"]
    assert statuses == EXPECTED | {"mesh3d": "FAILED"}
    assert svc.get_revision(created.project_id, created.revision_id).revision_id == created.revision_id
    failed = svc.artifacts.get_artifact(created.project_id, "mesh3d", now=T0)
    assert failed["error"]["code"] == "DERIVATION_FAILED" and failed["payload"] is None
    assert "boom" not in failed["error"]["message"]  # no internals leak


def test_dependent_of_failed_derivation_fails(store):
    svc = service(store, registry(timber_schedule=stub("timber_schedule", fail=True)))
    created = create(svc)
    assert created.body()["artifact_statuses"]["preliminary_estimate"] == "FAILED"
    error = svc.artifacts.get_artifact(created.project_id, "preliminary_estimate", now=T0)["error"]
    assert error["code"] == "UPSTREAM_NOT_CURRENT"


def test_non_i_json_payload_is_a_failure(store):
    svc = service(store, registry(plan2d=stub("plan2d", nan=True)))
    assert create(svc).body()["artifact_statuses"]["plan2d"] == "FAILED"


# 5./6. lazy recompute ----------------------------------------------------------------------------


def test_missing_artifacts_are_derived_on_read(store):
    svc = service(store)
    created = create(svc)
    with store.transaction() as tx:
        tx.delete_artifacts(created.revision_id)  # simulate a crash between commit and derivation
    assert set(svc.artifacts.statuses(created.project_id, created.revision_id).values()) == {"MISSING"}
    # Reading the estimate derives its dependency first.
    assert svc.artifacts.get_artifact(created.project_id, "preliminary_estimate", now=at(2))["status"] == "UNAVAILABLE"
    statuses = svc.artifacts.statuses(created.project_id, created.revision_id)
    assert statuses == {"plan2d": "MISSING", "mesh3d": "MISSING", "timber_schedule": "CURRENT", "preliminary_estimate": "UNAVAILABLE"}


def test_generator_version_bump_makes_artifacts_stale(store):
    created = create(service(store))
    bumped = ArtifactService(store, registry(plan2d=stub("plan2d", version="2")))
    assert bumped.statuses(created.project_id, created.revision_id)["plan2d"] == "STALE"
    envelope = bumped.get_artifact(created.project_id, "plan2d", now=at(3))
    assert (envelope["status"], envelope["generator_version"]) == ("CURRENT", "2")


def test_external_input_change_makes_only_that_artifact_stale(store):
    book = {}
    svc = service(store, registry(book))
    created = create(svc)
    book["value"] = {"currency": "USD", "rows": []}
    statuses = svc.artifacts.statuses(created.project_id, created.revision_id)
    assert statuses == {"plan2d": "CURRENT", "mesh3d": "CURRENT", "timber_schedule": "CURRENT", "preliminary_estimate": "STALE"}
    envelope = svc.artifacts.get_artifact(created.project_id, "preliminary_estimate", now=at(4))
    assert envelope["status"] == "CURRENT" and envelope["payload"] == {"coverage": "complete", "members": 193}
    assert envelope["source_revision_id"] == created.revision_id


# 7. historical revisions -----------------------------------------------------------------------


def test_historical_artifacts_are_flagged_not_head(store):
    svc = service(store)
    created = create(svc)
    svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
    old = svc.artifacts.get_artifact(created.project_id, "plan2d", created.revision_id, now=at(2))
    assert (old["status"], old["head"], old["source_revision_id"]) == ("CURRENT", False, created.revision_id)
    assert svc.artifacts.manifest(created.project_id, created.revision_id)["head"] is False
    assert svc.artifacts.manifest(created.project_id)["head"] is True


# 8. determinism -------------------------------------------------------------------------------------


def test_rederivation_stores_one_row(store):
    svc = service(store)
    created = create(svc)
    first = svc.artifacts.get_artifact(created.project_id, "timber_schedule", now=T0)
    svc.artifacts.derive_revision(created.project_id, created.revision_id, now=at(5))
    with store.transaction() as tx:
        rows = tx.get_artifacts(created.revision_id, "timber_schedule")
    assert len(rows) == 1
    again = svc.artifacts.get_artifact(created.project_id, "timber_schedule", now=at(6))
    assert again == first  # the first stored row is kept, including generated_at


# no derivations registered, errors, no-ops -------------------------------------------------------------


def test_unregistered_types_are_missing(store):
    svc = ProjectService(store, token_key=KEY, registry=Registry())  # nothing registered
    created = create(svc)
    assert set(created.body()["artifact_statuses"].values()) == {"MISSING"}
    envelope = svc.artifacts.get_artifact(created.project_id, "plan2d", now=T0)
    assert (envelope["status"], envelope["generator_id"], envelope["payload"]) == ("MISSING", None, None)


def test_unknown_type_revision_or_project(store):
    svc = service(store)
    pid = create(svc).project_id
    with pytest.raises(NotFound):
        svc.artifacts.get_artifact(pid, "ifc", now=T0)
    with pytest.raises(NotFound):
        svc.artifacts.get_artifact(pid, "plan2d", cid(), now=T0)
    with pytest.raises(NotFound):
        svc.artifacts.manifest(cid())


def test_noop_commit_reports_current_statuses_without_rederiving(store):
    svc = service(store)
    created = create(svc)
    fp = next(e for e in head(svc, created.project_id).entities if e.kind == "Footprint")
    command = {
        "command_id": cid(), "project_id": created.project_id, "base_revision_id": created.revision_id,
        "type": "SetFootprintDimensions", "args": {"width_m": fp.width_m, "depth_m": fp.depth_m},
    }
    result = svc.commit(created.project_id, command, actor_id=ACTOR, now=at(1))
    assert result.is_noop and result.body()["artifact_statuses"] == EXPECTED


# reuse across revisions (DEP-001 §7, §14 items 4, 6, 7) ------------------------------------------------


def _rows(store, revision_id):
    with store.transaction() as tx:
        return {kind: tx.get_artifacts(revision_id, kind) for kind in ARTIFACT_TYPES}


def test_unchanged_artifacts_are_copied_without_deriving(store):
    svc = service(store)
    created = create(svc)
    CALLS.clear()
    committed = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))  # AddSection
    assert committed.body()["artifact_statuses"] == EXPECTED and sum(CALLS.values()) == 0  # no derivation ran
    base, new = _rows(store, created.revision_id), _rows(store, committed.revision_id)
    for kind in ARTIFACT_TYPES:
        ([old], [copy]) = base[kind], new[kind]
        assert copy.revision_id == committed.revision_id
        assert (copy.input_fingerprint, copy.status, copy.payload, copy.warnings, copy.generated_at) == (
            old.input_fingerprint, old.status, old.payload, old.warnings, old.generated_at)
    envelope = svc.artifacts.get_artifact(created.project_id, "plan2d", now=at(2))
    assert (envelope["source_revision_id"], envelope["head"]) == (committed.revision_id, True)


def test_failed_rows_are_derived_again_not_copied(store):
    svc = service(store, registry(mesh3d=stub("mesh3d", fail=True)))
    created = create(svc)
    CALLS.clear()
    committed = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
    assert CALLS == Counter({"mesh3d": 1})  # only the FAILED artifact ran
    [row] = _rows(store, committed.revision_id)["mesh3d"]
    assert (row.status, row.error["code"], row.generated_at) == ("FAILED", "DERIVATION_FAILED", at(1))


def test_upstream_not_current_stays_failed(store):
    svc = service(store, registry(timber_schedule=stub("timber_schedule", fail=True)))
    created = create(svc)
    committed = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
    assert committed.body()["artifact_statuses"]["preliminary_estimate"] == "FAILED"
    error = svc.artifacts.get_artifact(created.project_id, "preliminary_estimate", now=at(2))["error"]
    assert error["code"] == "UPSTREAM_NOT_CURRENT"


def test_copied_rows_survive_deleting_the_source_rows(store):
    svc = service(store)
    created = create(svc)
    committed = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
    with store.transaction() as tx:
        tx.delete_artifacts(created.revision_id)
    assert svc.artifacts.statuses(created.project_id, committed.revision_id) == EXPECTED
    assert svc.artifacts.get_artifact(created.project_id, "mesh3d", now=at(2))["generated_at"] == "2026-11-19T12:00:00.000000Z"


def test_lazy_recompute_reuses_a_row_of_another_revision(store):
    svc = service(store)
    created = create(svc)
    committed = svc.commit(created.project_id, routine_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
    with store.transaction() as tx:
        tx.delete_artifacts(committed.revision_id)  # a crash between commit and derivation
    assert set(svc.artifacts.statuses(created.project_id, committed.revision_id).values()) == {"MISSING"}
    CALLS.clear()
    envelope = svc.artifacts.get_artifact(created.project_id, "preliminary_estimate", now=at(2))  # and its schedule first
    assert sum(CALLS.values()) == 0
    assert (envelope["status"], envelope["source_revision_id"], envelope["generated_at"]) == (
        "UNAVAILABLE", committed.revision_id, "2026-11-19T12:00:00.000000Z")
    assert svc.artifacts.statuses(created.project_id, committed.revision_id) == {
        "plan2d": "MISSING", "mesh3d": "MISSING", "timber_schedule": "CURRENT", "preliminary_estimate": "UNAVAILABLE"}


def test_selector_errors_fail_the_derivation_only(store):
    def broken(snapshot):
        raise KeyError("missing")

    plan = Derivation("plan2d", "plan2d-stub", "1", broken, stub("plan2d").derive)
    svc = service(store, registry(plan2d=plan))
    created = create(svc)
    assert created.body()["artifact_statuses"] == EXPECTED | {"plan2d": "FAILED"}
    envelope = svc.artifacts.get_artifact(created.project_id, "plan2d", now=T0)
    assert envelope["status"] == "FAILED" and envelope["error"] == {"code": "DERIVATION_FAILED", "message": "Derivation raised KeyError."}
