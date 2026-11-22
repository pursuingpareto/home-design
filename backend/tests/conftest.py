from __future__ import annotations

import copy
import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings as hypothesis_settings

# TEST-001 §7: deterministic by default (no flakes in CI); `HYPOTHESIS_PROFILE=thorough` for long runs.
# Tests that set max_examples explicitly keep their own counts. No per-example deadline: wall-clock time
# under load is not a property of the code, and a first call can take several times longer than a second,
# which Hypothesis reports as a flaky DeadlineExceeded (TEST-002, seen in test_robustness.py).
hypothesis_settings.register_profile("ci", derandomize=True, max_examples=40, print_blob=True, deadline=None)
hypothesis_settings.register_profile("thorough", derandomize=False, max_examples=500, print_blob=True, deadline=None)
hypothesis_settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

from homedesign.model.limits import RECORD_SCHEMA_VERSIONS
from homedesign.model.schema import Snapshot
from homedesign.timber import get_rule

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "docs" / "reference-projects" / "vermont-timber-house" / "fixture.snapshot.json"
VECTORS_PATH = REPO_ROOT / "tests" / "vectors" / "jcs" / "vectors.json"
SCHEMA_PATH = REPO_ROOT / "docs" / "architecture" / "schemas" / "snapshot.v3.schema.json"
BUILDING_MODEL_DOC = REPO_ROOT / "docs" / "architecture" / "building-model.md"

FIXTURE_BYTES = FIXTURE_PATH.read_bytes()
FIXTURE: dict[str, Any] = json.loads(FIXTURE_BYTES)


def fresh_fixture() -> dict[str, Any]:
    return copy.deepcopy(FIXTURE)


def entities_of(doc: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [e for e in doc["entities"] if e["kind"] == kind]


def index_of(doc: dict[str, Any], entity_id: str) -> int:
    return next(i for i, e in enumerate(doc["entities"]) if e["id"] == entity_id)


def epath(entity: dict[str, Any], *rest: str | int) -> str:
    """D036 path for a fixture entity addressed by its (usable) ID."""
    text = f"entities[{entity['id']}]"
    for step in rest:
        text += f"[{step}]" if isinstance(step, int) else f".{step}"
    return text


@pytest.fixture
def doc() -> dict[str, Any]:
    return fresh_fixture()


_TEST_ID_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-0000000000aa")


# --- MODEL-004 stores (MODEL-004 §7) ----------------------------------------------

PG_URL = os.environ.get("HOMEDESIGN_TEST_DATABASE_URL", "postgresql:///homedesign_test")


@pytest.fixture(scope="session")
def pg_url() -> str:
    """Recreate the name-guarded test database on the local server and apply migrations.

    Only a database whose name starts with ``homedesign_test`` is ever dropped or created.
    An unreachable server fails the tests instead of skipping them.
    """
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    from homedesign.project.migrate import migrate

    dbname = conninfo_to_dict(PG_URL).get("dbname") or ""
    if not dbname.startswith("homedesign_test"):
        pytest.fail(f"Refusing to use database {dbname!r}: test database names must start with 'homedesign_test'.")
    try:
        with psycopg.connect(make_conninfo(PG_URL, dbname="postgres"), autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(dbname)))
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
    except psycopg.OperationalError as exc:
        pytest.fail(f"PostgreSQL is not reachable for {PG_URL!r} (set HOMEDESIGN_TEST_DATABASE_URL): {exc}")
    migrate(PG_URL)
    return PG_URL


@pytest.fixture(params=["memory", "postgres"])
def store(request):
    from homedesign.project import MemoryStore
    from homedesign.project.postgres import PostgresStore

    if request.param == "memory":
        return MemoryStore()
    return PostgresStore(request.getfixturevalue("pg_url"))


GENERATED_KINDS = ("TimberMember", "Connection", "Wall", "WallFramingPiece")


