# D061 — VS-02 selector contents, builders over selections, and where the impact property is tested

**Status:** Confirmed; implemented ([DEP-001](../../implementation/tasks/DEP-001.md), VS-02)  
**Date:** 2026-11-20  
**Scope:** What each version 2 selector extracts, how derivations consume their selections, and which task carries AC2-04's if-and-only-if check. Approved from [DEP-001](../../implementation/tasks/DEP-001.md) §13, items 8–10. The routine items 1–7 of that list are specified in the task file, and go into artifacts.md, interfaces.md, and dependencies.md with the implementation.  
**Refines:** [D056](D056-dependency-selectors.md) item 4, which left "exact field lists" to the VS-02 task files. D056 is otherwise unchanged.  
**Amends** (done with DEP-001): the task breakdown in [vs-02.md](../../implementation/acceptance-tests/vs-02.md) §12.2. "The if-and-only-if impact property" moves from `TEST-002` to `DEP-001`.

## Decision

### Selections are projections of what each builder reads (item 8)

A selection contains **exactly the values its builder reads, after the projections the builder itself applies, and nothing else.** AC2-04 ("if and only if its payload changes") governs where D056 item 4's lists are coarser. In particular:

- **No grid** in any selection. Nor the `FrameSystem`, unused sections and materials, or revision metadata. Their effects reach payloads only through the members and connections, which are selected.
- **`plan2d`:** member and connection positions in plan `x, y`, plane heights, and level IDs. No 3D axes and no pitch.
- **`mesh3d`:** each member's section dimensions, not its `section_id`.
- **`timber_schedule`:** each member's reference-axis length, not its axis.
- **`preliminary_estimate`:** the schedule's `aggregates`, `connection_aggregates`, and `assumptions`, not the schedule's fingerprint. Plus the price book, as before.

The exact contents are in DEP-001 §4.2.

**Measured consequences on Reference House 001 v2** (DEP-001 §8). Each is narrower than vs-02.md §11's example "footprint, grid, roof, and story-height changes still affect all four":

- a pitch-only roof edit leaves `plan2d` unchanged;
- an overhang-only roof edit leaves `timber_schedule` and `preliminary_estimate` unchanged;
- a joist spacing that keeps the joist count leaves `timber_schedule` and `preliminary_estimate` unchanged;
- a section swap with the same dimensions leaves `mesh3d` unchanged;
- re-identifying grid line `y1` at the same fraction leaves `preliminary_estimate` unchanged.

### Builders take their selection as their only model input (item 9)

`build_plan2d`, `build_mesh3d`, and `build_schedule` read their selection, not the snapshot. `build_estimate` already reads only the schedule's lists and the price book. A builder therefore cannot read a value that its selection omits.

### The if-and-only-if property lands with DEP-001 (item 10)

DEP-001 adds the AC2-04 check to the existing property-based sequences, the invariants (every payload equals a fresh build), and the golden scenario. `TEST-002` keeps the traceability matrix for AC2-01 to AC2-09 and the golden scenario's new commands.

## Rationale

- **The criterion governs:** every case above is reachable, and was measured. A coarser selection lists an artifact whose payload does not change, which AC2-04 forbids.
- **Correct by construction:** when a builder reads only its selection, the "if" direction of AC2-04 cannot fail through a missed field. The property tests then guard mainly against over-selection.
- **Checked when it lands:** `main` should not claim exact impact while only hand-picked cases check it.

## Alternatives considered

- **Field-level selections as D056 lists them** (axes, sections, grid, the whole roof). They are simpler to state, but they over-report in every case above, and AC2-04 would have to be weakened to "only if".
- **Selectors beside snapshot builders.** This is a smaller change, but the two can drift, and only the property tests would catch it, for the edits they happen to draw.
- **The property in `TEST-002`, as §12.2 had it.** That keeps the breakdown as written, but leaves DEP-001's exactness checked only by its targeted cases until `TEST-002` lands.

## What this does not decide

- The fingerprint object, reuse rules, and API typing (DEP-001 items 1–7, routine).
- Browser presentation of impact beyond the empty case (`UI-003`).
- Asynchronous workers (D056 item 6: not in VS-02).
