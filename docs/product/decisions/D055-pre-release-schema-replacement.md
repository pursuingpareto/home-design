# D055 — Pre-release schema policy: replace, don't migrate

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** How schema and generation-rule changes are handled while the platform has no users. Chosen by the product owner during decision 5 of the [VS-02 scope proposal](../../implementation/acceptance-tests/vs-02.md) (§10), replacing that proposal's side-by-side approach.  
**Amends, while pre-release:** [interfaces.md §8](../../architecture/interfaces.md#8-concurrency-security-and-compatibility) ("schema changes require backward-compatible readers or explicit migrations").

## Decision

While the platform is **pre-release** (no users and no production data), a new model schema or generation rule **replaces** the previous one:

- **Newest only:** the backend supports only the newest `model_schema_version` and generation rule. With VS-02, that is version 2 and `vs02-frame-1`. `vs01-post-beam-1` and version 1 snapshots are retired.
- **Old snapshots are rejected:** a stored or submitted snapshot of an older version fails validation with `UNSUPPORTED_SCHEMA_VERSION`, which is already a stage-1 code. Nothing reads, converts, or upgrades it.
- **No upgrade mechanism:** there is no upgrade command, no data migration of stored snapshots, and no dual-version code paths.
- **Newest template:** `CreateReferenceProject` creates the newest template. With VS-02, that is Reference House 001 v2 ([D053](D053-reference-house-001-v2-design-intent.md)).
- **Local data is disposable:** development and test databases are recreated rather than migrated. The test suite already recreates its database on every run. Developers drop or recreate their local `homedesign` database after such a change; the change's release notes say so.
- **Visible regeneration:** fixtures, golden records, schemas, and test expectations are regenerated deliberately, as reviewed diffs (TEST-001 §6), never silently.

**This ends at the first release.** Once real users or production data exist, interfaces.md §8 applies in full again: backward-compatible readers or explicit migrations, with contract tests and fixture upgrades. Ending pre-release is a decision to record when it happens.

## Rationale

- There are no users and no data worth preserving.
- Dual-version readers, an upgrade command, and their tests would cost a large share of VS-02 for no benefit.
- Replacing keeps one code path, one fixture, and one set of expectations, which is simpler to reason about and to test.

## Consequences

- **VS-01 tests move to v2:** VS-01 acceptance tests keep their meaning, but run against the v2 reference house. Expected counts change, for example from 58 to 193 members.
- **Regeneration is reviewed:** the TEST-001 golden record, the UI fixtures, and the committed schemas are regenerated in VS-02, with reviewed diffs.
- **Superseded proposal:** decision 5 of the VS-02 proposal (side-by-side versions and `UpgradeFrameRule`) is not adopted.
