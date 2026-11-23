"""TEST-002 §8, TEST-003 §8, D063, and D090: payload size and time budgets.

**Sizes:** each payload's RFC 8785 canonical bytes are at most 256 KiB for Reference House 001 v3 and at most
2,000,000 bytes for the largest cases, each with both wall assemblies (D090: the stud infill house is gated):
D063's largest frame (TIMBER-002 §5.3) and D090's named largest case for walls (`conftest.largest_wall_case`). The
named wall case is a named case, not a bound: openings have no bounds beyond the fit (D077). Canonical bytes do
not depend on the server's JSON settings or on compression, so the check has no tolerance. The largest frame's
bytes differ slightly between machines (TEST-003 §4); CI's are the gated ones.

**Times:** through the service, in-process, with the in-memory store, the median of 5 runs and no retries: a
reference-house width preview within 1 s and `SetOpening` preview within 1 s; on the named wall case, a width
preview, a `SetWallAssembly` preview, and a commit that derives all five artifacts, each within 5 s. The browser
ceilings are in `frontend/e2e/connections.spec.ts` (D063) and `frontend/e2e/walls.spec.ts` (D090).

The ceilings catch regressions; they are not targets to tune toward. If a CI measurement exceeds half its
ceiling, report it to the product owner rather than raising the ceiling (D063). Every check prints its
measurement, also without `-s`, and a failure names it.
"""

from __future__ import annotations

import statistics
import time
import uuid
from typing import Any, Callable

import pytest

from api_support import FULL_PRICES, book
from conftest import FIXTURE, STUD_INFILL, largest_doc, largest_wall_case, with_assembly
from homedesign.assemblies.schedule import build_assembly_schedule, select_assembly_schedule
from homedesign.estimating import build_estimate
from homedesign.geometry import build_mesh3d, build_plan2d, select_mesh3d, select_plan2d
from homedesign.model.canonical import snapshot_fingerprint
from homedesign.model.jcs import canonical_json
from homedesign.model.schema import Snapshot
from homedesign.project import MemoryStore, ProjectService
from homedesign.project.store import ProjectRow, RevisionRow
from homedesign.timber.schedule import build_schedule, select_schedule
from test_project import ACTOR, KEY, T0, at, create, envelope, head

REFERENCE_HOUSE_CEILING = 262_144  # 256 KiB
LARGEST_CASE_CEILING = 2_000_000


def _complete_book(schedule: dict[str, Any], assemblies: dict[str, Any]) -> dict[str, Any]:
    """A stored price-book row pricing every line, so the estimate carries every amount (its largest form)."""
    keys = [f"timber.{a['role']}.{a['nominal_section']}" for a in schedule["aggregates"]]
    keys += sorted({f"connection.{a['connection_type']}" for a in schedule["connection_aggregates"]})
    keys += [f"assembly.{a['assembly_label']}.{a['layer']}" for a in assemblies["layer_aggregates"]]
    keys += [f"wallframing.{a['piece_kind']}.{a['nominal_section']}" for a in assemblies["framing_aggregates"]]
    unit = lambda key: "each" if key.startswith("connection.") else "m2" if key.startswith("assembly.") else "m"  # noqa: E731
    rows = [{"key": key, "unit": unit(key), "unit_price_minor": 4500} for key in keys]
    book = {"currency": "USD", "as_of": "2026-11-01", "source": "Budget test quote", "geography": "Chittenden County, VT", "rows": rows}
    return {"price_book_id": "00000000-0000-4000-8000-0000000000b1", "version": 1, "book": book}


def payload_sizes(doc: dict[str, Any]) -> dict[str, int]:
    snapshot = Snapshot.model_validate(doc)
    schedule = build_schedule(select_schedule(snapshot))
    assemblies = build_assembly_schedule(select_assembly_schedule(snapshot))
    status, estimate, _ = build_estimate(schedule, assemblies, _complete_book(schedule, assemblies))
    assert status == "CURRENT" and estimate["coverage"] == "complete"
    payloads = {
        "plan2d": build_plan2d(select_plan2d(snapshot)),
        "mesh3d": build_mesh3d(select_mesh3d(snapshot)),
        "timber_schedule": schedule,
        "assembly_schedule": assemblies,
        "preliminary_estimate": estimate,
        "preliminary_estimate (no price book)": build_estimate(schedule, assemblies, None)[1],
    }
    return {kind: len(canonical_json(payload)) for kind, payload in payloads.items()}


