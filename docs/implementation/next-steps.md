# Next steps

1. Draft and implement `MODEL-004`: revision persistence (PostgreSQL JSONB snapshots plus the append-only operation log, D026), project head and optimistic concurrency, the idempotency store, preview tokens and expiry, and no-op logging (D045). It wraps `MODEL-003`'s `propose`.
2. Then the artifact derivations (`GEOM-001` plan and mesh, `EST-001` schedule and estimate) and the API task.
3. Open spec items to schedule: hosting and identity (open question 8), C5 (per-artifact fingerprint inputs), and C1 (the `mesh3d` roof-slope example).

Unresolved questions that should not reopen D025–D046: exact CAD kernel, Vermont code editions, datasets, hosting, and drawing export formats.
