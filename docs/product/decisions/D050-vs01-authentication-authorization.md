# D050 — VS-01 authentication and authorization

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** Who may call the VS-01 HTTP API, and which projects they may read and write. Approved from [API-001](../../implementation/tasks/API-001.md) §11, items 4–5. Production identity stays open (open question 8).

## Decision

### Authentication

- **Pluggable:** an `Authenticator` turns a request into an authenticated actor (a canonical UUID) or rejects it. Routes depend only on that interface.
- **Development authenticator:** VS-01 ships exactly one.
  - Requests carry `Authorization: Bearer <token>`.
  - Tokens are mapped to actor UUIDs by server configuration (`HOMEDESIGN_DEV_TOKENS`).
  - A missing, malformed, or unknown token is **401 `UNAUTHORIZED`**.
  - Tokens are never logged or echoed.
- **Not for production:** the development authenticator is for development and test environments only. It is replaced by a real identity provider when open question 8 is decided, with no route changes.
- **Server-side identity:** the actor comes only from authentication, never from a request body or header that a client controls (interfaces.md §2).

### Authorization

- **Owner only:** in VS-01, a project is readable and writable **only by its creator**, the actor stored as `projects.created_by`. Creating a project requires only authentication.
- **Other actors get 404:** any other authenticated actor receives **404 `NOT_FOUND`** for every route under that project. That is the same response as for a project that does not exist, so a project's existence is never revealed (interfaces.md §9, test 6).
- **403 is reserved:** `FORBIDDEN` (403) is kept for later roles that can see a project but may not perform an action.
- **Checked on the server**, before any service call, on every project route (interfaces.md §8).

## Rationale

VS-01 needs a real security boundary for its contract tests and a stable actor identity for audit, idempotency, and ID minting (D041). It does not need accounts or sharing. A pluggable development authenticator provides both without deciding hosting or identity prematurely. Hiding existence (404) is the conservative default for project URLs that contain identifiers.

## What this does not decide

- The production identity provider, sessions, token issuance, or rotation (open question 8).
- Roles, sharing, project membership, and professional reviewers (FR-11, VS-06). These replace the owner-only rule with a membership model.
- Rate limiting and abuse protection.
