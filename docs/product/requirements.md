# Functional requirements

**Status:** Confirmed product intent; specific implementation boundaries are defined by vertical slice.

### FR-01 Project and revision management

Create, load, save, and version projects. Each revision has a stable identifier, timestamp, author/source, parent revision, operation log, and schema version. Undo/redo must preserve model consistency. Support branches for alternatives and a clear merge/accept workflow in later slices.

### FR-02 Unified semantic building model

Represent stories, levels, grids, rooms, walls, openings, slabs, roofs, foundations, structural members, connections, assemblies, materials, and building-system components with stable IDs, typed parameters, units, relationships, and validation rules. Store authoritative parametric definitions; derive CAD geometry, render meshes, analysis representations, and schedules.

### FR-03 2D and 3D interfaces

Support floor-plan editing and interactive 3D viewing against the same model. Changes in either interface become validated model operations. Measurements and dimensions are explicit, not inferred from display pixels.

### FR-04 Timber framing

Represent posts, beams, braces, joists, rafters, purlins, and girders with species/grade, section, position, orientation, connection references, and structural role. Support traditional joinery and engineered metal connectors as typed components, initially in a deliberately limited subset. Derive member schedules and fabrication information when supported.

### FR-05 Modular assemblies

Define reusable layered wall, roof, floor, and ceiling assemblies with thickness, material, quantities, thermal and moisture properties, installation requirements, and data provenance. Initial wall families include straw bale and dimensional-lumber stud infill. Flag unverified climate-specific details.

### FR-06 MEP coordination

Represent relevant plumbing, electrical, and HVAC fixtures/routes/clearances and identify geometric or design conflicts. Full automated trade design is not assumed for the MVP.

### FR-07 Structural analysis and review

For explicitly supported configurations, calculate and document loads, load paths, member checks, connections, and foundation reactions using validated methods. Unsupported cases return an explicit `unsupported` result, never a silent pass. Record analysis inputs, calculation engine version, assumptions, and result status. Professional review is a separate action by an authorized reviewer.

### FR-08 Cost and environmental impact

Estimate quantities and cost by category: materials, labor, subcontractors, site work, permits, and contingency, marking unavailable inputs. Model embodied carbon with transparent lifecycle boundaries and biogenic-carbon treatment, operational energy, lifecycle cost, waste, and durability where data supports it. Display ranges, confidence/provenance, and missing data; do not present invented precision.

### FR-09 Alternatives and optimization

Generate distinct, revision-linked alternatives and compare construction cost, embodied carbon, energy, and other goals. Start with side-by-side comparisons (lowest cost, lowest carbon, balanced); interactive objective sliders and advanced optimization follow later. Explain proposed changes, such as grouping plumbing fixtures or simplifying roofs. Validate real routing and quantities before asserting savings.

### FR-10 Construction outputs

Generate revision-stamped views, dimensioned drawings, preliminary timber member schedules, material takeoffs, cut lists, and engineering review packages as capabilities mature. Every output declares its completeness and suitability; preliminary documents must not be labeled permit-ready or construction-approved.

### FR-11 Collaboration and approval

Implement role-based access, comments, review records, and approvals bound to a model revision and relevant dependency scope. A change affecting an approved element must flag the approval as needing reevaluation; unrelated approvals should not be indiscriminately revoked.

### FR-12 Intelligent change propagation

Routine edits propagate automatically. Consequential edits require an impact preview and confirmation. Apply updates transactionally; recalculate or invalidate dependent derived artifacts. Never leave stale results appearing current.
