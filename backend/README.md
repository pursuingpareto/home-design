# Backend

Python backend for the Home Design Platform. Currently contains the `model` module from [MODEL-001](../docs/implementation/tasks/MODEL-001.md) (with typed commands from [MODEL-003](../docs/implementation/tasks/MODEL-003.md)) and the `timber` module from [TIMBER-001](../docs/implementation/tasks/TIMBER-001.md). Together they provide the authoritative Pydantic schema for VS-01 snapshots (D028), five-stage validation including rule conformance (D035, D046), the `vs01-post-beam-1` generator, and RFC 8785 canonical serialization and fingerprints (D029, D030). No HTTP API, persistence, or UI yet.

## Setup

Requires [uv](https://docs.astral.sh/uv/). uv installs the pinned Python (`.python-version`, 3.12) and the locked dependencies (`uv.lock`).

```bash
cd backend
uv sync
```

## Common commands

```bash
uv run pytest                                      # full test suite
uv run python -m homedesign.model.schema_export    # regenerate the snapshot and command JSON Schemas in docs/architecture/schemas/
uv run python -m homedesign.model.schema_export --check   # fail if the committed schema is stale
```

## Using the library

```python
from homedesign.model import validate_bytes, snapshot_fingerprint

result = validate_bytes(open("snapshot.json", "rb").read())
if result.valid:
    print(snapshot_fingerprint(result.snapshot))   # sha256:… over the canonical snapshot
else:
    print(result.code, [issue.to_dict() for issue in result.issues])
```

- `validate_bytes(data)` parses untrusted JSON strictly (duplicate keys, NaN, size and depth limits) and validates it. `validate_value(obj)` validates an already-parsed value. Neither raises.
- `canonical_json(value)` and `fingerprint(value)` implement RFC 8785 for any I-JSON value. `canonical_snapshot(snapshot)` sorts `entities` by `id` first (D030).

## Layout

| Path | Contents |
|---|---|
| `src/homedesign/model/schema.py` | Pydantic models (stage 1 contract; JSON Schema is exported from here) |
| `src/homedesign/model/validation.py` | Stages 1–5, issue paths, `related_paths` |
| `src/homedesign/model/codes.py` | Detail-code catalog (must match building-model.md §6.1) |
| `src/homedesign/model/vs01.py` | VS-01 bounds and tolerances (D031–D034) |
| `src/homedesign/model/jcs.py`, `canonical.py` | RFC 8785 and snapshot fingerprints |
| `src/homedesign/model/strict_json.py`, `paths.py` | Strict parser and D036 path rendering |
| `src/homedesign/model/commands/` | Typed commands: envelopes, `propose`/`propose_create`, D041 minting, diff and classification, packaged template |
| `src/homedesign/timber/` | Rule registry, `vs01-post-beam-1` (`generate`, `conformance`), `GeneratedMember` |
| `tests/` | Fixture, mutation table, generator, JCS and inventory vectors, property tests, catalog-doc sync |
