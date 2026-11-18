# D041 — Deterministic ID minting from the command

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** How the server creates IDs for entities, revisions, and operations produced by a command. Closes gap M2. IDs remain opaque UUIDs ([D026](D026-canonical-units-identity-persistence.md)).  
**Amended by:** [D044](D044-undo-to-revision.md) — `UndoToRevision` restores records with their original IDs, an exception to "re-added keys get new IDs".

## Decision

Every ID a command creates is a **UUIDv5** whose name is the RFC 8785 canonical JSON ([D029](D029-canonical-json-rfc8785.md)) of an array that identifies the command and the thing being created:

```text
id = UUIDv5(NAMESPACE, canonical_json([purpose, project_id, actor_id, command_id, creation_key]))
NAMESPACE = 6652101f-3d1d-4a2b-bd82-9d87e0207354
```

- **`NAMESPACE`** is a fixed constant of this platform. It never changes; changing it would change every ID that replay produces.
- **`project_id`, `actor_id`, `command_id`:** the command's idempotency identity. `command_id` is scoped to project and actor ([interfaces.md §2](../../architecture/interfaces.md#2-command-envelope)), so this triple identifies exactly one command. `actor_id` is the authenticated actor's opaque server-side ID, never a value taken from the request body.
- **`purpose` and `creation_key`:**

  | Created thing | `purpose` | `creation_key` |
  |---|---|---|
  | Generated member (new generation key) | `"entity"` | `"generation/" + generation_key` |
  | Record created from a template (`CreateReferenceProject`) | `"entity"` | `"template/" + template record ID` |
  | The revision a command commits | `"revision"` | `null` |
  | The operation record | `"operation"` | `null` |

  Later commands that create records must define their `creation_key` in their own contract, unique within that command.
- **IDs that are not derived:** `project_id` (assigned by the server at creation and stored with the idempotency record) and `preview_id`. Both are random UUIDv4.
- **Existing records:** an entity that survives a command keeps its ID. For generated members, that means the generation key still exists (building-model.md §5).

## Consequences

- **Preview equals commit:** a preview reports exactly the IDs the commit will create, without storing a candidate snapshot.
- **Deterministic replay:** re-running the operation log reproduces identical revisions, entity IDs, and canonical fingerprints (AC-09).
- **No reuse of retired IDs:** a generation key that is removed and later re-added is re-created by a different command, so it gets a new ID. No retired-ID ledger is needed in VS-01. Collisions would require a SHA-1 collision across 122 bits.
- **Identical commands, identical IDs:** idempotent retries of the same command (same identity and payload) mint the same IDs. A different payload under the same `command_id` is already rejected with `IDEMPOTENCY_CONFLICT` before anything is minted.
- **Projects from the template get their own IDs:** `CreateReferenceProject` creates the non-generated records from the template (with `template/…` keys) and then runs the generator, so members get `generation/…` keys. No project reuses the fixture's IDs.
- **Fixture IDs are arbitrary:** the Reference House 001 fixture's IDs are fixed, arbitrary values. They are UUIDv5 values from an undocumented namespace and need not be reproducible. Clients must not read meaning into any ID.

## Test vector (for `MODEL-003`)

```text
name  = ["entity","17ac32e0-0b3b-518e-b568-adf98f41bcd0","00000000-0000-4000-8000-000000000001","b8f9d645-5a10-4eb5-b2ca-38ce46e5d4aa","generation/frame/x0/y0/level-0/post"]
id    = 5f9ff518-e552-59c3-b2a6-798263c3f9ac
```

`MODEL-003` must add this vector to `tests/vectors/` and confirm it with an independent implementation.

## What this does not decide

- **Persistence check:** whether `MODEL-004` should also reject a commit that adds an ID already seen in an earlier revision of the project. This is recommended as defense in depth; it is not required by this decision.
- **Grid keys:** how generation keys are defined when grid lines are inserted or removed. Decided in [D042](D042-stable-grid-line-ids.md); the test vector above uses D042 keys.
- Import of external snapshots, whose IDs would not follow this scheme.
