"""MODEL-004 acceptance tests (§8). Each runs against the in-memory and PostgreSQL stores unless noted."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from conftest import FIXTURE
from homedesign.model import canonical_snapshot, codes, snapshot_fingerprint
from homedesign.model.jcs import canonical_json
from homedesign.model.schema import Snapshot
from homedesign.project import (
    CommandRejected,
    CorruptRevision,
    IdempotencyConflict,
    MemoryStore,
    NotFound,
    PreviewExpired,
    PreviewInvalid,
    PreviewRequired,
    ProjectService,
    RevisionConflict,
)
from homedesign.project.postgres import PostgresStore
from homedesign.project.store import ProjectRow, RevisionRow

KEY = b"test-preview-signing-key-0123456"
ACTOR = "00000000-0000-4000-8000-000000000001"
ACTOR_B = "00000000-0000-4000-8000-000000000002"
T0 = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def cid() -> str:
    return str(uuid.uuid4())


def service(store) -> ProjectService:
    return ProjectService(store, token_key=KEY)


def create(svc, actor=ACTOR):
    return svc.create_project({"command_id": cid(), "type": "CreateReferenceProject", "args": {}}, actor_id=actor, now=T0)


def head(svc, project_id):
    p = svc.get_project(project_id)
    return svc.get_revision(project_id, p["head_revision_id"])


def envelope(svc, project_id, type_, args, command_id=None, base=None):
    return {
        "command_id": command_id or cid(),
        "project_id": project_id,
        "base_revision_id": base or svc.get_project(project_id)["head_revision_id"],
        "type": type_,
        "args": args,
    }


def width_cmd(svc, project_id, width, **kw):
    fp = next(e for e in head(svc, project_id).entities if e.kind == "Footprint")
    return envelope(svc, project_id, "SetFootprintDimensions", {"width_m": width, "depth_m": fp.depth_m}, **kw)


def roof_cmd(svc, project_id, pitch=0.5, **kw):
    return envelope(svc, project_id, "SetGableRoofParameters", {"pitch_rad": pitch, "eave_overhang_m": 0.6096}, **kw)


def preview_commit(svc, project_id, command, *, actor=ACTOR, now=T0):
    p = svc.preview(project_id, command, actor_id=actor, now=now)
    return svc.commit(project_id, command, p.preview_token, actor_id=actor, now=now)


def counts(svc, project_id):
    return len(svc.list_revisions(project_id)), len(svc.list_operations(project_id)), svc.get_project(project_id)["head_revision_id"]


# 1. create ------------------------------------------------------------------------


def test_create_and_replay(store):
    svc = service(store)
    command = {"command_id": cid(), "type": "CreateReferenceProject", "args": {}}
    first = svc.create_project(command, actor_id=ACTOR, now=T0)
    assert (first.http_status, first.sequence, first.parent_revision_id) == (201, 1, None)
    assert svc.get_project(first.project_id)["head_revision_id"] == first.revision_id
    assert [o.result for o in svc.list_operations(first.project_id)] == ["committed"]
    replay = svc.create_project(command, actor_id=ACTOR, now=at(1))
    assert replay.http_status == 200
    assert replay.body() == first.body() | {"replayed": True}
    assert counts(svc, first.project_id)[:2] == (1, 1)
    # Same command_id from another actor is a different command: a second project.
    other = svc.create_project(command, actor_id=ACTOR_B, now=T0)
    assert other.http_status == 201 and other.project_id != first.project_id


# 2. previews write nothing --------------------------------------------------------


def test_previews_write_nothing(store):
    svc = service(store)
    pid = create(svc).project_id
    before = counts(svc, pid)
    for width in (11.0, 12.0, 13.0):
        svc.preview(pid, width_cmd(svc, pid, width), actor_id=ACTOR, now=T0)
    with pytest.raises(CommandRejected):
        svc.preview(pid, width_cmd(svc, pid, -1), actor_id=ACTOR, now=T0)
    assert counts(svc, pid) == before


# 3. commit with a valid token -----------------------------------------------------------


def test_commit_with_token_matches_preview(store):
    svc = service(store)
    created = create(svc)
    pid = created.project_id
    command = width_cmd(svc, pid, 12.192)
    p = svc.preview(pid, command, actor_id=ACTOR, now=T0)
    assert p.body["confirmation_required"] and p.body["preview_token"] == p.preview_token
    result = svc.commit(pid, command, p.preview_token, actor_id=ACTOR, now=at(5))
    assert (result.http_status, result.sequence, result.parent_revision_id) == (201, 2, created.revision_id)
    assert result.revision_id == p.change.revision_id and result.operation_id == p.change.operation_id
    stored = svc.get_revision(pid, result.revision_id)
    assert {m.id for m in stored.entities if m.kind == "TimberMember"} == {m.id for m in p.change.candidate.entities if m.kind == "TimberMember"}
    assert result.body()["artifact_statuses"] == svc.artifacts.statuses(pid, result.revision_id)
    assert set(result.body()["artifact_statuses"]) == {"plan2d", "mesh3d", "timber_schedule", "preliminary_estimate"}


# 4. preview token rules ----------------------------------------------------------------


def test_consequential_commit_requires_token(store):
    svc = service(store)
    pid = create(svc).project_id
    with pytest.raises(PreviewRequired):
        svc.commit(pid, width_cmd(svc, pid, 12.192), actor_id=ACTOR, now=T0)
    assert svc.list_operations(pid)[-1].rejection_code == "PREVIEW_REQUIRED"


def test_expired_token(store):
    svc = service(store)
    pid = create(svc).project_id
    command = width_cmd(svc, pid, 12.192)
    token = svc.preview(pid, command, actor_id=ACTOR, now=T0).preview_token
    with pytest.raises(PreviewExpired):
        svc.commit(pid, command, token, actor_id=ACTOR, now=at(15.01))
    assert svc.commit(pid, command, token, actor_id=ACTOR, now=at(14.99)).http_status == 201


@pytest.mark.parametrize("variant", ["tampered", "other-actor", "other-command", "other-base", "other-key"])
def test_invalid_tokens(store, variant):
    svc = service(store)
    pid = create(svc).project_id
    command = width_cmd(svc, pid, 12.192)
    token = svc.preview(pid, command, actor_id=ACTOR, now=T0).preview_token
    actor = ACTOR
    if variant == "tampered":
        token = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]
    elif variant == "other-actor":
        actor = ACTOR_B
    elif variant == "other-command":
        command = width_cmd(svc, pid, 12.8016)
    elif variant == "other-base":
        assert svc.commit(pid, roof_cmd(svc, pid), actor_id=ACTOR, now=T0).http_status == 201  # head moves (routine)
        command = width_cmd(svc, pid, 12.192)  # same edit, rebased; the old token names the old base
    elif variant == "other-key":
        token = ProjectService(store, token_key=b"another-key").preview(pid, command, actor_id=ACTOR, now=T0).preview_token
    with pytest.raises(PreviewInvalid):
        svc.commit(pid, command, token, actor_id=actor, now=T0)


def test_routine_commit_needs_no_token(store):
    svc = service(store)
    pid = create(svc).project_id
    result = svc.commit(pid, roof_cmd(svc, pid), actor_id=ACTOR, now=T0)
    assert result.http_status == 201 and result.sequence == 2


def test_routine_commit_with_bad_token_is_rejected(store):
    svc = service(store)
    pid = create(svc).project_id
    with pytest.raises(PreviewInvalid):
        svc.commit(pid, roof_cmd(svc, pid), "not-a-token", actor_id=ACTOR, now=T0)


# 5. stale base ----------------------------------------------------------------------------


def test_stale_preview_is_a_revision_conflict(store):
    svc = service(store)
    pid = create(svc).project_id
    stale = width_cmd(svc, pid, 12.192)
    token = svc.preview(pid, stale, actor_id=ACTOR, now=T0).preview_token
    winner = preview_commit(svc, pid, width_cmd(svc, pid, 12.8016))
    before = canonical_snapshot(svc.get_revision(pid, winner.revision_id))
    with pytest.raises(RevisionConflict):
        svc.commit(pid, stale, token, actor_id=ACTOR, now=T0)
    assert svc.get_project(pid)["head_revision_id"] == winner.revision_id
    assert canonical_snapshot(svc.get_revision(pid, winner.revision_id)) == before
    assert svc.list_operations(pid)[-1].rejection_code == "REVISION_CONFLICT"


# 6. concurrency (PostgreSQL only) --------------------------------------------------------------


@pytest.mark.parametrize("round_", range(3))
def test_concurrent_commits_have_one_winner(pg_url, round_):
    svc = service(PostgresStore(pg_url))
    pid = create(svc).project_id
    commands = [roof_cmd(svc, pid, pitch) for pitch in (0.5, 0.6)]
    barrier, outcomes = threading.Barrier(2), []

    def worker(command):
        barrier.wait()
        try:
            outcomes.append(svc.commit(pid, command, actor_id=ACTOR, now=T0).http_status)
        except RevisionConflict:
            outcomes.append("conflict")

    threads = [threading.Thread(target=worker, args=(c,)) for c in commands]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(map(str, outcomes)) == ["201", "conflict"]
    assert svc.get_project(pid)["head_sequence"] == 2


def test_concurrent_identical_creations_create_one_project(pg_url):
    svc = service(PostgresStore(pg_url))
    command = {"command_id": cid(), "type": "CreateReferenceProject", "args": {}}
    barrier, results = threading.Barrier(2), []

    def worker():
        barrier.wait()
        results.append(svc.create_project(command, actor_id=ACTOR, now=T0))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r.http_status for r in results) == [200, 201]
    assert len({r.project_id for r in results}) == 1


# 7. retries ---------------------------------------------------------------------------------


def test_idempotent_retry_writes_nothing(store):
    svc = service(store)
    pid = create(svc).project_id
    command = width_cmd(svc, pid, 12.192)
    first = preview_commit(svc, pid, command)
    after_first = counts(svc, pid)
    retry = svc.commit(pid, command, actor_id=ACTOR, now=at(30))  # no token needed: replay comes first
    assert retry.http_status == 200 and retry.body() == first.body() | {"replayed": True}
    assert counts(svc, pid) == after_first


def test_reused_command_id_with_different_payload(store):
    svc = service(store)
    pid = create(svc).project_id
    command = width_cmd(svc, pid, 12.192)
    preview_commit(svc, pid, command)
    changed = dict(command, args={**command["args"], "width_m": 12.8016})
    with pytest.raises(IdempotencyConflict):
        svc.commit(pid, changed, actor_id=ACTOR, now=T0)
    assert svc.list_operations(pid)[-1].rejection_code == "IDEMPOTENCY_CONFLICT"


# 8. no-op ------------------------------------------------------------------------------------


def test_noop_commit(store):
    svc = service(store)
    pid = create(svc).project_id
    h = head(svc, pid)
    fp = next(e for e in h.entities if e.kind == "Footprint")
    command = width_cmd(svc, pid, fp.width_m)
    result = svc.commit(pid, command, actor_id=ACTOR, now=T0)  # consequential type, but a no-op: no token
    assert (result.http_status, result.is_noop, result.revision_id, result.sequence) == (200, True, h.revision_id, 1)
    assert svc.get_project(pid)["head_revision_id"] == h.revision_id
    assert [o.result for o in svc.list_operations(pid)] == ["committed", "noop"]
    replay = svc.commit(pid, command, actor_id=ACTOR, now=T0)
    assert replay.body() == result.body() | {"replayed": True}


# 9. rejection --------------------------------------------------------------------------------


def test_rejection_is_audited_but_does_not_reserve_command_id(store):
    svc = service(store)
    pid = create(svc).project_id
    command = width_cmd(svc, pid, -1)
    with pytest.raises(CommandRejected) as exc:
        svc.commit(pid, command, actor_id=ACTOR, now=T0)
    assert exc.value.result.code == codes.VALIDATION_FAILED
    assert any(i.code == codes.OUT_OF_RANGE and "args.width_m" in i.related_paths for i in exc.value.result.issues)
    rejected = svc.list_operations(pid)[-1]
    assert (rejected.result, rejected.rejection_code, rejected.command_id) == ("rejected", "VALIDATION_FAILED", command["command_id"])
    assert len(svc.list_revisions(pid)) == 1
    fixed = dict(command, args={**command["args"], "width_m": 12.192})
    assert preview_commit(svc, pid, fixed).http_status == 201  # same command_id, now valid


def test_malformed_command_is_audited(store):
    svc = service(store)
    pid = create(svc).project_id
    with pytest.raises(CommandRejected):
        svc.commit(pid, {"type": "SetFootprintDimensions"}, actor_id=ACTOR, now=T0)
    last = svc.list_operations(pid)[-1]
    assert (last.result, last.command_id, last.command) == ("rejected", None, None)


def test_unknown_project(store):
    svc = service(store)
    with pytest.raises(NotFound):
        svc.commit(str(uuid.uuid4()), {}, actor_id=ACTOR, now=T0)
    with pytest.raises(NotFound):
        svc.get_project("not-a-uuid")


# 10. round trip ------------------------------------------------------------------------------


def test_round_trip_preserves_canonical_bytes(store):
    """AC-05: what is stored and reopened is byte-identical (canonically) to what was committed."""
    svc = service(store)
    pid = create(svc).project_id
    command = width_cmd(svc, pid, 12.192)  # stations become generator output such as 12.192 × ⅓
    preview = svc.preview(pid, command, actor_id=ACTOR, now=T0)
    result = svc.commit(pid, command, preview.preview_token, actor_id=ACTOR, now=T0)
    stored = svc.get_revision(pid, result.revision_id)
    assert canonical_snapshot(stored) == canonical_snapshot(preview.change.candidate)
    assert stored.revision_id == result.revision_id and stored.parent_revision_id == result.parent_revision_id


def test_edge_values_survive_storage(store):
    """Fixture decimals, generator output, 1e-7, and -0 read back with identical canonical bytes."""
    doc = Snapshot.model_validate(FIXTURE).model_dump(mode="json")
    doc["project_id"] = str(uuid.uuid4())
    doc["revision_id"] = str(uuid.uuid4())
    fp = next(e for e in doc["entities"] if e["kind"] == "Footprint")
    fp["rotation_rad"] = -0.0
    material = next(e for e in doc["entities"] if e["kind"] == "Material")
    material["density_kg_m3"] = 1e-7
    member = next(e for e in doc["entities"] if e["kind"] == "TimberMember")
    member["end_m"][0] = 3.6575999999999995
    snapshot = Snapshot.model_validate(doc)
    with store.transaction() as tx:
        tx.insert_project(ProjectRow(doc["project_id"], doc["revision_id"], 1, T0, ACTOR))
        tx.insert_revision(RevisionRow(doc["revision_id"], doc["project_id"], None, 1, 1, snapshot.model_dump(mode="json"), snapshot_fingerprint(snapshot), T0))
    with store.transaction() as tx:
        row = tx.get_revision(doc["project_id"], doc["revision_id"])
    back = Snapshot.model_validate(row.snapshot)
    assert canonical_snapshot(back) == canonical_snapshot(snapshot)
    assert snapshot_fingerprint(back) == row.fingerprint
    assert next(e for e in row.snapshot["entities"] if e["id"] == member["id"])["end_m"][0] == 3.6575999999999995


# 11. immutability (PostgreSQL only) ---------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE revisions SET fingerprint = 'x' WHERE project_id = %s",
        "DELETE FROM revisions WHERE project_id = %s",
        "UPDATE operations SET result = 'rejected' WHERE project_id = %s",
        "DELETE FROM operations WHERE project_id = %s",
    ],
)
def test_revisions_and_operations_are_append_only(pg_url, statement):
    svc = service(PostgresStore(pg_url))
    pid = create(svc).project_id
    with psycopg.connect(pg_url) as conn, pytest.raises(psycopg.errors.RestrictViolation):
        conn.execute(statement, (pid,))


@pytest.mark.parametrize("table", ["revisions", "operations"])
def test_truncate_is_rejected(pg_url, table):
    with psycopg.connect(pg_url) as conn, pytest.raises(psycopg.errors.RestrictViolation):
        conn.execute(f"TRUNCATE {table} CASCADE")


# 12. deterministic replay -------------------------------------------------------------------------


def test_replaying_the_operation_log_reproduces_history(store):
    svc = service(store)
    pid = create(svc).project_id
    x = [{"id": line.id, "fraction": line.fraction} for line in next(e for e in head(svc, pid).entities if e.kind == "TimberGrid").x_lines]
    y = [{"id": line.id, "fraction": line.fraction} for line in next(e for e in head(svc, pid).entities if e.kind == "TimberGrid").y_lines]
    preview_commit(svc, pid, width_cmd(svc, pid, 12.192), now=at(1))
    preview_commit(svc, pid, envelope(svc, pid, "SetTimberGrid", {"x_lines": x[:2] + [{"fraction": 0.5}] + x[2:], "y_lines": y}), now=at(2))
    svc.commit(pid, roof_cmd(svc, pid), actor_id=ACTOR, now=at(3))
    first_rev = svc.list_revisions(pid)[0]["revision_id"]
    preview_commit(svc, pid, envelope(svc, pid, "UndoToRevision", {"target_revision_id": first_rev}), now=at(4))
    original = [(r["revision_id"], snapshot_fingerprint(svc.get_revision(pid, r["revision_id"]))) for r in svc.list_revisions(pid)]

    fresh = ProjectService(MemoryStore(), token_key=KEY, project_id_factory=lambda: pid)
    for op in svc.list_operations(pid):
        if op.result == "rejected":
            continue
        if op.command_type == "CreateReferenceProject":
            fresh.create_project(op.command, actor_id=op.actor_id, now=op.created_at)
        else:
            token = fresh.preview(pid, op.command, actor_id=op.actor_id, now=op.created_at).preview_token
            fresh.commit(pid, op.command, token, actor_id=op.actor_id, now=op.created_at)
    replayed = [(r["revision_id"], snapshot_fingerprint(fresh.get_revision(pid, r["revision_id"]))) for r in fresh.list_revisions(pid)]
    assert replayed == original and len(original) == 5


# 13. undo -----------------------------------------------------------------------------------------


def test_undo_across_stored_revisions(store):
    svc = service(store)
    created = create(svc)
    pid = created.project_id
    grid = next(e for e in head(svc, pid).entities if e.kind == "TimberGrid")
    x = [{"id": line.id, "fraction": line.fraction} for line in grid.x_lines if line.id != "x2"]
    y = [{"id": line.id, "fraction": line.fraction} for line in grid.y_lines]
    preview_commit(svc, pid, envelope(svc, pid, "SetTimberGrid", {"x_lines": x, "y_lines": y}))
    undo = preview_commit(svc, pid, envelope(svc, pid, "UndoToRevision", {"target_revision_id": created.revision_id}))
    restored, original = svc.get_revision(pid, undo.revision_id), svc.get_revision(pid, created.revision_id)
    content = lambda s: canonical_json({"b": s.model_dump(mode="json")["building"], "e": sorted(s.model_dump(mode="json")["entities"], key=lambda e: e["id"])})  # noqa: E731
    assert content(restored) == content(original) and undo.sequence == 3

    other = create(svc).project_id
    with pytest.raises(CommandRejected) as exc:
        svc.preview(pid, envelope(svc, pid, "UndoToRevision", {"target_revision_id": svc.get_project(other)["head_revision_id"]}), actor_id=ACTOR, now=T0)
    assert (exc.value.result.issues[0].code, exc.value.result.issues[0].path) == (codes.DANGLING_REFERENCE, "args.target_revision_id")


# 14. integrity (in-memory store hook) -------------------------------------------------------------


def test_corrupted_snapshot_is_refused():
    store = MemoryStore()
    svc = service(store)
    created = create(svc)
    doc = svc.get_revision(created.project_id, created.revision_id).model_dump(mode="json")
    next(e for e in doc["entities"] if e["kind"] == "Footprint")["width_m"] = 99.0
    store.corrupt_for_test(created.revision_id, doc)
    with pytest.raises(CorruptRevision):
        svc.get_revision(created.project_id, created.revision_id)
    with pytest.raises(CorruptRevision):
        svc.preview(created.project_id, roof_cmd(svc, created.project_id) | {"base_revision_id": created.revision_id}, actor_id=ACTOR, now=T0)


# 15. ordering --------------------------------------------------------------------------------------


def test_history_is_a_single_ordered_chain(store):
    svc = service(store)
    pid = create(svc).project_id
    for pitch in (0.4, 0.5, 0.6):
        svc.commit(pid, roof_cmd(svc, pid, pitch), actor_id=ACTOR, now=T0)
    history = svc.list_revisions(pid)
    assert [r["sequence"] for r in history] == [1, 2, 3, 4]
    assert history[0]["parent_revision_id"] is None
    assert all(b["parent_revision_id"] == a["revision_id"] for a, b in zip(history, history[1:]))
    assert [r["command_type"] for r in history] == ["CreateReferenceProject"] + ["SetGableRoofParameters"] * 3
    assert svc.get_project(pid)["head_sequence"] == 4


def test_actor_must_be_a_uuid(store):
    with pytest.raises(ValueError):
        create(service(store), actor="alice")
