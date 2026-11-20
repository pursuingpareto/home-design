# D060 — VS-02 artifact payloads: roof plan plane, plumb purlins, interim browser scope

**Status:** Confirmed (implemented in VS-02, [ART-002](../../implementation/tasks/ART-002.md))  
**Date:** 2026-11-20  
**Scope:** How the version 2 `plan2d`, `mesh3d`, and `preliminary_estimate` present the complete frame and its connections, where the documents left a choice, and which browser changes ship with the payloads. Approved from [ART-002](../../implementation/tasks/ART-002.md) §12, items 8–10. The routine items 1–7 of that list are specified in the task file and go into artifacts.md with the implementation.  
**Amends:** [D027](D027-vs01-artifact-dtos.md) and [artifacts.md](../../architecture/artifacts.md) §5–8:
- `plan2d` gains a fourth plane and an array per role, and posts and beams lose `section_id` (ART-002 §4.3, so that [D056](D056-dependency-selectors.md)'s "changing a role's section leaves `plan2d` unaffected" holds under AC2-04);
- estimate line items gain a `kind` (`timber` or `connection`), with connection lines counted `each` ([D054](D054-vs02-connection-catalog.md)).

## Decision

### A `roof` plan plane (item 8)

`plan2d` has four planes: `level-0`, `level-1`, `eave`, and **`roof`**. The roof plane holds the principal rafters, the purlins, and the `rafter-foot`, `rafter-peak`, and `purlin-rafter` connection markers. Its `level_id` is `null` and its `z_m` is `z_eave`, the plate line where the roof framing bears ([D058](D058-datum-reference-axes.md)). Its members are plan projections.

Reference House 001 v2: 8 rafters, 12 purlins, and 36 markers on the roof plane.

### Plumb purlins (item 9)

In `mesh3d`, a purlin's `section_depth_m` is vertical, as for every horizontal member. One orientation rule covers every role (ART-002 §5.1). It gives [D053](D053-reference-house-001-v2-design-intent.md)'s "depth vertical" for joists and "depth perpendicular to the roof plane" for principal rafters. Purlin axes, lengths, and connections are unaffected: this is display only.

### Interim browser changes ship with the payloads (item 10)

ART-002 makes the smallest browser changes that keep the existing views correct:
- the estimate table shows connection lines as counts priced each;
- the price-book form takes per-piece prices for `each` rows, with no unit conversion. AC2-08's price-book bullet moves from `UI-003` to ART-002;
- the plan view draws the new roles in one neutral style, including the roof tab.

Connection markers in 2D and 3D, a connection table, role styling, the Frame tab, and the connection-type editor stay in `UI-003`.

## Rationale

- **Roof plane:** each rafter's plan projection lies exactly on its bent's eave tie beam. A separate plane keeps the eave framing and the roof framing above it readable, and gives the plan a roof framing view without a new payload shape.
- **Plumb purlins:** they need no role-specific rule in artifacts.md or the client, and no orientation field. Rolled purlins can be added later as a display change.
- **Browser scope:** without these changes, the current form would submit connection prices per meter, which the new `PRICE_UNIT_MISMATCH` check rejects. The API could then set prices that the browser cannot edit.

## Alternatives considered

- **Rafters and purlins on the `eave` plane:** three planes, but rafters overlap tie beams in plan, and one plane mixes two framing levels.
- **Rolled purlins** (depth perpendicular to the roof plane): also common in principal-rafter roofs, but it needs a special rule or a payload field.
- **Only stopping the browser breakage:** less work here, but per-piece prices would be settable only through the API until `UI-003`.

## What this does not decide

- Selectors and exact `impacted_artifacts` (`DEP-001`). ART-002 §10 lists what each derivation reads, as input for that task.
- How the browser draws coincident connection markers (`UI-003`).
- Any engineering meaning of connections (VS-04). Everything stays preliminary (AC-08).
