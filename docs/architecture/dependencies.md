# Dependency graph and change propagation — design specification

**Version:** 0.2 draft · **Status:** Behavior confirmed (Decision 018); graph implementation provisional.

## 1. Goal

When an authoritative parameter changes, identify exactly which derived outputs are no longer current, recompute what is supported, and prevent stale outputs or approvals from being presented as valid. All changes are transactional; expensive derivations may be asynchronous.

## 2. Graph model

A directed edge `A -> B` means **B depends on A**. Nodes represent semantic input fields or groups, derived entities, and artifacts. Graph node keys are stable logical identifiers, not transient UI objects.

Initial graph example:

```text
Footprint.width/depth -> TimberGrid.coordinates -> TimberMember.axes
Footprint.width/depth -> RoofGeometry
Level.elevation -> TimberMember.axes
FrameSystem.member_defaults -> TimberMember.section_id/material_id (D039, D040)
TimberMember.axes + Section -> timber_schedule
TimberMember.axes + Section -> mesh3d
TimberMember.axes -> plan2d
timber_schedule + optional project price book -> preliminary_estimate
ModelRevision + analysis inputs -> AnalysisResult (future)
AnalysisResult + reviewed inputs -> ProfessionalApproval (future)
```

Edges are registered by module-owned derivation rules with declared input selectors and output keys. **VS-02 ([D056](../product/decisions/D056-dependency-selectors.md)):** the selectors *are* the graph. Impact is computed by comparing each artifact's selector fingerprint between base and candidate, and no edge list is maintained separately. Derived artifact nodes must form an acyclic graph in VS-01. If future iterative solvers require cycles, encapsulate them as a single solver node with explicit convergence criteria; do not allow unbounded recursive propagation.

## 3. Artifact status machine

`MISSING -> QUEUED -> COMPUTING -> CURRENT` or `FAILED`; a newer relevant input revision transitions `CURRENT|QUEUED|COMPUTING|FAILED -> STALE` (or superseded). Status is accompanied by `source_revision_id`, `generator_version`, `input_fingerprint`, `generated_at`, and error details if failed. A result is **CURRENT** only if its input fingerprint matches the latest applicable inputs; a matching revision ID alone is insufficient for independently versioned external datasets.

UI must visibly label `STALE`, `COMPUTING`, `FAILED`, or `UNAVAILABLE`; it may show old results for comparison but must never label them current. Unknown cost inputs produce `UNAVAILABLE`, not zero.

## 4. Change classification and confirmation

- **Routine:** e.g. adjusting a nonstructural display property, or a supported footprint dimension within validated limits when no protected review is affected. Can auto-commit and queue recomputation.
- **Consequential:** e.g. moving structural posts, altering load-path assumptions, changing reviewed members, deleting connected objects, or edits with potentially significant budget implications. Requires an impact preview and confirmation.
- Classification is rule-based, versioned, conservative, and server-enforced; future AI may suggest classification but cannot override it.
- For VS-01, any footprint/roof/grid change that regenerates framing is treated as **consequential** by default, until a more nuanced policy is approved.

### 4.1 Classification table (`vs02-change-classes-1`)

Approved from [MODEL-003](../implementation/tasks/MODEL-003.md) §10, item 7, as `vs01-change-classes-1`, and replaced in VS-02 by `vs02-change-classes-1` ([D057](../product/decisions/D057-vs02-frame-command-roof-classification.md), MODEL-005 §7.3). The server applies this table; clients cannot override it.

| Command | Class | Reason |
|---|---|---|
| `AddSection` | routine | Adds a catalog record; no member changes |
| `SetGableRoofParameters` | consequential | Regenerates principal rafters and purlins, which follow the pitch (D057; routine in `vs01-change-classes-1`, when no member used the roof) |
| `SetFrameParameters` | consequential | Regenerates framing; may retire and create members |
| `SetFootprintDimensions` | consequential | Regenerates framing |
| `SetStoryHeights` | consequential | Regenerates framing |
| `SetTimberGrid` | consequential | Regenerates framing; may retire and create members |
| `SetMemberSection` | consequential | Changes every member of a role ([D040](../product/decisions/D040-setmembersection-role-default.md)) |
| `UndoToRevision` | consequential | Can change anything ([D044](../product/decisions/D044-undo-to-revision.md)) |
| `CreateReferenceProject` | consequential | Creates the whole model |

*VS-02 amendment ([D059](../product/decisions/D059-vs02-junction-rules-connection-type-command.md), approved; not yet implemented):* `SetConnectionType` is **consequential**, because it changes every connection of a junction class and has per-piece budget implications. [CONN-001](../implementation/tasks/CONN-001.md) adds the row to this table, within version `vs02-change-classes-1` as D057 anticipated, when it implements the command.

- **Routine** commands may be committed without a preview, and the commit still validates fully. **Consequential** commands require a preview and a confirmation bound to it (§5).
- A no-op never requires confirmation ([D045](../product/decisions/D045-no-op-commits.md)).
- Every preview and commit result records the table version. Changing the table, for example once professional approvals exist and must make some routine edits consequential, means publishing a new version and updating this section.

## 5. Change protocol

1. Receive typed command with idempotency key, actor, `base_revision_id`, and arguments.
2. Authenticate and authorize; validate syntax and base revision.
3. Compute proposed semantic diff in an isolated candidate snapshot.
4. Validate candidate model and determine changed input keys.
5. Traverse reverse dependency index to build impacted-node closure, with deterministic ordering.
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

Use a topological order of affected derivations. Cache by `(derivation_type, generator_version, input_fingerprint)`. In VS-01 the fingerprint includes the revision, so the cache never hits across revisions. It only prevents re-deriving the same revision ([artifacts.md §2.3](artifacts.md#23-fingerprint)). From VS-02 ([D056](../product/decisions/D056-dependency-selectors.md)), fingerprints exclude the revision, so unchanged artifacts are reused across revisions. Jobs are at-least-once, idempotent, and safe to retry. Workers must not overwrite a newer result with an older computation. Failure in a noncritical derived artifact must not corrupt the committed semantic model. Propagate failure or unknown statuses to dependent artifacts rather than fabricating fallback numbers.

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

## 9. Observability

Record operation ID, project ID, base/new revision, impacted-node count, derivation duration, generator version, cache hit/miss, and failure code. Exclude private project content from routine logs.

## 10. Open issues

Graph storage (in-memory rebuild versus persisted edge index), fine-grained field selectors, preview threshold rules, and job-queue selection are provisional. Benchmark with the reference house before optimizing.
