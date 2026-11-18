# D040 — `SetMemberSection` changes a role default in VS-01

**Status:** Confirmed  
**Date:** 2026-11-18  
**Scope:** Semantics of the VS-01 `SetMemberSection` command ([interfaces.md §2](../../architecture/interfaces.md#2-command-envelope)). Builds on [D039](D039-frame-member-defaults.md).

## Decision

- In VS-01, `SetMemberSection` **changes the section default of one member role**, the role's `section_id` in `FrameSystem.member_defaults`. It never changes a single member.
- **Effect:** the candidate snapshot regenerates the frame. Every generated member of that role takes the new section. Member IDs and generation keys are unchanged, because geometry and section may change without changing an ID (building-model.md §5). No member is added or retired.
- **Valid targets:**
  - The role must be one the frame's generation rule generates (`POST` or `BEAM` for `vs01-post-beam-1`). Any other role is rejected with `UNSUPPORTED_CONFIGURATION`.
  - The section must already exist in the snapshot. The command references a `Section` by ID; it does not create one. A missing or wrong-kind ID fails stage 2 (`DANGLING_REFERENCE`, `WRONG_REFERENCE_KIND`).
- **Change classification:** consequential by default. Changing every post or beam affects members, the schedule, the 3D view, and any estimate, so it requires an impact preview and confirmation ([dependencies.md §4](../../architecture/dependencies.md#4-change-classification-and-confirmation)). This follows the conservative VS-01 rule for edits that regenerate framing.
- **Dependencies:** `FrameSystem.member_defaults → TimberMember.section_id / material_id → timber_schedule, mesh3d, plan2d, preliminary_estimate`.
- **No per-member overrides in VS-01.** Every generated member must equal its role's defaults. That is checked by generation-rule conformance in `TIMBER-001`.

## Rationale

A role-level change needs no extra data. The result still follows from the snapshot's parameters alone, and a later regeneration cannot silently undo it. A per-member override would need a record of the override that survives regeneration, a field marking members as user-changed, and rules for when an overridden member's generation key disappears. That design is deferred to a later slice.

## Known gaps (not decided here)

- **No way to add sections:** the VS-01 command set has no command for adding a `Section`, so this command can only switch a role between sections already in the snapshot (8×8 and 8×12 for Reference House 001). Whether VS-01 needs a command to add sections is part of the command-argument work (gap M5).
- **No way to change materials:** nothing in VS-01 changes a role's `material_id`. That is also part of M5.
- The command's exact name and argument schema (for example `{role, section_id}`) are part of M5.
- Per-member overrides and user-authored members.
