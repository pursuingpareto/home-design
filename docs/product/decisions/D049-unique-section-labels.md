# D049 — Section labels are unique within a project

**Status:** Confirmed  
**Date:** 2026-11-19  
**Scope:** `Section.nominal_label` in semantic snapshots, the `AddSection` command, and the keys of schedule aggregates, estimate lines, and price-book rows. Chosen during review of [EST-001](../../implementation/tasks/EST-001.md) §7, item 3.  
**Amends:** [D043](D043-vs01-command-set.md) (the `AddSection` contract said labels need not be unique). Makes a narrow exception to [D026](D026-canonical-units-identity-persistence.md)'s "names are not identifiers".

## Problem

The confirmed schedule and estimate DTOs ([D027](D027-vs01-artifact-dtos.md)) aggregate and price timber by `role` + `nominal_section`, for example `timber.POST.8x8`. `AddSection` allowed duplicate labels, so two different sections both labelled "8x8" would have merged into one schedule line and one price.

## Decision

- **Uniqueness:** within a snapshot, every `Section.nominal_label` must be unique. The comparison is exact and case-sensitive, with no trimming or normalization, so `8x8` and `8X8` are different labels.
- **Snapshot rule:** a duplicate is the new stage-2 detail code **`DUPLICATE_SECTION_LABEL`** (`VALIDATION_FAILED`). It applies to every snapshot, whichever command produced it, including `UndoToRevision`.
- **Error paths (D036, D037 mapping):** the records are ordered by `id`, as for `DUPLICATE_GENERATION_KEY`. Every section after the first is reported with `path` = its `nominal_label`, and `related_paths` = the first section's `nominal_label`.
- **`AddSection`:** adding a section whose label already exists is rejected through candidate validation. Through the argument-to-field mapping (interfaces.md §7.1), `args.nominal_label` appears in `related_paths`.
- **Keys:** schedule aggregates stay keyed by (`role`, `nominal_section`), and estimate and price-book keys stay `timber.<ROLE>.<nominal_label>`, exactly as D027 confirmed. Because labels are unique, each key identifies exactly one section.

## The exception to D026

D026 says names are not identifiers, and entity identity remains the opaque UUID. A section's label is now also a **natural key** in one place only: aggregate, estimate-line, and price-book keys, which people read and write. References between records still use section IDs.

## Consequences

- **No migration:** Reference House 001 already complies (`8x8`, `8x12`), so no fixture or schema change is needed.
- **No relabeling:** VS-01 has no command that changes a label. A future relabel command must decide how existing price-book rows follow the change, because they are keyed by label.

## Rejected alternative

Keying aggregates and prices by section ID (`timber.POST.<uuid>`): labels could repeat, but keys would be unreadable in price books, and the D027 example keys would change.
