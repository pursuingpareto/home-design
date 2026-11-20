"""API-001 acceptance tests (§9): the HTTP API over both stores, checked against the committed OpenAPI.

Every response a test receives through `Api` is validated against the operation's documented
response for its status code (interfaces.md §9, test 1).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
import threading
import uuid
from datetime import timedelta
from typing import Any

import jsonschema
import pytest
from fastapi.testclient import TestClient

from conftest import REPO_ROOT
from homedesign.api.app import create_app
from homedesign.api.settings import ConfigError, Settings
from homedesign.dependencies import Registry, registry_of
from homedesign.dependencies.registry import Derivation, Outcome
from homedesign.model import canonical_snapshot, codes
from homedesign.model.schema import Snapshot
from homedesign.model.schema_export import OPENAPI_PATH, render_openapi
from homedesign.model.limits import DEFAULT_MAX_BYTES
from homedesign.project import MemoryStore
from homedesign.project.postgres import PostgresStore
from test_project import ACTOR, ACTOR_B, KEY, T0, cid


from api_support import FULL_PRICES, BEAM_KEY, OPENAPI, POST_KEY, TOKENS, UUID_RE, Api, Clock, book, conforms, make_api, schema_for  # noqa: E402,F401


@pytest.fixture
def api(store) -> Api:
    return make_api(store)



# --- 1. the VS-01 flow end to end (AC-01, AC-02, AC-05, AC-07, AC-08) ----------------------


def test_vs01_flow(api):
    pid = api.create()
    statuses = {a["artifact_type"]: a["status"] for a in api.get(f"/api/v1/projects/{pid}/artifacts").json()["artifacts"]}
    assert statuses == {"plan2d": "CURRENT", "mesh3d": "CURRENT", "timber_schedule": "CURRENT", "preliminary_estimate": "UNAVAILABLE"}

    command = api.width(pid, 12.192)
    preview = api.preview(pid, command).json()
    assert preview["confirmation_required"] is True and preview["revision_id"]
    commit = api.commit(pid, command, preview["preview_token"])
    assert commit.status_code == 201
    head = commit.json()["revision_id"]
    assert head == preview["revision_id"] and api.head(pid) == head

    plan = api.get(f"/api/v1/projects/{pid}/artifacts/plan2d").json()
    mesh = api.get(f"/api/v1/projects/{pid}/artifacts/mesh3d").json()
    for envelope in (plan, mesh):
        assert envelope["status"] == "CURRENT" and envelope["source_revision_id"] == head
        assert envelope["suitability"] == "preliminary"
        assert "PRELIMINARY_UNVERIFIED" in [w["code"] for w in envelope["warnings"]]
    assert plan["payload"]["footprint"]["width_m"] == 12.192
    assert plan["payload"]["dimensions"][0]["value_m"] == 12.192
    assert mesh["payload"]["envelope"]["footprint_ring_m"][1] == [12.192, 0.0]

    response = api.get(f"/api/v1/projects/{pid}/revisions/{head}")
    stored = api.service.get_revision(pid, head)
    assert response.content == canonical_snapshot(stored)
    assert canonical_snapshot(Snapshot.model_validate(response.json())) == response.content

    revisions = api.get(f"/api/v1/projects/{pid}/revisions").json()["revisions"]
    assert [r["sequence"] for r in revisions] == [1, 2]
    assert revisions[1]["command_type"] == "SetFootprintDimensions"
    assert api.get(f"/api/v1/projects/{pid}").json()["permissions"] == ["read", "write"]


# --- project list (UI-001 §8.1) ---------------------------------------------------------------


def test_project_list_is_owner_only_and_newest_first(store):
    # Fresh actors: the PostgreSQL test database is shared by every test in the session.
    tokens = {"tok-a": str(uuid.uuid4()), "tok-b": str(uuid.uuid4())}
    clock = Clock()
    api = Api(create_app(Settings(preview_key=KEY, store="memory", dev_tokens=tokens), store=store, clock=clock), clock)
    assert api.get("/api/v1/projects").json() == {"projects": []}
    first = api.create()
    api.clock.now = T0 + timedelta(minutes=1)
    tied = sorted([api.create(), api.create()])  # same created_at: ordered by project_id
    api.clock.now = T0 + timedelta(minutes=2)
    newest = api.create()
    api.create(token="tok-b")
    api.commit(first, api.routine(first, 0.6))
    listed = api.get("/api/v1/projects").json()["projects"]
    assert [p["project_id"] for p in listed] == [newest, *tied, first]
    assert listed[-1]["head_sequence"] == 2 and listed[-1]["head_revision_id"] == api.head(first)
    assert listed[-1] == {k: v for k, v in api.get(f"/api/v1/projects/{first}").json().items() if k != "permissions"}
    assert len(api.get("/api/v1/projects", token="tok-b").json()["projects"]) == 1
    for token in (None, "nope"):
        assert api.get("/api/v1/projects", token=token).status_code == 401


# --- 2. contract matrix (interfaces.md §9) ---------------------------------------------------


def test_1_openapi_is_current_and_requests_conform():
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(), (
        "openapi.v1.json is stale. Run `uv run python -m homedesign.model.schema_export` and commit the result."
    )
    assert OPENAPI["openapi"].startswith("3.1")
    text = json.dumps(OPENAPI)
    for ref in set(re.findall(r'"\$ref": "#/components/schemas/([^"]+)"', text)):
        assert ref in OPENAPI["components"]["schemas"], ref
    assert "HTTPValidationError" not in OPENAPI["components"]["schemas"]
    # Example requests validate against the declared request bodies.
    pid, base = str(uuid.uuid4()), str(uuid.uuid4())
    command = {"command_id": cid(), "project_id": pid, "base_revision_id": base, "type": "SetFootprintDimensions", "args": {"width_m": 12.192, "depth_m": 7.3152}}
    conforms("Command", command)
    conforms("CreateProjectRequest", {"command_id": cid(), "type": "CreateReferenceProject", "args": {}})
    conforms("CommitRequest", {"command": command, "preview_token": "t"})
    conforms("PriceBook", book(**{POST_KEY: 3150}))
    with pytest.raises(jsonschema.ValidationError):
        conforms("CommitRequest", {"command": command, "extra": 1})
    for path, operations in OPENAPI["paths"].items():
        for method, operation in operations.items():
            assert operation["operationId"], (method, path)
            if method in ("post", "put"):
                assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"], (method, path)


def test_2_preview_writes_nothing(api):
    pid = api.create()
    before = (api.get(f"/api/v1/projects/{pid}").json(), api.get(f"/api/v1/projects/{pid}/revisions").json(), len(api.service.list_operations(pid)))
    assert api.preview(pid, api.width(pid, 12.192)).status_code == 200
    after = (api.get(f"/api/v1/projects/{pid}").json(), api.get(f"/api/v1/projects/{pid}/revisions").json(), len(api.service.list_operations(pid)))
    assert after == before


def test_3_commit_moves_head_exactly_once(api):
    pid = api.create()
    response = api.commit(pid, api.routine(pid, 0.6))
    assert response.status_code == 201 and response.json()["sequence"] == 2
    project = api.get(f"/api/v1/projects/{pid}").json()
    assert (project["head_sequence"], project["head_revision_id"]) == (2, response.json()["revision_id"])
    assert len(api.get(f"/api/v1/projects/{pid}/revisions").json()["revisions"]) == 2


@pytest.mark.parametrize("round_", range(3))
def test_4_concurrent_commits_have_one_winner(pg_url, round_):
    api = make_api(PostgresStore(pg_url))
    pid = api.create()
    commands = [api.routine(pid, pitch) for pitch in (0.5, 0.6)]
    barrier, outcomes = threading.Barrier(2), []

    def worker(command):
        client = Api(api.app, api.clock)  # one client per thread
        barrier.wait()
        response = client.commit(pid, command)
        outcomes.append((response.status_code, response.json().get("error", {}).get("code")))

    threads = [threading.Thread(target=worker, args=(c,)) for c in commands]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes, key=str) == sorted([(201, None), (409, "REVISION_CONFLICT")], key=str)
    assert api.get(f"/api/v1/projects/{pid}").json()["head_sequence"] == 2


def test_5_retry_is_replayed(api):
    pid = api.create()
    command = api.routine(pid, 0.6)
    first = api.commit(pid, command)
    retry = api.commit(pid, command)
    assert (first.status_code, retry.status_code) == (201, 200)
    assert retry.json() == first.json() | {"replayed": True}
    assert len(api.get(f"/api/v1/projects/{pid}/revisions").json()["revisions"]) == 2
    create = {"command_id": cid(), "type": "CreateReferenceProject", "args": {}}
    created, replayed = api.post("/api/v1/projects", create), api.post("/api/v1/projects", create)
    assert (created.status_code, replayed.status_code, replayed.json()["replayed"]) == (201, 200, True)
    assert created.json()["project_id"] == replayed.json()["project_id"]


def _project_routes(api, pid):
    rev = api.head(pid)
    command = api.routine(pid, 0.6)
    return [
        ("GET", f"/api/v1/projects/{pid}", None),
        ("POST", f"/api/v1/projects/{pid}/commands/preview", command),
        ("POST", f"/api/v1/projects/{pid}/commands/commit", {"command": command}),
        ("GET", f"/api/v1/projects/{pid}/revisions", None),
        ("GET", f"/api/v1/projects/{pid}/revisions/{rev}", None),
        ("GET", f"/api/v1/projects/{pid}/artifacts", None),
        ("GET", f"/api/v1/projects/{pid}/artifacts/plan2d", None),
        ("GET", f"/api/v1/projects/{pid}/artifacts/plan2d?revision_id={rev}", None),
        ("PUT", f"/api/v1/projects/{pid}/price-book", book(**{POST_KEY: 3150})),
        ("GET", f"/api/v1/projects/{pid}/price-book", None),
    ]


def test_6_other_actors_get_404_and_anonymous_callers_401(api):
    pid = api.create()
    missing = str(uuid.uuid4())
    routes = _project_routes(api, pid)
    for method, path, body in routes:
        other = api.call(method, path, token="tok-b", json_body=body)
        absent = api.call(method, path.replace(pid, missing), json_body=body)
        assert (other.status_code, other.json()["error"]["code"]) == (404, "NOT_FOUND"), (method, path)
        strip = lambda r: {**r.json()["error"], "request_id": None}  # noqa: E731
        assert strip(other) == strip(absent), "a foreign project must look exactly like a missing one"
        for token in (None, "nope"):
            anonymous = api.call(method, path, token=token, json_body=body)
            assert (anonymous.status_code, anonymous.json()["error"]["code"]) == (401, "UNAUTHORIZED")
            assert anonymous.headers["www-authenticate"] == "Bearer"
    anonymous = api.post("/api/v1/projects", {"command_id": cid(), "type": "CreateReferenceProject", "args": {}}, token=None)
    assert anonymous.status_code == 401
    # Nothing was written by the rejected calls.
    assert api.get(f"/api/v1/projects/{pid}").json()["head_sequence"] == 1
    assert api.get(f"/api/v1/projects/{pid}/price-book").json() == {"price_book": None}


def test_7_plan_mesh_schedule_share_source_revision(api):
    pid = api.create()
    api.commit(pid, api.routine(pid, 0.6))
    head = api.head(pid)
    sources = {api.get(f"/api/v1/projects/{pid}/artifacts/{t}").json()["source_revision_id"] for t in ("plan2d", "mesh3d", "timber_schedule")}
    assert sources == {head}


def test_8_unsupported_geometry_is_a_structured_422(api):
    pid = api.create()
    for route in ("preview", "commit"):
        command = api.width(pid, 23)
        response = api.preview(pid, command) if route == "preview" else api.commit(pid, command)
        error = response.json()["error"]
        assert (response.status_code, error["code"]) == (422, "UNSUPPORTED_CONFIGURATION")
        assert error["details"] and all("message" not in d for d in error["details"])
        assert {d["code"] for d in error["details"]} == {codes.OUT_OF_SUPPORTED_RANGE}
        assert any("args.width_m" in d.get("related_paths", []) for d in error["details"])
    assert api.get(f"/api/v1/projects/{pid}").json()["head_sequence"] == 1


# --- 3. error mapping (§5) ----------------------------------------------------------------------


def _error(response, status, code):
    assert response.status_code == status, response.json()
    error = response.json()["error"]
    assert error["code"] == code
    return error


def test_strict_bodies(api):
    pid = api.create()
    url = f"/api/v1/projects/{pid}/commands/preview"
    cases = [
        (b'{"command_id": "a", "command_id": "b"}', "command_id", codes.DUPLICATE_KEY),
        (b'{"args": {"width_m": NaN}}', "args.width_m", codes.NON_FINITE_NUMBER),
        (b'{"args": {"width_m": 1e400}}', "args.width_m", codes.NON_FINITE_NUMBER),
        (b'{"x": "\\ud800"}', "x", codes.MALFORMED_JSON),
        (b"{not json", "", codes.MALFORMED_JSON),
        (b"", "", codes.MALFORMED_JSON),
        (b"\xff", "", codes.MALFORMED_JSON),
        (b"[" * 200 + b"]" * 200, "", codes.PAYLOAD_LIMIT_EXCEEDED),
        (b'"' + b"a" * DEFAULT_MAX_BYTES + b'"', "", codes.PAYLOAD_LIMIT_EXCEEDED),
    ]
    for raw, path, code in cases:
        error = _error(api.call("POST", url, raw=raw), 422, "VALIDATION_FAILED")
        assert {"path": path, "code": code} in [{k: d[k] for k in ("path", "code")} for d in error["details"]], (raw[:40], error)
    for content_type in ("text/plain", "application/x-www-form-urlencoded", "application/jsonx"):
        error = _error(api.call("POST", url, raw=b"{}", content_type=content_type), 415, "VALIDATION_FAILED")
        assert error["details"] == [{"path": "", "code": codes.MALFORMED_JSON}]
    assert api.call("POST", url, json_body=api.routine(pid), content_type="application/json; charset=utf-8").status_code == 200


def test_commit_body_wrapper(api):
    pid = api.create()
    url = f"/api/v1/projects/{pid}/commands/commit"
    command = api.routine(pid, 0.6)
    for body, path, code in [
        ([], "", codes.WRONG_TYPE),
        ({}, "command", codes.MISSING_FIELD),
        ({"command": command, "preview_token": 7}, "preview_token", codes.WRONG_TYPE),
        ({"command": command, "extra": 1}, "extra", codes.UNKNOWN_FIELD),
        ({"command": command, "a b": 1}, '["a b"]', codes.UNKNOWN_FIELD),
    ]:
        error = _error(api.post(url, body), 422, "VALIDATION_FAILED")
        assert [(d["path"], d["code"]) for d in error["details"]] == [(path, code)]
    # Command paths stay relative to the envelope (interfaces.md §7.1).
    bad = api.command(pid, "SetFootprintDimensions", {"width_m": "36", "depth_m": 7})
    error = _error(api.post(url, {"command": bad}), 422, "VALIDATION_FAILED")
    assert error["details"][0] == {"path": "args.width_m", "code": codes.WRONG_TYPE, "value": "36"}
    assert api.get(f"/api/v1/projects/{pid}").json()["head_sequence"] == 1


def test_service_errors_map_to_statuses(api):
    pid = api.create()
    width = api.width(pid, 12.192)
    _error(api.commit(pid, width), 428, "PREVIEW_REQUIRED")
    _error(api.commit(pid, width, "not-a-token"), 409, "PREVIEW_INVALID")
    token = api.preview(pid, width).json()["preview_token"]
    other = api.width(pid, 12.5)
    _error(api.commit(pid, other, token), 409, "PREVIEW_INVALID")  # token for a different command
    api.clock.now = T0 + timedelta(minutes=16)
    _error(api.commit(pid, width, token), 409, "PREVIEW_EXPIRED")
    api.clock.now = T0
    stale = api.routine(pid, 0.6)
    assert api.commit(pid, api.routine(pid, 0.55)).status_code == 201
    _error(api.commit(pid, stale), 409, "REVISION_CONFLICT")
    _error(api.preview(pid, stale), 409, "REVISION_CONFLICT")
    reused = api.routine(pid, 0.6)
    assert api.commit(pid, reused).status_code == 201
    _error(api.commit(pid, reused | {"args": {**reused["args"], "nominal_label": "routine-0.7"}}), 409, "IDEMPOTENCY_CONFLICT")
    error = _error(api.preview(pid, api.width(pid, -1)), 422, "VALIDATION_FAILED")
    assert error["details"][0]["code"] == codes.OUT_OF_RANGE
    _error(api.get(f"/api/v1/projects/{pid}/revisions/{uuid.uuid4()}"), 404, "NOT_FOUND")
    _error(api.get(f"/api/v1/projects/{pid}/revisions/not-a-uuid"), 404, "NOT_FOUND")
    _error(api.get("/api/v1/projects/not-a-uuid"), 404, "NOT_FOUND")


def test_unknown_routes_and_methods(api):
    pid = api.create()
    response = api.client.get("/api/v1/nowhere", headers={"Authorization": "Bearer tok-a"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    response = api.client.delete(f"/api/v1/projects/{pid}", headers={"Authorization": "Bearer tok-a"})
    assert response.status_code == 405 and response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["allow"] == "GET"


def test_internal_errors_hide_details(api, monkeypatch, caplog):
    pid = api.create()

    def explode(*args, **kwargs):
        raise RuntimeError("secret project content")

    monkeypatch.setattr(api.service, "list_revisions", explode)
    with caplog.at_level(logging.ERROR, logger="homedesign.api"):
        response = api.get(f"/api/v1/projects/{pid}/revisions")
    error = _error(response, 500, "INTERNAL")
    assert error["details"] == [] and "secret" not in response.text and "Traceback" not in response.text
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert error["request_id"] in logged and "RuntimeError" in logged and "secret" not in logged


def test_corrupt_revision_is_500_internal():
    store = MemoryStore()
    api = make_api(store)
    pid = api.create()
    rev = api.head(pid)
    store.revisions[rev] = dataclasses.replace(store.revisions[rev], fingerprint="sha256:" + "0" * 64)
    error = _error(api.get(f"/api/v1/projects/{pid}/revisions/{rev}"), 500, "INTERNAL")
    assert rev not in error["message"]


# --- 4. artifact statuses (§4) -------------------------------------------------------------------


def _stub(kind, status="CURRENT", fail=False):
    def derive(ctx):
        if fail:
            raise ValueError("boom")
        return Outcome(status, {"kind": kind}, ({"code": "STUB", "message": "stub"},) if status == "UNAVAILABLE" else ())

    return Derivation(kind, f"{kind}-stub", "1", derive)


def test_artifact_statuses(store):
    reg = registry_of([_stub("plan2d"), _stub("mesh3d", "UNAVAILABLE"), _stub("timber_schedule", fail=True)])
    api = make_api(store, reg)
    pid = api.create()
    url = f"/api/v1/projects/{pid}/artifacts"
    current, unavailable, failed, missing = (api.get(f"{url}/{t}") for t in ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate"))
    assert (current.status_code, current.json()["status"], current.json()["payload"]) == (200, "CURRENT", {"kind": "plan2d"})
    assert (unavailable.status_code, unavailable.json()["status"], unavailable.json()["payload"]) == (200, "UNAVAILABLE", {"kind": "mesh3d"})
    assert (failed.status_code, failed.json()["status"], failed.json()["payload"]) == (200, "FAILED", None)
    assert failed.json()["error"]["code"] == "DERIVATION_FAILED"
    assert (missing.status_code, missing.json()["status"], missing.json()["payload"]) == (202, "MISSING", None)
    _error(api.get(f"{url}/elevation"), 404, "NOT_FOUND")
    _error(api.get(f"{url}/plan2d?revision_id={uuid.uuid4()}"), 404, "NOT_FOUND")
    _error(api.get(f"{url}?revision_id={uuid.uuid4()}"), 404, "NOT_FOUND")


def test_empty_registry_is_missing_202(store):
    api = make_api(store, Registry())
    pid = api.create()
    for kind in ("plan2d", "mesh3d", "timber_schedule", "preliminary_estimate"):
        response = api.get(f"/api/v1/projects/{pid}/artifacts/{kind}")
        assert (response.status_code, response.json()["status"]) == (202, "MISSING")


def test_old_revisions_are_served_with_head_false(api):
    pid = api.create()
    first = api.head(pid)
    api.commit(pid, api.routine(pid, 0.6))
    manifest = api.get(f"/api/v1/projects/{pid}/artifacts?revision_id={first}").json()
    plan = api.get(f"/api/v1/projects/{pid}/artifacts/plan2d?revision_id={first}").json()
    assert (manifest["revision_id"], manifest["head"], plan["source_revision_id"], plan["head"]) == (first, False, first, False)


# --- 5. price books -----------------------------------------------------------------------------


def test_price_book_put_get_and_estimate(api):
    pid = api.create()
    assert api.get(f"/api/v1/projects/{pid}/price-book").json() == {"price_book": None}
    response = api.put(f"/api/v1/projects/{pid}/price-book", book(**FULL_PRICES))
    assert response.status_code == 201 and response.json()["version"] == 1
    stored = api.get(f"/api/v1/projects/{pid}/price-book").json()["price_book"]
    assert (stored["version"], stored["set_by"], stored["book"]["source"]) == (1, ACTOR, "Supplier quote #123")
    manifest = {a["artifact_type"]: a["status"] for a in api.get(f"/api/v1/projects/{pid}/artifacts").json()["artifacts"]}
    assert manifest["preliminary_estimate"] == "STALE" and manifest["plan2d"] == "CURRENT"
    estimate = api.get(f"/api/v1/projects/{pid}/artifacts/preliminary_estimate").json()
    assert (estimate["status"], estimate["payload"]["coverage"]) == ("CURRENT", "complete")
    again = api.put(f"/api/v1/projects/{pid}/price-book", book(**FULL_PRICES))
    assert (again.json()["version"], again.json()["price_book_id"]) == (2, response.json()["price_book_id"])
    assert api.get(f"/api/v1/projects/{pid}").json()["head_sequence"] == 1  # not a model command


@pytest.mark.parametrize(
    "mutate, path, code",
    [
        (lambda b: b["rows"][0].__setitem__("unit_price_minor", -1), "rows[0].unit_price_minor", codes.OUT_OF_RANGE),
        (lambda b: b.__setitem__("discount", 5), "discount", codes.UNKNOWN_FIELD),
        (lambda b: b["rows"][0].__setitem__("unit", "each"), "rows[0].unit", codes.PRICE_UNIT_MISMATCH),  # ART-002 §7.3
    ],
)
def test_invalid_price_book_is_422(api, mutate, path, code):
    pid = api.create()
    candidate = book(**{POST_KEY: 3150})
    mutate(candidate)
    error = _error(api.put(f"/api/v1/projects/{pid}/price-book", candidate), 422, "VALIDATION_FAILED")
    assert (path, code) in {(d["path"], d["code"]) for d in error["details"]}
    assert api.get(f"/api/v1/projects/{pid}/price-book").json() == {"price_book": None}


# --- 6. request IDs -----------------------------------------------------------------------------


def test_request_ids_are_server_generated_and_unique(api):
    pid = api.create()
    spoofed = "11111111-1111-4111-8111-111111111111"
    ids = {api.get(f"/api/v1/projects/{pid}", headers={"X-Request-ID": spoofed}).headers["x-request-id"] for _ in range(5)}
    assert len(ids) == 5 and spoofed not in ids
    error = api.get(f"/api/v1/projects/{uuid.uuid4()}", headers={"X-Request-ID": spoofed})
    assert error.json()["error"]["request_id"] == error.headers["x-request-id"] != spoofed


# --- 7. startup and settings (§7) ---------------------------------------------------------------

KEY_HEX = "ab" * 32


@pytest.mark.parametrize(
    "env, message",
    [
        ({}, "HOMEDESIGN_PREVIEW_KEY is required"),
        ({"HOMEDESIGN_PREVIEW_KEY": "zz"}, "hex"),
        ({"HOMEDESIGN_PREVIEW_KEY": "ab" * 31}, "at least 32 bytes"),
        ({"HOMEDESIGN_PREVIEW_KEY": KEY_HEX}, "HOMEDESIGN_DATABASE_URL is required"),
        ({"HOMEDESIGN_PREVIEW_KEY": KEY_HEX, "HOMEDESIGN_STORE": "sqlite"}, "must be 'postgres' or 'memory'"),
        ({"HOMEDESIGN_PREVIEW_KEY": KEY_HEX, "HOMEDESIGN_STORE": "memory", "HOMEDESIGN_DEV_TOKENS": "abc"}, "token=<actor UUID>"),
        ({"HOMEDESIGN_PREVIEW_KEY": KEY_HEX, "HOMEDESIGN_STORE": "memory", "HOMEDESIGN_DEV_TOKENS": "abc=bob"}, "canonical actor UUID"),
    ],
)
def test_startup_refuses_invalid_settings(env, message, monkeypatch):
    for name in ("HOMEDESIGN_PREVIEW_KEY", "HOMEDESIGN_STORE", "HOMEDESIGN_DATABASE_URL", "HOMEDESIGN_DEV_TOKENS", "HOMEDESIGN_CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError, match=message):
        create_app()


def test_settings_from_env_and_secrets_not_in_repr(monkeypatch):
    env = {
        "HOMEDESIGN_PREVIEW_KEY": KEY_HEX, "HOMEDESIGN_STORE": "postgres", "HOMEDESIGN_DATABASE_URL": "postgresql://u:pw@h/db",
        "HOMEDESIGN_DEV_TOKENS": f"tok-a={ACTOR}, tok-b={ACTOR_B}", "HOMEDESIGN_CORS_ORIGINS": "http://localhost:5173, https://app.test",
    }
    settings = Settings.from_env(env)
    assert settings.preview_key == bytes.fromhex(KEY_HEX) and settings.dev_tokens == TOKENS
    assert settings.cors_origins == ("http://localhost:5173", "https://app.test")
    text = repr(settings)
    assert KEY_HEX not in text and "pw" not in text and "tok-a" not in text


def test_cors_allows_only_configured_origins():
    settings = Settings(preview_key=KEY, store="memory", dev_tokens=TOKENS, cors_origins=("http://localhost:5173",))
    client = TestClient(create_app(settings))
    allowed = client.options("/api/v1/projects", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
    assert allowed.status_code == 200 and allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.get("/api/v1/projects/x", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in denied.headers
    simple = client.get(f"/api/v1/projects/{uuid.uuid4()}", headers={"Origin": "http://localhost:5173", "Authorization": "Bearer tok-a"})
    assert "x-request-id" in simple.headers["access-control-expose-headers"].lower()


def test_openapi_and_docs_are_served_outside_api_v1():
    client = TestClient(create_app(Settings(preview_key=KEY, store="memory")))
    assert client.get("/openapi.json").json() == OPENAPI
    assert client.get("/docs").status_code == 200
    assert client.get("/api/v1/openapi.json").status_code == 404


def test_ui_fixtures_are_current():
    from homedesign.api.ui_fixtures import FIXTURE_PATH, render

    assert FIXTURE_PATH.read_text(encoding="utf-8") == render(), (
        "frontend/tests/fixtures/reference-house-001.json is stale. Run `uv run python -m homedesign.api.ui_fixtures` and commit the result."
    )
