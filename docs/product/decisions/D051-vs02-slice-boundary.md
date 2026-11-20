# D051 — VS-02 slice boundary: complete frame with connections

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** What VS-02 delivers, and what moves to the next slice. Chosen as Option 1 of the [VS-02 scope proposal](../../implementation/acceptance-tests/vs-02.md) §3.  
**Amends:** the [roadmap](../../implementation/roadmap.md) VS-02 line. Assemblies move to a new slice, VS-02b, which follows VS-02.

## Decision

VS-02 delivers three of the roadmap's four VS-02 themes:

- **A. Complete frame:** additional generated framing members beyond posts and beams, from a new generation rule version. Which roles and parameters is decision 2 of the proposal.
- **B. Connections:** typed `Connection` records at member intersections, from a deliberately small catalog (D007, FR-04, open question 4). They have no capacity or adequacy claims.
- **D. Dependency propagation, the selector part only:** each artifact declares its inputs, so impact previews and staleness cover only affected artifacts. An asynchronous worker is not part of VS-02 unless a derivation becomes too slow to run synchronously.

**Moved to VS-02b:** layered assemblies (FR-05, D008: straw bale and stud infill first), with walls and openings as needed. VS-02b builds on VS-02's completed frame and connections.

**Unchanged:** everything stays preliminary (AC-08). Structural analysis remains VS-04.

## Rationale

- Infill walls and roof assemblies attach to members that VS-01 does not generate yet: joists, rafters, girts, and sills. Placing assemblies first would mean redefining their placement when the frame grows.
- Connections are only meaningful once the full set of member intersections exists.
- Selectors become worthwhile as soon as different artifacts depend on different inputs, and they make previews more honest (FR-12).
- The cost: the homeowner-facing straw-bale cost and comfort story (D008) arrives one slice later, in VS-02b.

## Alternatives considered

- **Option 2, a thin slice of all four themes:** shallow parts, likely to be redone.
- **Option 3, envelope first:** fastest to the homeowner story, but wall placement would be defined against a frame about to change.

## What this does not decide

Which frame roles and parameters, Reference House 001 v2 design values, the connection catalog, schema migration, and selector granularity. These are the proposal's decisions 2–6.
