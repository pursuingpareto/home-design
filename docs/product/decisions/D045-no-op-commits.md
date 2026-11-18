# D045 — No-op commands create no revision

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Preview and commit behavior when a command would not change the model. Approved from [MODEL-003](../../implementation/tasks/MODEL-003.md) §10, item 6.

## Decision

A command is a **no-op** when its candidate's `building` and `entities` are canonically equal to the base snapshot's ([D030](D030-canonical-snapshot-entity-order.md)). Examples are setting the current width, or `UndoToRevision` targeting identical content ([D044](D044-undo-to-revision.md)).

- **Preview:**
  - `is_noop` is `true`, and `changes` and the `members` lists are empty.
  - `revision_id` is `null`, because no revision will be created.
  - `confirmation_required` is `false` whatever the command's classification, because there is nothing to confirm.
- **Commit:**
  - The commit succeeds **without creating a revision**. The project head, the stored snapshots, and artifact statuses are unchanged.
  - The response is HTTP **200** (not 201), with `revision_id` equal to the current head and `is_noop: true`.
- **Audit:** the operation log still records the attempt, including its actor, command, base revision, and result `noop`. Its `operation_id` is minted as usual ([D041](D041-deterministic-id-minting.md)).
- **Idempotency:** retrying the same command returns the same no-op result. If the head has moved since the preview, the usual `REVISION_CONFLICT` rules apply.
- **Validation still applies:** a command that is invalid is rejected even if it would otherwise change nothing. A no-op is a valid command with no effect.

## Rationale

Identical revisions would clutter the history. They would also make every artifact look stale (each fingerprint covers the snapshot, including its `revision_id`), and they would turn retries and double-clicks into history entries. Logging the attempt keeps the audit trail complete without changing the model.

## What this does not decide

- Whether the UI disables controls that would produce a no-op.
- How long operation-log entries are retained.
