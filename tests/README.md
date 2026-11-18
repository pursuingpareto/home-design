# Shared test vectors

Language-neutral test data used by every implementation. Unit tests for each language live with that code (for example, `backend/tests/`).

## `vectors/jcs/` — RFC 8785 canonical JSON (D029)

- `inputs/*.json` — raw JSON documents. Files are kept byte-exact so that literal spellings (`1.0`, `-0`, `4.50`, `\u` escapes) are preserved.
- `vectors.json` — expected canonical bytes and `sha256:` fingerprints for each input, RFC 8785 Appendix B number samples, the canonical fingerprint of Reference House 001 (`entities` sorted by `id`, D030), and the canonical `vs01-post-beam-1` inventory for its parameters, computed by an independent ECMAScript implementation of the rule (TIMBER-001).
- `generate.mjs` — regenerates `vectors.json` using an ECMAScript engine, the reference that RFC 8785 is defined against. Do not edit `vectors.json` by hand.

```bash
node tests/vectors/jcs/generate.mjs   # from the repository root; Node is needed only to regenerate
```

A change to the Reference House 001 fingerprint means the fixture or the canonicalization changed, and requires a decision.