SIZE_CASES = [
    ("Reference House 001 v3", lambda: FIXTURE, REFERENCE_HOUSE_CEILING),
    ("Reference House 001 v3, stud infill", lambda: STUD_INFILL, REFERENCE_HOUSE_CEILING),
    ("largest supported frame", largest_doc, LARGEST_CASE_CEILING),
    ("largest supported frame, stud infill", lambda: with_assembly(largest_doc()), LARGEST_CASE_CEILING),
    ("named largest wall case, stud infill", largest_wall_case, LARGEST_CASE_CEILING),
    ("named largest wall case, straw bale", lambda: largest_wall_case("straw-bale"), LARGEST_CASE_CEILING),
]


@pytest.mark.parametrize(
    "case,doc,ceiling", SIZE_CASES,
    ids=["reference-house", "reference-house-stud-infill", "largest-frame", "largest-frame-stud-infill", "wall-case", "wall-case-straw-bale"],
)
def test_payload_sizes_are_within_budget(case, doc, ceiling, capsys):
    sizes = payload_sizes(doc())
    _print_sizes(capsys, case, sizes, ceiling)
    over = {kind: size for kind, size in sizes.items() if size > ceiling}
    assert not over, f"{case}: payloads over the {ceiling:,}-byte budget (D063, D090): {over}"


def _print_sizes(capsys, case: str, sizes: dict[str, int], ceiling: int) -> None:
    with capsys.disabled():
        print()
        for kind, size in sizes.items():
            print(f"[budget] {case}: {kind} = {size:,} canonical bytes ({size / ceiling:.0%} of {ceiling:,})")


# --- time (§8.2) ------------------------------------------------------------------------------

RUNS = 5
FT = 0.3048


def _median_seconds(run: Callable[[int], Any]) -> tuple[float, list[float]]:
    times = []
    for i in range(RUNS):
        start = time.perf_counter()
        run(i)
        times.append(time.perf_counter() - start)
    return statistics.median(times), times


def _report(capsys, what: str, ceiling: float, median: float, times: list[float]) -> None:
    with capsys.disabled():
        runs = ", ".join(f"{t * 1000:.0f}" for t in times)
        print(f"\n[budget] {what}: median {median * 1000:.0f} ms of {RUNS} ({runs} ms), "
              f"{median / ceiling:.0%} of the {ceiling:g} s ceiling")
    assert median <= ceiling, f"{what}: median {median:.3f} s is over the {ceiling:g} s budget (TEST-002 §8.2, D063)"


def _width_edit(svc: ProjectService, pid: str) -> dict[str, Any]:
    """One foot narrower: every member, connection, wall, and piece is regenerated, and all five artifacts change."""
    footprint = next(e for e in head(svc, pid).entities if e.kind == "Footprint")
    return envelope(svc, pid, "SetFootprintDimensions", {"width_m": footprint.width_m - FT, "depth_m": footprint.depth_m})


def _seeded(svc: ProjectService, source: dict[str, Any]) -> str:
    """A project whose head is ``source`` (a large case), with a complete price book and its five artifacts
    derived, so a preview or commit starts from stored payloads as in use."""
    doc = Snapshot.model_validate(source).model_dump(mode="json")
    doc["project_id"], doc["revision_id"] = str(uuid.uuid4()), str(uuid.uuid4())
    snapshot = Snapshot.model_validate(doc)
    with svc.store.transaction() as tx:
        tx.insert_project(ProjectRow(doc["project_id"], doc["revision_id"], 1, T0, ACTOR))
        tx.insert_revision(RevisionRow(doc["revision_id"], doc["project_id"], None, 1, doc["model_schema_version"], snapshot.model_dump(mode="json"), snapshot_fingerprint(snapshot), T0))
    svc.set_price_book(doc["project_id"], book(**FULL_PRICES), actor_id=ACTOR, now=T0)
    statuses = svc.artifacts.derive_revision(doc["project_id"], doc["revision_id"], now=T0)
    assert set(statuses.values()) == {"CURRENT"}, statuses
    return doc["project_id"]


