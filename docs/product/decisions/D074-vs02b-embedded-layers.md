# D074 — VS-02b layers live inside their assembly definition

**Status:** Confirmed (not yet implemented; [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-21  
**Scope:** How the version 3 model stores an assembly definition's layers. Approved as [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 item 2, within [D067](D067-vs02b-assembly-definitions.md) and [D071](D071-vs02b-thermal-moisture-values.md).  
**Settles:** the record layout that D067 left to MODEL-006 ("field names, detail codes, and record versions").

## Decision

- **`AssemblyDefinition.layers`** is an ordered list of `Layer` objects, exterior to interior, stored **inside** the definition. A layer is not a separate record kind and has no record ID.
- **Each layer has a `name`:** a slug (`^[a-z0-9]+(-[a-z0-9]+)*$`), unique within its definition. It is the `<layer>` token of the estimate key `assembly.<label>.<layer>` ([D070](D070-vs02b-quantities-and-outputs.md)), and the stable handle for a layer, as grid-line IDs are inside `TimberGrid` ([D042](D042-stable-grid-line-ids.md)).
- **Validation:** a repeated name is `DUPLICATE_LAYER_NAME` (stage 2). Error paths address a layer by position inside its definition (`entities[<definition id>].layers[2].thickness_m`; [D036](D036-error-path-syntax.md)).
- **The reserved kind name `Layer`** (building-model.md §3.2) names the object type. A separate `Layer` record kind is not used in VS-02b.

## Rationale

- Definitions are fixed in VS-02b (D067): a layer has no life apart from its definition, and nothing refers to a layer from outside it.
- Embedding needs no ownership rule (each layer in exactly one definition) and adds no records to the template.
- A unique `name` gives each layer a stable handle for the estimate key now and for layer-editing commands later, as grid lines have.

## Alternatives considered

- **`Layer` as its own record kind,** referenced by `layer_ids`: an ID per layer for future editing commands, at the cost of ownership rules and 7 more template records with no use in VS-02b. Layer editing can revisit this with its own decision.

## What this does not decide

The layer's property-value fields (MODEL-006 §13, item 3). The framing layer's fields and sections (items 4–5). User authoring or editing of definitions and layers, which stays deferred (D067).