def regenerate(doc: dict[str, Any]) -> dict[str, Any]:
    """Test helper: replace members, connections, walls, and wall framing with the rules' output.

    Keeps a record's ID when its key survives and gives new keys a test-only UUIDv5. Openings
    whose wall is retired are removed, as the pipeline does (MODEL-006 §8.5).
    (Production ID assignment is MODEL-003's job, D041; CONN-001 §5.2.)
    """
    from homedesign.assemblies import get_wall_rule

    snapshot = Snapshot.model_validate(doc)
    grid = next(e for e in snapshot.entities if e.kind == "TimberGrid")
    system = next(e for e in snapshot.entities if e.kind == "WallSystem")
    rule = get_rule(grid.generation_rule_version)
    wall_rule = get_wall_rule(system.generation_rule_version)
    existing = {e["generation_key"]: e["id"] for e in doc["entities"] if e["kind"] in GENERATED_KINDS}

    def record_id(key: str) -> str:
        return existing.get(key) or str(uuid.uuid5(_TEST_ID_NAMESPACE, key))

    def record(kind: str, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        return {"id": record_id(key), "kind": kind, "schema_version": RECORD_SCHEMA_VERSIONS[kind], **fields}

    members = [record("TimberMember", m.generation_key, m.to_json()) for m in rule.generate(snapshot)]
    member_ids = {m["generation_key"]: m["id"] for m in members}
    connections = [record("Connection", c.generation_key, c.to_json([member_ids[k] for k in c.member_keys])) for c in rule.generate_connections(snapshot)]
    inventory = wall_rule.build(snapshot)
    pieces = [record("WallFramingPiece", p.generation_key, p.to_json()) for p in inventory.framing]
    walls = [
        record("Wall", w.generation_key, w.to_json([piece["id"] for p, piece in zip(inventory.framing, pieces) if p.wall_key == w.generation_key]))
        for w in inventory.walls
    ]
    wall_ids = {w["id"] for w in walls}
    retired = {e["id"] for e in doc["entities"] if e["kind"] == "Opening" and e["wall_id"] not in wall_ids}
    doc["entities"] = [e for e in doc["entities"] if e["kind"] not in GENERATED_KINDS and e["id"] not in retired] + members + connections + walls + pieces
    frame = next(e for e in doc["entities"] if e["kind"] == "FrameSystem")
    frame["member_ids"] = [m["id"] for m in members]
    frame["connection_ids"] = [c["id"] for c in connections]
    wall_system = next(e for e in doc["entities"] if e["kind"] == "WallSystem")
    wall_system["wall_ids"] = [w["id"] for w in walls]
    wall_system["opening_ids"] = [i for i in wall_system["opening_ids"] if i not in retired]
    return doc


def remove_openings(doc: dict[str, Any]) -> dict[str, Any]:
    """The doc with no openings and no opening framing (for frame-only tests whose edits no D072
    window would fit). Layout studs and girts are left as they are: regenerate for conformance."""
    gone = {e["id"] for e in doc["entities"] if e["kind"] == "Opening" or (e["kind"] == "WallFramingPiece" and e["opening_id"] is not None)}
    doc["entities"] = [e for e in doc["entities"] if e["id"] not in gone]
    for wall in (e for e in doc["entities"] if e["kind"] == "Wall"):
        wall["framing_ids"] = [i for i in wall["framing_ids"] if i not in gone]
    next(e for e in doc["entities"] if e["kind"] == "WallSystem")["opening_ids"] = []
    return doc


# --- frames built from the fixture (shared by test_timber, test_connections, test_budgets) ------

FT = 0.3048


def with_frame_parameters(doc: dict[str, Any] | None = None, **parameters: Any) -> dict[str, Any]:
    """The doc (by default the fixture) with these frame parameters, regenerated."""
    doc = doc or fresh_fixture()
    entities_of(doc, "FrameSystem")[0]["parameters"].update(parameters)
    return regenerate(doc)


def grid_doc(nx: int, ny: int, bay_ft: float = 12) -> dict[str, Any]:
    """The fixture on an nx × ny station grid of equal bays, regenerated."""
    doc = fresh_fixture()
    footprint = entities_of(doc, "Footprint")[0]
    footprint["width_m"] = (nx - 1) * bay_ft * FT
    footprint["depth_m"] = (ny - 1) * bay_ft * FT
    grid = entities_of(doc, "TimberGrid")[0]
    grid["x_lines"] = [{"id": f"x{i}", "fraction": i / (nx - 1)} for i in range(nx)]
    grid["y_lines"] = [{"id": f"y{j}", "fraction": j / (ny - 1)} for j in range(ny)]
    return regenerate(doc)


def largest_doc() -> dict[str, Any]:
    """TIMBER-002 §5.3: 7 × 7 stations over 80' × 80', 12" joists, 4 purlins, both brace planes
    (1,216 members, 2,110 connections)."""
    return with_frame_parameters(grid_doc(7, 7, bay_ft=80 / 6), joist_spacing_m=0.3048, purlins_per_slope=4)
