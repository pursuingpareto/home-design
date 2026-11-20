# D059 — VS-02 junction rules and `SetConnectionType`

**Status:** Confirmed (implemented in VS-02, [CONN-001](../../implementation/tasks/CONN-001.md))  
**Date:** 2026-11-20  
**Scope:** Which connections `vs02-frame-1` generates, which member receives each one, and how switching a junction class's type is classified. Approved from [CONN-001](../../implementation/tasks/CONN-001.md) §11, items 7–10.  
**Resolves:** the two open points of [D054](D054-vs02-connection-catalog.md): the exact junction rules (and so the Reference House 001 v2 count), and the type-switching command's classification.  
**Amends:** [dependencies.md §4.1](../../architecture/dependencies.md#41-classification-table-vs02-change-classes-1): table `vs02-change-classes-1` gains its `SetConnectionType` row, as [D057](D057-vs02-frame-command-roof-classification.md) anticipated. The row was added with the implementation, because a test keeps the table equal to the server's classification.

## Decision

### One connection per entering member end (item 7)

A connection is generated for each member end that lands on another member's axis and that one of the seven D054 classes covers. The member whose end it is **enters**. The member it lands on **receives**. Where an end lands on several candidate members, exactly one receives (below).

- **Reference House 001 v2: 312 connections.** That is 68 `post-beam`, 12 `post-sill`, 136 `brace`, 60 `joist-beam`, 4 `rafter-peak`, 8 `rafter-foot`, and 24 `purlin-rafter`.
- **Formula:** `4·B + nx·ny + 3·nx + 2·(braces + joists + purlins)`, with `B = ny·(nx − 1) + nx·(ny − 1)`.
- **Reconciliation with the frame:**
  - two connections per beam, brace, joist, and purlin;
  - one per Level 0 post;
  - three per principal rafter pair.

### Receiving members where several meet (item 8)

| End | Receiving member |
|---|---|
| Beam end, and a knee brace's lower end | The post **below** the plane: the Level 0 post on the Level 1 plane, and the Level 1 post on the eave plane |
| Level 0 post foot | The **Y-direction sill in the post's bent** (its X grid line): the bay that starts at the post's Y line, or ends there on the last line |
| Principal rafter foot | The **tie beam**: the eave-plane Y-direction beam in the rafter's bent, in the first Y bay (south) or the last (north) |
| Rafter peak | The **south** rafter receives; the north rafter enters |

These choices set `member_ids` and generation keys only. `location_m` is always the entering member's endpoint, so neither the count nor any location depends on them.

### Junctions without a class get no record (item 9)

The Level 1 post-to-post splices, the sill-to-sill joints at grid stations, and the other contacts at a rafter foot (plate and post) get **no `Connection` record** and are not counted.

- The omission is documented in generation-rules.md and the reference house README.
- `ART-002` adds a schedule and estimate assumption line for it, so the per-piece lines are not read as complete. For example: "Post splices and sill joints at grid stations are not counted."
- A `post-post` class, or any other new class, is a new catalog version and needs its own decision (D054).

### `SetConnectionType` is consequential (item 10)

`SetConnectionType {junction_class, connection_type}` sets `FrameSystem.connection_defaults[junction_class]` and regenerates that class's connections. It requires a preview and confirmation. Its arguments and errors are in [interfaces.md §2](../../architecture/interfaces.md#2-command-envelope).

## Rationale

- **Honest per-piece counts:** a connection stands for one joint a builder would cut. Counting every pair of members that meet would give 388 connections for the reference house: 102 `post-beam`, 34 `post-sill`, and 28 `rafter-foot`. The extra 76 are joints nobody cuts, and the estimate would price them (D054 §"Estimate").
- **Receiving members follow the bent:** a beam, its brace, and the post below form one braced triangle. Post feet and rafter feet are received by members in their own bent, as braces lie in their beam's plane ([D058](D058-datum-reference-axes.md)). The rafter-to-tie-beam joint is the traditional one.
- **No improvised joinery:** the D054 catalog has no splice type, and every class needs a traditional and an engineered type. Leaving these joints out, and saying so, keeps the output preliminary and honest (AC2-07) without inventing types.
- **Conservative classification:** the command changes every connection of a class at once, as `SetMemberSection` changes every member of a role (D040). Switching between traditional and engineered joinery has budget implications, which dependencies.md §4 classes as consequential.

## Alternatives considered

- **One connection per meeting pair of members** (388 for the reference house). It needs no choice of receiving member, but overcounts joints.
- **The post above at Level 1, X-direction sills for post feet, or the eave plate for rafter feet.** Each is deterministic too, but splits braced triangles or leaves the bent. The plate also needs a second tie-break at interior bents.
- **A `post-post` class now** (324 connections). It needs a new catalog version and two new types, and still leaves sill joints uncounted.
- **`SetConnectionType` as routine,** applied directly with undo. Quicker in the browser, but inconsistent with dependencies.md §4's budget wording.

## What this does not decide

- How the schedule, estimate, plan, and mesh present connections, and the wording of the assumption line (`ART-002`).
- Any splice class or type, and continuous posts or sills.
- Any engineering analysis of connections (VS-04). Nothing here asserts that a joint is adequate (AC-08).
