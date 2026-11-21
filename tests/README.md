# Shared test vectors

Language-neutral test data used by every implementation. Unit tests for each language live with that code (for example, `backend/tests/`).

## `vectors/jcs/` — RFC 8785 canonical JSON (D029)

- `inputs/*.json` — raw JSON documents. Files are kept byte-exact so that literal spellings (`1.0`, `-0`, `4.50`, `\u` escapes) are preserved.
- `vectors.json` — expected canonical bytes and `sha256:` fingerprints for each input, RFC 8785 Appendix B number samples, the canonical fingerprint of Reference House 001 (`entities` sorted by `id`, D030), and the canonical `vs01-post-beam-1` inventory for its parameters, computed by an independent ECMAScript implementation of the rule (TIMBER-001), D041 UUIDv5 ID-minting cases computed by an independent ECMAScript UUIDv5 (MODEL-003), and the `plan2d` fingerprint and full `mesh3d` payload for Reference House 001 from an independent ECMAScript implementation of the views (GEOM-001; version 2 payloads with every role and the connection markers, ART-002), and the `timber_schedule` fingerprint, aggregates, and connection aggregates (EST-001, ART-002).
- `generate.mjs` — regenerates `vectors.json` using an ECMAScript engine, the reference that RFC 8785 is defined against. Do not edit `vectors.json` by hand.

```bash
node tests/vectors/jcs/generate.mjs   # from the repository root; Node is needed only to regenerate
```

A change to the Reference House 001 fingerprint means the fixture or the canonicalization changed, and requires a decision.

## `vectors/scenarios/` — the golden scenario record (TEST-001 §6)

- `reference-house-001.json` — fingerprints per revision, and each step's status, error code, and `impacted_artifacts`, for the Reference House 001 scenario in `backend/tests/integration/scenario.py`: every command over HTTP, rejections, a retry, a conflict, undo, and a replay. Since TEST-002 §6 it includes a joist spacing that keeps the joist count (plan and mesh only), eave braces off, `joist-beam` to Joist hanger (an unpriced line, no total), and a rejection of each new command: 18 steps and 12 revisions.
- Regenerate with `uv run python tests/integration/golden.py` from `backend/`, and review the diff (D055). Do not edit it by hand.
