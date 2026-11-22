# D075 — VS-02b declared property values: three nullable fields per layer, each with its own provenance

**Status:** Confirmed (not yet implemented; [MODEL-006](../../implementation/tasks/MODEL-006.md))  
**Date:** 2026-11-21  
**Scope:** How a version 3 layer records the declared thermal and vapor values of [D071](D071-vs02b-thermal-moisture-values.md). Approved as [MODEL-006](../../implementation/tasks/MODEL-006.md) §13 item 3, within D071 and [D074](D074-vs02b-embedded-layers.md).  
**Settles:** the field shapes that D071 left to MODEL-006 and ART-003 ("field names, payload shapes, and numeric rules").

## Decision

- **Three fields on every layer,** each a `DeclaredValue` or `null`:
  - `thermal_conductivity_w_m_k`: W/(m·K);
  - `thermal_resistance_m2_k_w`: m²·K/W;
  - `vapor_permeance_kg_pa_s_m2`: kg/(Pa·s·m²).

  The unit is fixed by the field name, in SI ([D026](D026-canonical-units-identity-persistence.md)).
- **`DeclaredValue`** is `{value, source, date, note}`: `value` a number, `source` a string, `date` an RFC 3339 full date (`YYYY-MM-DD`), and `note` a string or `null`. Each value carries its own provenance, so two values of one layer can come from different sources.
- **Unknown is `null`, never 0** (D071). A declared conductivity or resistance must be greater than 0. A permeance may be 0 (a perfect vapor barrier), but not negative.
- **Conductivity or resistance:** a layer declares at most one of the two thermal fields. A resistance records a product rated as a whole, such as a bale rated per thickness. Its layer's path resistance is that value; a conductivity's is the thickness divided by it.
- **The framing layer declares conductivities only:** its fill's on the layer (`thermal_conductivity_w_m_k`), and its framing material's in `framing.framing_thermal_conductivity_w_m_k`. D071 computes its two paths from them over the layer's thickness, so a resistance there is rejected.
- **Validation:** a bad date is `INVALID_DATE` (stage 1); a non-positive conductivity or resistance, or a negative permeance, is `OUT_OF_RANGE` (stage 3); both thermal fields set, or a resistance on the framing layer, is `UNSUPPORTED_VALUE` (stage 4).
- **Reference House 001 v3:** every value is `null` ([D072](D072-reference-house-001-v3-design-intent.md)).

## Rationale

- D071 names "a conductivity or a resistance"; recording both kinds keeps rated products expressible without converting through an invented thickness.
- Per-value provenance matches D071's "each with provenance", and keeps a mixed-source layer honest.
- Units in field names follow the model's existing style (`width_m`, `pitch_rad`), so no unit field can disagree with its value.

## Alternatives considered

- **Conductivity only:** simpler, but it cannot record a product's rated resistance.
- **One provenance per layer for all its values:** shorter, but it cannot say that two values came from different sources.

## What this does not decide

Any value itself, which stays `null` until supplied with a source (open question 6). How `ART-003` presents the values and the D071 figures. No value or figure claims energy-code or moisture performance (AC-08).
