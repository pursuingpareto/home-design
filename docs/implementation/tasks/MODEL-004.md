# MODEL-004 — Revision persistence, concurrency, idempotency, and previews

**Status:** Ready for implementation — all §10 proposals approved (2026-11-18)  
**Owner module:** `project` (interfaces.md §1: identity, head, revision persistence)  
**Slice:** VS-01  
**Depends on:** `MODEL-001`, `TIMBER-001`, `MODEL-003` (all done)  
**Unblocks:** the API task, the artifact tasks (which add an outbox to the same transaction), `UI-001`

## 1. Objective and user-visible behavior

Persist projects and their immutable revision history, and wrap `MODEL-003`'s pure `propose` in a transactional **preview → commit** service. The service enforces:

- optimistic concurrency (D026);
- idempotent retries (interfaces.md §2);
- preview binding and expiry (dependencies.md §5);
- no-op handling (D045);
- an append-only audit log.

There is no HTTP yet: the API task exposes these service calls. After this task, AC-05 holds: saving and reopening restores semantically equivalent data, including revision IDs. Deterministic replay of the operation log (AC-09) is also tested.

## 2. Inputs and governing documents

- Decisions:
  - [D026](../../product/decisions/D026-canonical-units-identity-persistence.md): JSONB snapshots, append-only operations, one parent per revision, `REVISION_CONFLICT`;
  - [D029](../../product/decisions/D029-canonical-json-rfc8785.md)/[D030](../../product/decisions/D030-canonical-snapshot-entity-order.md): canonical form;
  - [D041](../../product/decisions/D041-deterministic-id-minting.md): the server assigns project IDs, and other IDs are minted from the command;
  - [D044](../../product/decisions/D044-undo-to-revision.md): undo;
  - [D045](../../product/decisions/D045-no-op-commits.md): no-ops.
- [interfaces.md](../../architecture/interfaces.md) §2–5, §7–9; [dependencies.md](../../architecture/dependencies.md) §4.1, §5; [building-model.md](../../architecture/building-model.md) §7–9.

## 3. Scope

**In scope**

- `homedesign.project`, which provides a `ProjectService`:
  - `create_project(command, *, actor_id, now) -> CommitResult`;
  - `preview(project_id, command, *, actor_id, now) -> PreviewResult`;
  - `commit(project_id, command, preview_token | None, *, actor_id, now) -> CommitResult`;
  - `get_project(project_id)`, `get_revision(project_id, revision_id) -> Snapshot`, and `list_revisions(project_id)`.
- A `RevisionStore` interface with two implementations: **in-memory**, for fast unit tests, and **PostgreSQL**, for production. One shared contract test suite runs against both.
- The PostgreSQL schema and migrations (§5), and immutability enforced in the database.
- Signed, stateless preview tokens (§6).
- Deterministic replay of the operation log (§8, test 12).

**Non-goals**

- HTTP routes, authentication, and authorization → API task. `actor_id` is passed in, already authenticated.
- Artifact derivation, statuses beyond `MISSING`, and the outbox → artifact tasks. The commit transaction leaves a clear hook for them.
- Hosting, backups, connection pooling configuration, observability pipelines (open question 8).
- Branches and merges (deferred by D026).

## 4. Service behavior (§10; approved)

### 4.1 Create

`create_project` runs these steps:

1. Look up idempotency by (`actor_id`, `command_id`). A hit returns the stored result.
2. Assign a random UUIDv4 `project_id` (D041).
3. Call `propose_create`.
4. Persist, in **one transaction**: the project row (head = new revision, sequence 1), the revision, and the operation.

The first commit is HTTP **201**. A replay is **200** with an identical body (§4.4).

### 4.2 Preview

`preview` runs these steps:

1. Load the head snapshot.
2. If `command.base_revision_id` ≠ head, the result is `REVISION_CONFLICT`.
3. For `UndoToRevision`, load the target revision of this project.
4. Call `propose`.
5. Return the interfaces.md §3 preview, plus a **`preview_token`** (§6) and `expires_at`.

