# D044 — Undo and redo with `UndoToRevision`

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Undo and redo for VS-01 (FR-01). Approved from [MODEL-003](../../implementation/tasks/MODEL-003.md) §10, item 4. Adds a command to [D043](D043-vs01-command-set.md).  
**Amends:** [D041](D041-deterministic-id-minting.md) (adds an exception for restoration).

## Decision

VS-01 includes **`UndoToRevision {target_revision_id}`**.

- **Effect:** the command creates a new revision whose `building` and `entities` are exactly those of the target revision, compared canonically ([D030](D030-canonical-snapshot-entity-order.md)).
  - The new revision gets a fresh `revision_id` minted from the command (D041).
  - Its `parent_revision_id` is the current head, so history stays linear with one parent per revision ([D026](D026-canonical-units-identity-persistence.md)).
  - No earlier revision is modified or removed.
- **Redo:** redo is the same command targeting a later revision. Any revision in the project's history can be a target.
- **Restored IDs (exception to D041):** records that existed in the target, including members retired after it, come back with **their original IDs**. Restoring a member's earlier state is different from creating a new member, so references to it, such as future comments or approvals, reattach to the same entity.
  - D041's rule that a re-added generation key gets a new ID still applies to every other command.
  - building-model.md §5 ("never reassign a retired ID to a different member") is satisfied, because the ID returns to the same member.
- **Validation:** the restored snapshot is validated against the **current** rules. If a rule has changed so that the target is no longer valid or supported, the undo is rejected with the usual codes; it is never applied unvalidated.
- **Errors:** a target that is not a revision of this project is `DANGLING_REFERENCE` at `args.target_revision_id`. Targeting the current head (or any revision with identical content) is a no-op (MODEL-003 §10, item 6).
- **Loading the target:** the target snapshot is loaded by revision persistence (`MODEL-004`). The command logic in MODEL-003 receives it as an input.
- **Classification:** follows the VS-01 classification table (MODEL-003 §10, item 7). The proposal there classifies undo as consequential, because it can change anything.

## Rationale

FR-01 requires undo and redo that preserve model consistency. Expressing undo as an ordinary command keeps one change path: undo is validated, previewed, and audited like any edit, and the revision history stays append-only. Restoring the original IDs keeps the identity of members stable across undo.

## What this does not decide

- Branches or alternative histories (deferred by D026 and FR-01).
- Selective undo of one operation in the middle of the history.
- UI affordances such as undo stacks or keyboard shortcuts.
