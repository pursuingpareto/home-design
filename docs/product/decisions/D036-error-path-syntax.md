# D036 — Error detail path syntax

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** The `path` field of error details ([interfaces.md §7](../../architecture/interfaces.md#7-error-contract)) for snapshot validation and command arguments. Approved from [MODEL-001](../../implementation/tasks/MODEL-001.md) §9, item 2.  
**Amended by:** [D042](D042-stable-grid-line-ids.md) — grid fractions are now `x_lines[k].fraction` / `y_lines[k].fraction`; values unchanged.

## Decision

A `path` addresses one location, starting from the root of the validated document. For snapshots that root is the snapshot; for commands it is the command envelope, so argument paths begin with `args.`.

| Element | Form | Example |
|---|---|---|
| Whole document | empty string | `""` |
| Object field (identifier key) | `name`, joined with `.` | `building.footprint_id`, `args.width_m` |
| Object field (any other key) | `["…"]` with the key as a JSON string literal | `entities[<id>]["a.b"]` |
| Snapshot entity with a usable ID | `entities[<id>]` | `entities[9ba359f1-6354-5019-9b3f-d15f8e53523b].width_m` |
| Snapshot entity without a usable ID | `entities[#<index>]` | `entities[#12]` |
| Element of any other array | `[<index>]`, zero-based | `entities[<id>].x_fractions[2]`, `building.level_ids[1]` |

Rules:

- **Identifier keys:** an identifier key matches `^[A-Za-z_][A-Za-z0-9_]*$`. Every schema field qualifies. The quoted form is only needed for keys reported by `UNKNOWN_FIELD` or `DUPLICATE_KEY`.
- **When an entity has no usable ID:** an entity's ID is *usable* when it is present, a valid lowercase UUID ([D030](D030-canonical-snapshot-entity-order.md)), and unique in the snapshot. Otherwise the entity is addressed by its position in the submitted `entities` array, and `#` marks it as a position rather than an ID. Each entity that shares a duplicated ID is reported by its own position.
- **Why entities use IDs:** entity order has no meaning (D030), so an index would point at a different record once the array is reordered. Other arrays have a semantic order (D030), so indexes are stable for them.
- **Unambiguous paths:** a path is plain text with no further escaping. The quoted form uses JSON string escaping, and a path can always be parsed back into a list of steps.

## What this does not decide

- Whether an issue may carry additional `related_paths` (MODEL-001 §9, item 3).
- Paths into artifact payloads or persistence records (no consumer yet).
