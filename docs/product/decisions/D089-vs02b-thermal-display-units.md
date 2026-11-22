# D089 — VS-02b browser: thermal figures follow the units switch

**Status:** Confirmed; implemented in VS-02b by [UI-004](../../implementation/tasks/UI-004.md) (2026-11-22)  
**Date:** 2026-11-22  
**Scope:** The units the browser uses to show the assembly schedule's thermal figures and declared thermal values. Approved as [UI-004](../../implementation/tasks/UI-004.md) §15 item 3.  
**Applies:** [D071](D071-vs02b-thermal-moisture-values.md)'s figures, served in SI ([D026](D026-canonical-units-identity-persistence.md)); the per-browser units preference ([UI-001](../../implementation/tasks/UI-001.md) §7).

## Decision

- **Metric** shows the figures as served: U in W/(m²·K), R in m²·K/W, and conductivity in W/(m·K).
- **Imperial** shows U in Btu/(h·ft²·°F), R in h·ft²·°F/Btu, and declared conductivities in Btu·in/(h·ft²·°F). These use the IT Btu: 1 m²·K/W = 5.678263 h·ft²·°F/Btu (so 1 W/(m²·K) = 0.17611 Btu/(h·ft²·°F)), and 1 W/(m·K) = 6.933472 Btu·in/(h·ft²·°F).
- **Display only,** like lengths and areas. Payloads, stored values, and every computation stay in SI. Area-weighted UA is shown in W/K (metric) or Btu/(h·°F) (imperial).
- **Every figure shows its unit.** No figure is shown as a bare "R-20". An unknown figure reads "Not computed", never 0 (D071).
- **Vapor permeances stay in SI** in both systems: moisture values are recorded only (D071).

## Rationale

- North American builders and homeowners read R-values in imperial units, and the figure is the one D071 asked to stand out.
- The units switch already decides how every other quantity is shown, so one preference governs the whole page.
- Always showing the unit avoids mixing up imperial R and RSI.

## Alternatives considered

- **SI always,** as served: no conversion, but imperial users read the key figure in unfamiliar units.
- **Both side by side:** independent of the switch, but every figure appears twice in a wide table.

## What this does not decide

Any figure's method or value (D071, D084). Rounding of displayed figures (UI-004, routine). Any energy-code or compliance claim (AC-08).