def test_reference_house_preview_time(capsys):
    svc = ProjectService(MemoryStore(), token_key=KEY)
    pid = create(svc).project_id
    command = _width_edit(svc, pid)
    assert len(svc.preview(pid, command, actor_id=ACTOR, now=at(1)).impacted_artifacts) == 5  # warm-up, not timed
    median, times = _median_seconds(lambda i: svc.preview(pid, command, actor_id=ACTOR, now=at(2 + i)))
    _report(capsys, "preview, Reference House 001 v3, width edit", 1.0, median, times)


def test_reference_house_set_opening_preview_time(capsys):
    """D090: the routine edit a homeowner makes most, one opening 1" wider, previewed on the reference house."""
    svc = ProjectService(MemoryStore(), token_key=KEY)
    pid = create(svc).project_id
    opening = sorted((e for e in head(svc, pid).entities if e.kind == "Opening"), key=lambda o: o.id)[0]
    args = {"opening_id": opening.id, "width_m": opening.width_m + 0.0254, "height_m": opening.height_m, "sill_height_m": opening.sill_height_m, "offset_m": opening.offset_m}
    command = envelope(svc, pid, "SetOpening", args)
    assert len(svc.preview(pid, command, actor_id=ACTOR, now=at(1)).impacted_artifacts) == 4  # warm-up, not timed
    median, times = _median_seconds(lambda i: svc.preview(pid, command, actor_id=ACTOR, now=at(2 + i)))
    _report(capsys, "preview, Reference House 001 v3, SetOpening", 1.0, median, times)


def test_largest_wall_case_preview_time(capsys):
    """D090: the named wall case replaces D063's largest frame for the time checks."""
    svc = ProjectService(MemoryStore(), token_key=KEY)
    pid = _seeded(svc, largest_wall_case())
    command = _width_edit(svc, pid)
    assert len(svc.preview(pid, command, actor_id=ACTOR, now=at(1)).impacted_artifacts) == 5  # warm-up, not timed
    median, times = _median_seconds(lambda i: svc.preview(pid, command, actor_id=ACTOR, now=at(2 + i)))
    _report(capsys, "preview, named largest wall case, width edit", 5.0, median, times)


def test_largest_wall_case_set_wall_assembly_preview_time(capsys):
    """D090: switching the named wall case to straw bale replaces every one of its stud infill pieces."""
    svc = ProjectService(MemoryStore(), token_key=KEY)
    pid = _seeded(svc, largest_wall_case())
    snapshot = head(svc, pid)
    straw_bale = next(e.id for e in snapshot.entities if e.kind == "AssemblyDefinition" and e.label == "straw-bale")
    command = envelope(svc, pid, "SetWallAssembly", {"assembly_definition_id": straw_bale})
    assert len(svc.preview(pid, command, actor_id=ACTOR, now=at(1)).impacted_artifacts) == 4  # warm-up, not timed
    median, times = _median_seconds(lambda i: svc.preview(pid, command, actor_id=ACTOR, now=at(2 + i)))
    _report(capsys, "preview, named largest wall case, SetWallAssembly to straw bale", 5.0, median, times)


def test_largest_wall_case_commit_time(capsys):
    """The commit and the derivation of all five artifacts for the new revision (dependencies.md §6), on the
    named wall case (D090)."""
    svc = ProjectService(MemoryStore(), token_key=KEY)
    doc = largest_wall_case()
    pids = [_seeded(svc, doc) for _ in range(RUNS)]  # a commit is not repeatable, so one project per run
    previewed = []
    for pid in pids:
        command = _width_edit(svc, pid)
        previewed.append((pid, command, svc.preview(pid, command, actor_id=ACTOR, now=at(1)).preview_token))

    def run(i: int) -> None:
        pid, command, token = previewed[i]
        result = svc.commit(pid, command, token, actor_id=ACTOR, now=at(2))
        assert result.http_status == 201 and set(result.artifact_statuses.values()) == {"CURRENT"}, result

    median, times = _median_seconds(run)
    _report(capsys, "commit with all five artifacts derived, named largest wall case, width edit", 5.0, median, times)
