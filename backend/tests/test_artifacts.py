"""ART-001 acceptance tests (§7) with stub derivations, against both stores."""

from __future__ import annotations

import json

import jsonschema
import pytest

from conftest import REPO_ROOT
from homedesign.dependencies import ARTIFACT_TYPES, ArtifactService, Derivation, Outcome, registry_of
from homedesign.model.canonical import canonical_snapshot_value, fingerprint
from homedesign.project import NotFound, ProjectService
from test_project import ACTOR, KEY, T0, at, cid, create, head, roof_cmd

SCHEMA = json.loads((REPO_ROOT / "docs/architecture/schemas/artifacts.v1.schema.json").read_text())


def _validator(name):
    return jsonschema.Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{name}"})


def stub(kind, version="1", *, fail=False, nan=False):
    def derive(ctx):
        if fail:
            raise ValueError("boom")
        members = sum(e.kind == "TimberMember" for e in ctx.snapshot.entities)
        return Outcome("CURRENT", {"kind": kind, "members": float("nan") if nan else members})

    return Derivation(kind, f"{kind}-stub", version, derive)


def estimate_stub(book: dict):
    def external(tx, project_id):
        return {"price_book": book.get("value")}

    def derive(ctx):
        if ctx.external["price_book"] is None:
            return Outcome("UNAVAILABLE", {"coverage": "none"}, ({"code": "COST_INPUTS_MISSING", "message": "No prices."},))
        return Outcome("CURRENT", {"coverage": "complete", "members": ctx.upstream["timber_schedule"].payload["members"]})

    return Derivation("preliminary_estimate", "estimate-stub", "1", derive, depends_on=("timber_schedule",), external_inputs=external)


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
    committed = svc.commit(created.project_id, roof_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
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
    expected = fingerprint({
        "revision_id": snapshot.revision_id,
        "model_schema_version": snapshot.model_schema_version,
        "generator_id": "plan2d-stub",
        "generator_version": "1",
        "snapshot": canonical_snapshot_value(snapshot),
    })
    assert envelope["input_fingerprint"] == expected
    assert envelope["payload"] == {"kind": "plan2d", "members": 58}
    _validator("ArtifactEnvelope").validate(envelope)
    unavailable = svc.artifacts.get_artifact(pid, "preliminary_estimate", now=T0)
    assert unavailable["status"] == "UNAVAILABLE" and unavailable["payload"] == {"coverage": "none"}
    assert [w["code"] for w in unavailable["warnings"]] == ["PRELIMINARY_UNVERIFIED", "COST_INPUTS_MISSING"]


# 3. freshness --------------------------------------------------------------------------------


def test_old_head_artifacts_never_current_for_new_head(store):
    svc = service(store)
    created = create(svc)
    old = svc.artifacts.get_artifact(created.project_id, "mesh3d", now=T0)
    new_head = svc.commit(created.project_id, roof_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1)).revision_id
    current = svc.artifacts.get_artifact(created.project_id, "mesh3d", now=at(1))
    assert current["source_revision_id"] == new_head != old["source_revision_id"]
    assert current["input_fingerprint"] != old["input_fingerprint"]


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
    assert envelope["status"] == "CURRENT" and envelope["payload"] == {"coverage": "complete", "members": 58}


# 7. historical revisions -----------------------------------------------------------------------


def test_historical_artifacts_are_flagged_not_head(store):
    svc = service(store)
    created = create(svc)
    svc.commit(created.project_id, roof_cmd(svc, created.project_id), actor_id=ACTOR, now=at(1))
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
    svc = ProjectService(store, token_key=KEY)  # production default registry: nothing registered yet
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
