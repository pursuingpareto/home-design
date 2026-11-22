# D057 — VS-02 frame parameter command, and roof edits become consequential

**Status:** Confirmed (implemented in VS-02)  
**Date:** 2026-11-19  
**Scope:** The version 2 command additions and classification table. Approved from [MODEL-005](../../implementation/tasks/MODEL-005.md) §12, item 4.  
**Amends:**
- [D043](D043-vs01-command-set.md) (the command set): adds `SetFrameParameters`, and widens `SetMemberSection` to the version 2 roles;
- [dependencies.md §4.1](../../architecture/dependencies.md#41-classification-table-vs02b-change-classes-1): table `vs02-change-classes-1` replaces `vs01-change-classes-1`, and `SetGableRoofParameters` moves from routine to consequential.

## Decision

### `SetFrameParameters`

| `type` | `args` | Effect |
|---|---|---|
| `SetFrameParameters` | `{joist_spacing_m, purlins_per_slope, knee_brace_leg_m, knee_braces_level_1, knee_braces_eave}`, all required | Replaces `FrameSystem.parameters` and regenerates members. Members on surviving positions keep their keys and IDs (D042) |

- **One command for all five settings,** as `SetGableRoofParameters` covers pitch and overhang. Clients send stored values for the settings they do not change.
- **Errors** link each argument to its field (interfaces.md §7.1). Bounds and the brace-fit rule are in building-model.md §3.3.
- **Current values** are a no-op (D045).

### Existing commands under version 2

- `SetMemberSection` accepts all seven version 2 roles. `RAFTER` is no longer a role, so it is `INVALID_ENUM`.
- The other commands keep their arguments and regenerate more members.
- `SetConnectionType` is specified with `CONN-001`, which adds its row to the table below.

### Classification table `vs02-change-classes-1`

| Command | Class |
|---|---|
| `AddSection` | routine |
| `SetGableRoofParameters` | **consequential** (was routine) |
| `SetFrameParameters` | consequential |
| `SetFootprintDimensions`, `SetStoryHeights`, `SetTimberGrid`, `SetMemberSection`, `UndoToRevision`, `CreateReferenceProject` | consequential |

**Roof edits now need a preview and confirmation.** In VS-01 they were routine because `vs01-post-beam-1` ignored the roof. In version 2, the pitch places principal rafters and purlins ([D052](D052-vs02-frame-members.md)). The policy in dependencies.md §4 treats any roof change that regenerates framing as consequential. The browser's roof editor moves from apply-with-undo to the preview flow.

## Rationale

- **Conservative classification:** a change that regenerates structural members should not be committed without showing what changes. This also keeps the classification table consistent with its own stated policy.
- **One command per editor:** a single frame command fits the browser's existing editor pattern.

## Alternatives considered

Keeping roof edits routine. They would stay one click with undo, but members would regenerate without any preview. That contradicts dependencies.md §4.

## What this does not decide

- The connection-type command and its classification (`CONN-001`).
- A finer classification policy, for example treating small pitch changes as routine.