A preview **writes nothing** (interfaces.md §9, test 2).

### 4.3 Commit

`commit` runs in one database transaction:

1. Lock the project row (`SELECT … FOR UPDATE`).
2. **Idempotency:** look up (`project_id`, `actor_id`, `command_id`). If the same `command_hash` is found, return the stored result (HTTP 200). A different hash is `IDEMPOTENCY_CONFLICT`.
3. **Concurrency:** if `base_revision_id` ≠ head, the result is `REVISION_CONFLICT`. Nothing is written except the audit row (§4.5).
4. Call `propose` again: the same inputs give the same IDs and diff (MODEL-003). If rejected, return the validation error, and only the audit row is written.
5. **Preview check:**
   - a no-op needs no preview (D045);
   - a `routine` command may commit without one (dependencies.md §4.1);
   - a `consequential` command needs a valid token that matches project, actor, base revision, and `command_hash`. Otherwise the result is `PREVIEW_REQUIRED`, `PREVIEW_EXPIRED`, or `PREVIEW_INVALID` (§6).
6. **No-op:** write the operation (result `noop`) and return HTTP **200** with `revision_id` = head and `is_noop: true`.
7. **Otherwise:**
   - insert the revision (sequence = head sequence + 1, JSONB snapshot, canonical fingerprint) and the operation (result `committed`);
   - advance the head;
   - return HTTP **201** with `{revision_id, parent_revision_id, operation_id, sequence, is_noop: false, artifact_statuses}`.
   
   `artifact_statuses` lists all four artifact types as `MISSING` until the artifact tasks exist (artifacts.md §2.1: never computed).

**Two concurrent commits** against one base yield exactly one winner. The loser receives `REVISION_CONFLICT` (interfaces.md §9, test 4).

### 4.4 Idempotency

- **Scope:** (`project_id`, `actor_id`, `command_id`) for commands; (`actor_id`, `command_id`) for creation.
- **Comparison:** payloads are compared by `command_hash` (D029). A different payload under a used `command_id` is `IDEMPOTENCY_CONFLICT` (409).
- **Replays** return the stored result body with HTTP **200**, flagged `"replayed": true`. Nothing is written.
- **Only `committed` and `noop` operations reserve a `command_id`.** A rejected attempt is audited (§4.5) but does not block a retry under the same ID, for example after fixing a stale base.

### 4.5 Audit

Every commit attempt appends one operation row with its actor, command, command hash, base revision, result (`committed`, `noop`, `rejected`), top-level code if rejected, new revision if any, classification and its version, and timestamp (interfaces.md §8). Rows are never updated or deleted. Project content in the stored command is the command itself; the logs carry no snapshot data (dependencies.md §9).

### 4.6 Reads

- `get_project` returns `{project_id, head_revision_id, head_sequence, created_at}`.
- `get_revision` returns the stored snapshot after checking its canonical fingerprint against the stored value. A mismatch is a `500`-class integrity error, never silently served.
- `list_revisions` returns `{revision_id, parent_revision_id, sequence, created_at, operation_id, command_type}`, ordered by sequence.

## 5. PostgreSQL schema (approved — §10 item 4)

```text
projects   (project_id uuid PK, head_revision_id uuid NOT NULL, head_sequence int NOT NULL,
            created_at timestamptz, created_by uuid)
revisions  (revision_id uuid PK, project_id uuid FK, parent_revision_id uuid NULL FK,
            sequence int NOT NULL, model_schema_version int NOT NULL,
            snapshot jsonb NOT NULL, fingerprint text NOT NULL, created_at timestamptz,
            UNIQUE (project_id, sequence))
operations (operation_id uuid PK, project_id uuid, actor_id uuid, command_id uuid,
            command_type text, command jsonb, command_hash text, base_revision_id uuid NULL,
            result text CHECK (result IN ('committed','noop','rejected')), rejection_code text NULL,
            revision_id uuid NULL, classification text, classification_version text,
            created_at timestamptz)
  -- idempotency: UNIQUE (project_id, actor_id, command_id) WHERE result IN ('committed','noop')
  -- creation:    UNIQUE (actor_id, command_id) WHERE command_type = 'CreateReferenceProject' AND result = 'committed'
```

