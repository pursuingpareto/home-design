# Next steps

1. Optional: make the CI workflow required for merges to `main` (a repository setting; CI already passes).
2. After merging MODEL-005 and TIMBER-002, recreate the local database once: `scripts/dev.sh --reset` (D055). The migration step refuses the old database until then.
3. Draft `CONN-001` (connection generation per junction class and `SetConnectionType`), the next VS-02 task ([vs-02.md](acceptance-tests/vs-02.md) §12.2).
4. Open spec items to schedule: hosting and identity (open question 8).

Unresolved questions that should not reopen D025–D058: exact CAD kernel, Vermont code editions, datasets, hosting, and drawing export formats.
