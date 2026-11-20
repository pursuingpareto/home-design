# D054 — VS-02 connection catalog: generated, typed per junction class, no claims

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** What a VS-02 `Connection` is, the initial catalog, and where connections appear. Approved as decision 4 of the [VS-02 scope proposal](../../implementation/acceptance-tests/vs-02.md) (§9), within [D051](D051-vs02-slice-boundary.md).  
**Partially resolves:** open question 4, for **connection types only**. Engineering analysis boundaries stay open, for VS-04.  
**Refines:** D007 (traditional and engineered connections) and FR-04 ("a deliberately limited subset").

## Decision

### Records

- **Two members:** a `Connection` joins exactly two members, where one member's end meets the other. Its fields are:
  - `connection_type` (a catalog key);
  - `member_ids` (receiving and entering);
  - `location_m`, where the entering member's reference axis meets the receiving member's;
  - `junction_class`;
  - `generation_key`, derived from the two members' keys, so IDs stay stable (D041, D042).
- **Generated, like members:** connections are generated from the frame, one per junction, and are subject to conformance (D046). In VS-02, users do not place or edit individual connections.
- **Typed per junction class:** a type is chosen per junction class, as sections are chosen per role (D040). Every class defaults to its traditional type and has exactly one engineered alternative.

### Catalog (version 1)

| Junction class | Default (traditional) | Engineered alternative |
|---|---|---|
| `post-beam` | `PEGGED_MORTISE_TENON` | `STEEL_KNIFE_PLATE` |
| `post-sill` | `PEGGED_MORTISE_TENON` | `STEEL_KNIFE_PLATE` |
| `brace` (each end) | `PEGGED_MORTISE_TENON` | `STEEL_KNIFE_PLATE` |
| `joist-beam` | `HOUSED_DOVETAIL` | `JOIST_HANGER` |
| `rafter-peak` | `BRIDLE` | `STEEL_KNIFE_PLATE` |
| `rafter-foot` | `PEGGED_MORTISE_TENON` | `STEEL_KNIFE_PLATE` |
| `purlin-rafter` | `PEGGED_MORTISE_TENON` | `STEEL_KNIFE_PLATE` |

There are five types: `PEGGED_MORTISE_TENON`, `BRIDLE`, `HOUSED_DOVETAIL`, `STEEL_KNIFE_PLATE`, and `JOIST_HANGER`. Adding types or alternatives is a new catalog version, not a schema change.

### Where connections appear

- **3D and plan:** markers at `location_m`, colored by type and selectable.
- **Schedule:** a connection list, plus counts per type and junction class.
- **Estimate:** one line per type, counted "each" and priced by a price-book row `connection.<TYPE>`. Price-book units extend from meters only to meters or each. Unpriced types stay unpriced (artifacts.md §8.1).

### What a connection does not claim

- Capacity, adequacy, or code compliance.
- Peg, dowel, plate, or fastener sizes or positions.
- Machining geometry, or cut lengths. Member lengths remain reference-axis lengths.

Every output carries the preliminary label (AC-08). Catalog descriptions state that types are representational only.

## Rationale

- **Smallest useful catalog:** one traditional and one engineered option per junction satisfies D007 with the smallest catalog that is still useful to builders. It also gives the estimate per-piece lines.
- **Generated, not placed:** generating connections from the frame keeps them consistent with regeneration and conformance. Hand placement would need its own identity and validation story, so it waits for a later slice.

## What this does not decide

- **Exact junction rules,** such as which member is receiving, and so the connection counts for Reference House 001 v2. These are specified with the rule and reconciled in tests.
- **The type-switching command's name and classification,** which come with the VS-02 command set.
- **Any engineering analysis of connections** (VS-04).