- **Immutability:** triggers reject `UPDATE` and `DELETE` on `revisions` and `operations`. Only `projects.head_*` changes.
- **Numbers in JSONB:** PostgreSQL stores JSON numbers as exact decimals of their text, and Python writes the shortest round-trip form of each double. So every double reads back bit-identical. `-0` reads back as `0`, which RFC 8785 already treats as equal. A test pins this with fixture and edge values.
- **Migrations** are numbered SQL files applied by a small runner that records them in `schema_migrations` (§10, item 3).

## 6. Preview tokens (approved — D047)

A preview token is an opaque string: an HMAC-SHA-256 signature over the canonical form of `{project_id, actor_id, base_revision_id, command_hash, expires_at}`.

- **Lifetime:** `expires_at` = `now` + **15 minutes**.
- **Key:** the server key comes from configuration. Tests use a fixed key.
- **Commit checks:**
  - a token whose signature does not verify, or whose fields do not match the commit's project, actor, base, and hash, is `PREVIEW_INVALID` (409);
  - an expired token is `PREVIEW_EXPIRED` (409, already a stable code);
  - a consequential commit without a token is `PREVIEW_REQUIRED` (428, Precondition Required).
- **Why stateless:** no table, no cleanup job, and no database write per preview. Previews may be frequent, for example while dragging a dimension, and interfaces.md §9 test 2 requires that previews have no side effects. The cost is a server secret, which needs rotation once hosting is decided (open question 8).
- **Field name:** the preview response field becomes `preview_token` (opaque string) instead of the illustrative `preview_id` UUID in interfaces.md §3.

## 7. Test infrastructure (approved — §10 item 6, local server)

