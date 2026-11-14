# Dependency and change propagation

**Status:** Behavior confirmed; algorithms and data structures provisional.

A dependency graph connects semantic elements to derived geometry, schedules, analyses, estimates, documents, and approvals. Routine edits may propagate automatically; consequential edits require impact preview and confirmation.

## Invariants

- Validate all operations against the current base revision and permissions.
- Commit model changes atomically or return structured errors.
- Explicitly invalidate dependent artifacts before showing refreshed results.
- Tag every derived artifact with the model revision used to produce it.
- Reevaluate only approvals whose relevant inputs or dependency scopes changed.
- Never present stale calculations or documents as current.

## VS-01 test

Changing the footprint width updates generated timber geometry and both views, invalidates the old member schedule, and produces a reconciled new schedule.

See [VS-01 acceptance tests](../implementation/acceptance-tests/vs-01.md).
