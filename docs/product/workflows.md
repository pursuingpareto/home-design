# Users and workflows

## Roles

- **Homeowner:** Express goals, edit designs, explore alternatives, inspect budget and environmental effects.
- **Builder/carpenter:** Inspect geometry and framing, obtain drawings, timber schedules, takeoffs, and cut lists.
- **Architect/designer:** Refine and coordinate architecture and review revisions.
- **Structural engineer:** Inspect assumptions, analyses, and structural details; record review against exact revisions.
- **Trade specialist:** Review relevant plumbing, electrical, HVAC coordination and conflicts.
- **Project administrator:** Manage participants, permissions, revisions, and review workflow.

Roles are configurable, a person may hold multiple roles, and authorization is enforced on the server. Real-time simultaneous editing is deferred.

## End-to-end workflows

1. User describes a house in natural language: spaces, aesthetics, site, budget, sustainability goals.
2. System captures those goals as editable structured design requirements.
3. User and AI collaborate using synchronized 2D, 3D, and conversational interactions.
4. System models timber framing, connections, assemblies, and building-system coordination.
5. System analyzes supported structural configurations, calculates quantities, estimates costs and environmental impacts, and flags unknowns.
6. System proposes alternative designs with comparative consequences; user explicitly selects changes.
7. Builder and professionals review revision-specific information and produce appropriate documentation.

**AI modes:** assistant (advice only), collaborator (default; proposed edits), generative designer (larger alternatives). All AI changes pass through the same typed operations and validation as manual edits.
