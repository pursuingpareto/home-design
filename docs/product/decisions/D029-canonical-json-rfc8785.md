# D029 — Canonical JSON serialization (RFC 8785)

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Every place the specification needs the bytes of a JSON value to be reproducible across runs, processes, and languages (Python and TypeScript).

## Decision

**Canonical JSON** means the **JSON Canonicalization Scheme (JCS), [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785)**, encoded as UTF-8.

It applies to:

- Artifact `input_fingerprint` values ([artifacts.md](../../architecture/artifacts.md) §2.3): `sha256:` + lowercase hex of SHA-256 over the JCS bytes of the canonical input object.
- Preview `command_hash` and the operation hash that binds a confirmation to a preview ([interfaces.md](../../architecture/interfaces.md) §3, [dependencies.md](../../architecture/dependencies.md) §5).
- Payload comparison for idempotent retries (a repeated `command_id` with a different payload is `IDEMPOTENCY_CONFLICT`).
- Determinism tests that require "byte-equivalent" output, including canonical schedules ([building-model.md](../../architecture/building-model.md) §9 test 5).
- Golden-fixture comparisons and snapshot round-trip checks. Round-trip equality is tested on the canonical bytes, so what matters is the parsed values, not the key order or whitespace of the original text.

## Consequences and constraints

- **Key order:** JCS sorts object keys by UTF-16 code unit. This replaces the "sorted lexicographically" wording in artifacts.md §2.3. **Arrays keep their order**, so the documented ordering rules (for example, sort by `generation_key`) still decide array contents.
- **Numbers:** serialized as JCS specifies (ECMAScript number-to-string on IEEE-754 doubles). `1.0` becomes `1`, and `-0` becomes `0`. Non-finite values cannot be serialized, which matches D026.
- **Integers:** integer fields, including money in minor units (D026), must stay within ±(2⁵³ − 1) to stay exact. Values outside that range fail validation instead of losing precision.
- **Strings:** JCS does not apply Unicode normalization. Strings are hashed exactly as stored. Nothing in VS-01 uses string identity except UUIDs and enumerated codes.
- **Duplicate keys:** input with duplicate object keys is rejected (I-JSON, RFC 7493), not silently resolved.
- **Storage and API:** the JCS requirement covers **hashing and comparison only**. Snapshots remain PostgreSQL JSONB (D026), and API responses need not be canonical. Hashes are always computed by re-canonicalizing parsed values, never over JSONB text or a response body.
- **Conformance:** the Python implementation (and any TypeScript implementation that computes or verifies hashes) must pass the RFC 8785 examples, plus a shared set of cross-language test vectors committed in the repository. The vectors must cover non-integral doubles taken from Reference House 001, such as `0.6435011087932844` and `3.6575999999999995`.

## Rationale

The exact byte format underlies freshness (fingerprints), preview binding, and determinism tests. An informal "sorted keys" rule leaves number formatting undefined, and the defaults differ between Python and JavaScript. JCS is a published standard with libraries in both languages and is close to the existing wording. The rejected alternative is a project-specific scheme (for example, fixed decimal places), which would be simpler to describe but would be ours to maintain and verify.

## What this does not decide

- Which JCS library is used; `MODEL-001` chooses it and explains the tradeoffs.
- What goes into each hashed input object. That stays defined by artifacts.md §2.3 and interfaces.md §3 (including the open question of whether `revision_id` belongs in fingerprints).