- The **in-memory store** runs every service and contract test with no database.
- The **PostgreSQL store** runs the same contract suite against the developer's **local PostgreSQL server**:
  - The connection comes from `HOMEDESIGN_TEST_DATABASE_URL`. The default is `postgresql:///homedesign_test`: the local Unix socket, the current OS user, and database `homedesign_test`.
  - **Name guard:** the suite refuses to run unless the database name starts with `homedesign_test`, so it can never be pointed at a database holding real data.
  - **Clean start:** at the start of each test session the suite drops and recreates **only that database** (the user needs `CREATEDB`, which Homebrew's default superuser has), then applies the migrations. No other database is touched.
  - **Isolation:** tests use distinct project IDs, so they need no per-test cleanup, and the append-only triggers stay enabled throughout.
- CI sets `HOMEDESIGN_TEST_DATABASE_URL` to its own server under the same name guard.
- If the server is unreachable, the PostgreSQL tests **fail** with a message naming the URL; they never skip silently.

## 8. Acceptance criteria and automated tests

Each test runs against both stores unless marked "PG only".

1. **Create:** `create_project` produces sequence 1, head set, the operation logged. A replay returns an identical body with HTTP 200 and writes nothing. A different payload under the same `command_id` is `IDEMPOTENCY_CONFLICT`.
2. **Previews write nothing:** row counts and the head are unchanged after any number of previews (interfaces.md §9, test 2).
3. **Commit with a valid token:** HTTP 201, head advanced, sequence + 1. The IDs equal the preview's (D041).
4. **Commit without a valid token:**
   - a consequential command without a token is `PREVIEW_REQUIRED`;
   - an expired token is `PREVIEW_EXPIRED`;
   - a tampered token, or one from another actor, project, command, or base, is `PREVIEW_INVALID`;
   - a routine command without a token commits.
5. **Stale base:** after another commit, an old preview commits as `REVISION_CONFLICT`, and the head and stored model are unchanged (building-model.md §9, test 7).
6. **Concurrency:** two concurrent commits on one base give exactly one winner, and the loser gets `REVISION_CONFLICT`. *(PG only: real threads and row locks.)*
7. **Retries:** an idempotent retry creates no duplicate revisions or operations (interfaces.md §9, test 5).
8. **No-op:** HTTP 200, head unchanged, an operation with result `noop`, and no preview needed.
9. **Rejection:** an invalid command returns the MODEL-003 error, writes only a `rejected` audit row, and does not reserve the `command_id`.
10. **Round trip:** the fixture, a regenerated snapshot, and edge values (`3.6575999999999995`, `1e-7`, `-0`) read back with identical canonical bytes and fingerprint (AC-05). *(PG covers JSONB.)*
11. **Immutability:** `UPDATE` or `DELETE` on revisions or operations fails. *(PG only.)*
12. **Deterministic replay (AC-09):** replaying a project's committed operations, in order, into a fresh store reproduces identical revision IDs, snapshots, and fingerprints.
13. **Undo:** undo across stored revisions loads the target from the store and restores the original IDs. A target from another project is `DANGLING_REFERENCE`.
14. **Integrity:** a stored snapshot whose fingerprint no longer matches is refused on read. *(In-memory store: test hook.)*
15. **Ordering:** `list_revisions` is ordered by sequence, and parents form a single chain.

## 9. Implementation guidance (not prescriptive)

- `backend/src/homedesign/project/`: `service.py`, `store.py` (protocol, in-memory), `postgres.py`, `tokens.py`, `migrations/0001_initial.sql`.
- **Injected dependencies:** `now` and the project-ID factory are injected, so tests are deterministic.
- **Transactions:** keep each transaction to one connection and one `BEGIN … COMMIT`. Raise typed errors (`RevisionConflict`, `IdempotencyConflict`, `PreviewRequired`, …) that the API task maps to HTTP statuses.

## 10. Proposals approved by the product owner

1. ~~**Service behavior** (§4): create, preview, and commit steps; HTTP 201 for a new revision and 200 for a no-op or replay; `artifact_statuses` all `MISSING` for now.~~ **Approved**; interfaces.md §4 updated.
2. ~~**Idempotency and audit** (§4.4–4.5): idempotency scopes, replays flagged `"replayed": true`, rejected attempts audited but not reserving the `command_id`.~~ **Approved**; interfaces.md §2, §4, and §8 updated.
3. ~~**Libraries:** **psycopg 3** (synchronous) with **plain SQL migrations** and a small runner, with no ORM.~~ **Approved** over SQLAlchemy Core plus Alembic; recorded in [overview.md](../../architecture/overview.md).
4. ~~**Storage schema** (§5), including per-project `sequence` numbers, stored fingerprints, and immutability triggers.~~ **Approved**; summarized in building-model.md §7.
5. ~~**Stateless signed preview tokens** with a 15-minute lifetime, renaming `preview_id` to `preview_token` (§6), plus `PREVIEW_REQUIRED` (428) and `PREVIEW_INVALID` (409).~~ **Approved: [D047](../../product/decisions/D047-stateless-preview-tokens.md)**; interfaces.md §3, §4, §7 and dependencies.md §5 updated.
6. ~~**Test infrastructure** (§7): an ephemeral `initdb` cluster by default, the `HOMEDESIGN_TEST_DATABASE_URL` override, and fail rather than skip.~~ **Approved with a change:** tests use the **local PostgreSQL server** (database `homedesign_test`, name-guarded, recreated each session) instead of an ephemeral cluster. The override and fail-not-skip remain.

Approved items update interfaces.md §3–5, §7, and §9, and dependencies.md §5. Item 5 is recorded as a decision.

## 11. Definition of done

- All §8 tests pass against both stores. The migration applies cleanly to an empty database.
- interfaces.md and dependencies.md are updated for approved items. The task index and status docs are updated, and backend/README.md documents the database setup.
- Changed files, tests, limitations, and next steps are summarized (AGENTS.md).
