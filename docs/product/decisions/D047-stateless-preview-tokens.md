# D047 — Stateless signed preview tokens

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** How a commit is bound to its preview (dependencies.md §5), and the related error codes. Approved from [MODEL-004](../../implementation/tasks/MODEL-004.md) §10, item 5.

## Decision

### The token

- **Issued with every preview:** each preview returns a **`preview_token`**, an opaque string, together with `expires_at`. It replaces the illustrative `preview_id` UUID in interfaces.md §3.
- **What it signs:** the token is an **HMAC-SHA-256** signature, made with a server-held key, over the RFC 8785 canonical form ([D029](D029-canonical-json-rfc8785.md)) of:

  ```text
  {project_id, actor_id, base_revision_id, command_hash, expires_at}
  ```

- **Lifetime:** `expires_at` = issue time + **15 minutes**, set by the server.
- **No storage:** previews are stateless; nothing is written when a preview is issued (interfaces.md §9, test 2).

### Commit checks

| Situation | Result |
|---|---|
| Consequential command, not a no-op, without a token | `PREVIEW_REQUIRED` (HTTP **428**), a new stable code |
| The signature does not verify, or any signed field differs from the commit's project, actor, base revision, or `command_hash` | `PREVIEW_INVALID` (HTTP **409**), a new stable code |
| The token verifies but `expires_at` has passed | `PREVIEW_EXPIRED` (HTTP 409), an existing code |
| Routine command, or a no-op ([D045](D045-no-op-commits.md)) | No token needed. A token, if supplied, must still be valid |

Order of checks: idempotency, then `REVISION_CONFLICT` (base ≠ head), then command validation, then the preview checks above. A stale preview is therefore always reported as a revision conflict, which tells the client to refresh.

### Key management

The signing key comes from server configuration and is never logged or returned. Tests use a fixed key. Rotation, multiple active keys, and storage are deferred to hosting and security (open question 8). Until then, changing the key invalidates outstanding previews, which only costs users a fresh preview.

## Rationale

Previews may be frequent, for example while dragging a dimension. A stateless token avoids a database write per preview and needs no cleanup of expired rows. It also satisfies the existing contract that previews have no side effects. The signature prevents a client from forging a confirmation, and binding the base revision and command hash means the confirmed command is exactly the previewed one.

## Rejected alternative

Storing previews in a table: no key to manage, but a write on every preview (contradicting interfaces.md §9, test 2) and a cleanup job for expired rows.
