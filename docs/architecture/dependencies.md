# Dependency graph and change propagation — design specification

**Version:** 0.3 draft · **Status:** Behavior confirmed (Decision 018); selectors and computed impact implemented in VS-02 (D056, D061, DEP-001).

## 1. Goal

When an authoritative parameter changes, identify exactly which derived outputs are no longer current, recompute what is supported, and prevent stale outputs or approvals from being presented as valid. All changes are transactional; expensive derivations may be asynchronous.

## 2. Graph model

A directed edge `A -> B` means **B depends on A**. Nodes represent semantic input fields or groups, derived entities, and artifacts. Graph node keys are stable logical identifiers, not transient UI objects.

**VS-02: the selectors are the graph** ([D056](../product/decisions/D056-dependency-selectors.md), [D061](../product/decisions/D061-vs02-selector-contents.md)). Each derivation declares a pure selector that extracts exactly what its builder reads, and its builder reads nothing else. The edges are therefore implicit in the selections ([artifacts.md §2.5](artifacts.md#25-selections-vs-02)):

```text
footprint, levels, overhang, member plan positions, connection plan positions -> plan2d
footprint, levels, roof, member axes and section dimensions, connection locations -> mesh3d
member lengths, sections, and materials, connection members -> timber_schedule
timber_schedule (aggregates, connection aggregates, assumptions) + optional project price book -> preliminary_estimate
wall plan positions and extents, opening gaps, wall framing plan positions -> plan2d (VS-02b)
wall geometry and layers, openings, wall framing axes and section dimensions -> mesh3d (VS-02b)
wall lengths, heights, and framing face areas, openings, wall framing lengths and sections, definitions in use -> assembly_schedule (VS-02b)
assembly_schedule (layer aggregates, framing aggregates, assumptions) -> preliminary_estimate (VS-02b)
ModelRevision + analysis inputs -> AnalysisResult (future)
AnalysisResult + reviewed inputs -> ProfessionalApproval (future)
```

The grid, story heights, roof pitch, and frame parameters reach the first three only through the generated members and connections (D039, D040, D042).

Edges are registered by module-owned derivation rules with declared input selectors. Impact is computed by comparing each artifact's selection fingerprint between base and candidate, and no edge list is maintained separately. Derived artifact nodes must form an acyclic graph in VS-01. If future iterative solvers require cycles, encapsulate them as a single solver node with explicit convergence criteria; do not allow unbounded recursive propagation.

## 3. Artifact status machine

`MISSING -> QUEUED -> COMPUTING -> CURRENT` or `FAILED`; a newer relevant input revision transitions `CURRENT|QUEUED|COMPUTING|FAILED -> STALE` (or superseded). Status is accompanied by `source_revision_id`, `generator_version`, `input_fingerprint`, `generated_at`, and error details if failed. A result is **CURRENT** only if its input fingerprint matches the latest applicable inputs; a matching revision ID alone is insufficient for independently versioned external datasets.

UI must visibly label `STALE`, `COMPUTING`, `FAILED`, or `UNAVAILABLE`; it may show old results for comparison but must never label them current. Unknown cost inputs produce `UNAVAILABLE`, not zero.

## 4. Change classification and confirmation

- **Routine:** e.g. adjusting a nonstructural display property, or a supported footprint dimension within validated limits when no protected review is affected. Can auto-commit and queue recomputation.
- **Consequential:** e.g. moving structural posts, altering load-path assumptions, changing reviewed members, deleting connected objects, or edits with potentially significant budget implications. Requires an impact preview and confirmation.
- Classification is rule-based, versioned, conservative, and server-enforced; future AI may suggest classification but cannot override it.
- For VS-01, any footprint/roof/grid change that regenerates framing is treated as **consequential** by default, until a more nuanced policy is approved.

### 4.1 Classification table (`vs02b-change-classes-1`)

Approved from [MODEL-003](../implementation/tasks/MODEL-003.md) §10, item 7, as `vs01-change-classes-1`, replaced in VS-02 by `vs02-change-classes-1` ([D057](../product/decisions/D057-vs02-frame-command-roof-classification.md), MODEL-005 §7.3), and in VS-02b by `vs02b-change-classes-1` ([MODEL-006](../implementation/tasks/MODEL-006.md) §8.4, approved as §13 item 11). The server applies this table; clients cannot override it.

| Command | Class | Reason |
|---|---|---|
| `AddSection` | routine | Adds a catalog record; no member changes |
| `AddOpening` | routine | Regenerates only its own wall's framing; no member, connection, or other wall changes ([D069](../product/decisions/D069-vs02b-openings.md)) |
| `SetOpening` | routine | As `AddOpening` (D069) |
| `RemoveOpening` | routine | As `AddOpening` (D069) |
| `SetWallAssembly` | consequential | Changes every wall and its framing, and the estimate, at once ([D068](../product/decisions/D068-vs02b-wall-assembly-choice.md)) |
| `SetGableRoofParameters` | consequential | Regenerates principal rafters and purlins, which follow the pitch (D057; routine in `vs01-change-classes-1`, when no member used the roof) |
| `SetFrameParameters` | consequential | Regenerates framing; may retire and create members |
| `SetFootprintDimensions` | consequential | Regenerates framing |
| `SetStoryHeights` | consequential | Regenerates framing |
| `SetTimberGrid` | consequential | Regenerates framing; may retire and create members |
| `SetMemberSection` | consequential | Changes every member of a role ([D040](../product/decisions/D040-setmembersection-role-default.md)) |
| `SetConnectionType` | consequential | Changes every connection of a junction class, with per-piece budget implications ([D059](../product/decisions/D059-vs02-junction-rules-connection-type-command.md)) |
| `UndoToRevision` | consequential | Can change anything ([D044](../product/decisions/D044-undo-to-revision.md)) |
| `CreateReferenceProject` | consequential | Creates the whole model |

`SetConnectionType` was added in VS-02 ([D059](../product/decisions/D059-vs02-junction-rules-connection-type-command.md), [CONN-001](../implementation/tasks/CONN-001.md)) within version `vs02-change-classes-1`, as D057 anticipated.

VS-02b's `vs02b-change-classes-1` keeps every row of `vs02-change-classes-1` and adds the four wall commands. Since `ART-003` (2026-11-22) the three opening commands and `SetWallAssembly` impact exactly the artifacts whose payloads they change (before it, with no payload reading walls, they impacted none, MODEL-006 §10); no wall edit impacts `timber_schedule`.

- **Routine** commands may be committed without a preview, and the commit still validates fully. **Consequential** commands require a preview and a confirmation bound to it (§5).
- A no-op never requires confirmation ([D045](../product/decisions/D045-no-op-commits.md)).
- Every preview and commit result records the table version. Changing the table, for example once professional approvals exist and must make some routine edits consequential, means publishing a new version and updating this section.

## 5. Change protocol

1. Receive typed command with idempotency key, actor, `base_revision_id`, and arguments.
2. Authenticate and authorize; validate syntax and base revision.
3. Compute proposed semantic diff in an isolated candidate snapshot.
4. Validate candidate model, and compute every artifact's selection and input fingerprint for the base and for the candidate, under the project's current external inputs ([DEP-001](../implementation/tasks/DEP-001.md) §6).
5. The impacted artifacts are exactly those whose fingerprints differ, in code-unit order. A dependent whose dependencies' fingerprints are all equal has equal selections and is not impacted; otherwise its dependencies' outcomes are read from a stored row with the same fingerprint, or derived without being stored.
6. Return preview: semantic diff, added/removed/updated member IDs, impacted artifacts, required confirmation, and unknown impacts.
7. On confirmation, revalidate base revision and authorization (time-of-check/time-of-use protection).
8. Atomically persist new immutable revision, operation record, and artifact invalidation records/outbox messages.
9. Recompute synchronous lightweight derivations; queue expensive jobs with deduplication.
10. Publish status updates and results only when their fingerprints still match current inputs; otherwise mark superseded.

Preview is non-mutating. Confirmation must bind to a specific preview token, base revision, and operation hash; if anything changes, return a conflict requiring a fresh preview. The token is stateless and signed: it covers project, actor, base revision, `command_hash`, and a 15-minute expiry ([D047](../product/decisions/D047-stateless-preview-tokens.md)). Commits check, in order: idempotency, base revision (`REVISION_CONFLICT`), command validation, then the preview (`PREVIEW_REQUIRED`, `PREVIEW_INVALID`, `PREVIEW_EXPIRED`).

## 6. Incremental recomputation

**VS-01 execution model** ([ART-001](../implementation/tasks/ART-001.md) §4, approved as §8 item 1):

- **After commit:** once the commit transaction has committed, the service derives every artifact for the new revision synchronously, in dependency order, storing each result in its own transaction.
- **Failures:** a derivation that raises is stored as `FAILED` and never affects the committed revision.
- **Lazy recompute:** reading an artifact whose stored result is missing or has a different fingerprint (after a crash, a generator version change, or a price-book change) derives it on demand.
- **No workers or outbox in VS-01:** steps 8–9 of §5 reduce to "persist the revision, then derive". `QUEUED`, `COMPUTING`, and `SUPERSEDED` remain in the contract for a later asynchronous worker, but VS-01 never produces them.

Use a topological order of affected derivations. Cache by `(derivation_type, generator_version, input_fingerprint)`, **within one project** ([DEP-001](../implementation/tasks/DEP-001.md) §7):

- **After commit**, for each artifact of the new revision in dependency order: compute its fingerprint (the estimate's from the schedule outcome just stored for this revision); if a `CURRENT` or `UNAVAILABLE` row of any revision of the same project has that type, fingerprint, and generator version, copy it for the new revision, keeping its payload, warnings, and `generated_at`; otherwise derive. So the reused artifacts are exactly those the preview did not list, and `UndoToRevision` reuses every payload of its target.
- **On read**, lazy recompute uses the same lookup before deriving.
- **`FAILED` rows are never copied:** the artifact is derived again.
- **Rows are copied, not shared:** every revision keeps its own row, and deleting one revision's rows affects no other.
- **Never across projects:** payloads carry IDs minted per project, and the lookup stays inside the project's access boundary (D050). The lookup is indexed on `(project_id, artifact_type, input_fingerprint)`.
- When several rows match, the earliest by `generated_at`, then revision, is copied. They have equal payloads.

In VS-01 the fingerprint included the revision, so the cache never hit across revisions. Jobs are at-least-once, idempotent, and safe to retry. Workers must not overwrite a newer result with an older computation. Failure in a noncritical derived artifact must not corrupt the committed semantic model. Propagate failure or unknown statuses to dependent artifacts rather than fabricating fallback numbers.

## 7. Professional review dependency scope (future)

An approval records the reviewed revision, signer identity/authorization, review scope, applicable analysis version, and dependency fingerprints. A change to any scoped input marks that approval `REVIEW_REQUIRED` (not automatically revoked or re-approved). Unrelated changes leave its recorded status intact. This workflow does not constitute legal certification by itself.

## 8. VS-01 examples and tests

| Event | Required behavior |
|---|---|
| Change footprint width 12m -> 13m | New revision; grid and affected timber axes regenerate; plan/mesh/schedule become stale until regenerated |
| Change display color only | No semantic geometry recomputation |
| Change footprint to negative width | Validation error; no revision or invalidation |
| Submit same command twice | Same committed outcome/idempotent response; no duplicate revision |
| Confirm old preview after another edit | `REVISION_CONFLICT`; no commit |
| Old worker finishes after new worker | Old result remains superseded; UI shows only new current result |
| Remove grid bay | Retire removed generated member keys, preserve surviving member IDs, regenerate inventory (stable line IDs make this hold for interior bays, [D042](../product/decisions/D042-stable-grid-line-ids.md)) |
| Missing unit prices | Estimate `UNAVAILABLE` or partial with clear coverage; never $0 total by default ([artifacts.md](artifacts.md) §8) |

VS-02 examples ([DEP-001](../implementation/tasks/DEP-001.md) §8, measured on Reference House 001 v2; listed here rather than as table rows, because the VS-01 traceability matrix counts the rows above; traced as `DEP2-1` to `DEP2-4` in [vs-02-traceability.md](../implementation/acceptance-tests/vs-02-traceability.md)):

- **`AddSection`:** new revision; nothing is impacted, and all four artifacts are reused for it, payloads and fingerprints unchanged.
- **A pitch-only roof edit:** `mesh3d`, `timber_schedule`, and `preliminary_estimate` are impacted; `plan2d` is reused, because rafters and purlins move only in `z`.
- **An overhang-only roof edit:** `plan2d` and `mesh3d` only; no member moves.
- **A price-book change:** no revision; only the head's estimate reads `STALE` and is recomputed on read.

VS-02b examples ([ART-003](../implementation/tasks/ART-003.md) §8.3, measured on Reference House 001 v3 with straw bale; `tests/test_impact.py` checks both families). An opening added, removed, or narrowed impacts `plan2d`, `mesh3d`, `assembly_schedule`, and `preliminary_estimate`. Moving an opening along its wall impacts the two views and `assembly_schedule`, and changing only its sill height `mesh3d` and `assembly_schedule`: the schedule has no positions and the quantities are unchanged in exact arithmetic, but piece lengths and face areas are evaluated from the moved positions as written and change in their last bit. The estimate's sums are unchanged there, so it is reused, unless a stud infill piece really changes length. `SetWallAssembly` impacts every artifact but `timber_schedule`. A frame edit that moves no wall piece (on the straw bale house, the brace leg, the eave braces, or a connection type) impacts every artifact but `assembly_schedule`. No wall edit impacts `timber_schedule`.

## 9. Observability

Record operation ID, project ID, base/new revision, impacted-node count, derivation duration, generator version, cache hit/miss, and failure code. Exclude private project content from routine logs. Since DEP-001, every artifact stored after a commit or on read is logged (`homedesign.dependencies`) as a cache hit (a reused row) or a miss, with project, revision, type, and generator version; a miss also records the derivation's duration, status, and failure code.

## 10. Open issues

Preview threshold rules and job-queue selection are provisional. Settled: no graph storage is needed, because the selectors are the graph, and field-level selectors are exact projections of what each builder reads (D056, D061). Benchmark with the reference house before optimizing.
