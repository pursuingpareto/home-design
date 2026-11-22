"""D071's thermal figures, method ``parallel-path-1`` (ART-003 §4.8; D084).

A pure module: it takes a definition as the assembly schedule prints it (§4.5) and its walls' framing
fractions and net areas, and returns the figures. A later method version is a new function behind the
same output. Every value is evaluated exactly as written, in IEEE-754 doubles.

- Layer resistances: ``thickness / k`` with a declared conductivity, or the declared resistance's value.
  The framing layer has two: through the fill (its own conductivity) and through the framing (the framing
  material's conductivity). Unknown when the value it needs is null.
- ``R_fill`` and ``R_framing`` sum every layer's resistance, exterior to interior, with the framing layer at
  its fill or framing value. No surface air films are added (D084).
- Per wall: ``U = f / R_framing + (1 - f) / R_fill``, ``r = 1 / U``, ``ua = U * net_area``.
- Per definition and for all walls: ``ua`` summed over the walls in row order, ``u = ua / net``, ``r = 1 / u``.
- Gating is by input, not by wall: a figure is null unless every input it uses is known, and the missing
  inputs are named. A wall with no framing (``f = 0``) still needs ``R_framing``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

METHOD_ID = "parallel-path-1"
NOTES = (
    "Parallel-path method: the framing fraction comes from the generated wall framing.",
    "Heavy-timber frame members in the wall plane, air leakage, and moisture effects are not included.",
    "Surface air films are not included.",
    "Opaque walls only: no roof, floor, door, or window values, and no whole-envelope or heat-loss figure.",
    "Declared values, not verified. Not a code-compliance calculation.",
)

LAYER_FIELDS = ["thermal_conductivity_w_m_k", "thermal_resistance_m2_k_w"]  # either supplies a non-framing layer
FILL_FIELDS = ["thermal_conductivity_w_m_k"]
FRAMING_FIELDS = ["framing.framing_thermal_conductivity_w_m_k"]


def _value(declared: dict[str, Any] | None) -> float | None:
    return None if declared is None else declared["value"]


@dataclass
class Paths:
    """A definition's two path resistances and what each one lacks."""

    label: str
    r_fill: float | None
    r_framing: float | None
    missing_fill: list[dict[str, Any]] = field(default_factory=list)
    missing_framing: list[dict[str, Any]] = field(default_factory=list)
    missing_all: list[dict[str, Any]] = field(default_factory=list)  # the union, in build-up order


def path_resistances(definition: dict[str, Any]) -> Paths:
    """``R_fill`` and ``R_framing`` for one definition (its ``label`` and ``layers``, as §4.5 prints them)."""
    label = definition["label"]
    r_fill: float | None = 0.0
    r_framing: float | None = 0.0
    paths = Paths(label, None, None)

    def missing(layer: dict[str, Any], fields: list[str]) -> dict[str, Any]:
        return {"assembly_label": label, "layer": layer["name"], "fields": list(fields)}

    for layer in definition["layers"]:  # exterior to interior
        framing = layer["framing"]
        if framing is None:
            k = _value(layer["thermal_conductivity_w_m_k"])
            r = layer["thickness_m"] / k if k is not None else _value(layer["thermal_resistance_m2_k_w"])
            if r is None:
                entry = missing(layer, LAYER_FIELDS)
                paths.missing_fill.append(entry)
                paths.missing_framing.append(entry)
                paths.missing_all.append(entry)
                r_fill = r_framing = None
            else:
                r_fill = None if r_fill is None else r_fill + r
                r_framing = None if r_framing is None else r_framing + r
            continue
        k_fill = _value(layer["thermal_conductivity_w_m_k"])
        if k_fill is None:
            entry = missing(layer, FILL_FIELDS)
            paths.missing_fill.append(entry)
            paths.missing_all.append(entry)
            r_fill = None
        elif r_fill is not None:
            r_fill = r_fill + layer["thickness_m"] / k_fill
        k_framing = _value(framing["framing_thermal_conductivity_w_m_k"])
        if k_framing is None:
            entry = missing(layer, FRAMING_FIELDS)
            paths.missing_framing.append(entry)
            paths.missing_all.append(entry)
            r_framing = None
        elif r_framing is not None:
            r_framing = r_framing + layer["thickness_m"] / k_framing
    paths.r_fill, paths.r_framing = r_fill, r_framing
    return paths


def wall_figures(paths: Paths, framing_fraction: float, net_area_m2: float) -> dict[str, float | None]:
    """A wall's parallel-path ``u_value_w_m2_k``, ``r_value_m2_k_w``, and ``ua_w_k``, or nulls."""
    if paths.r_fill is None or paths.r_framing is None:
        return {"u_value_w_m2_k": None, "r_value_m2_k_w": None, "ua_w_k": None}
    f = framing_fraction
    u = f / paths.r_framing + (1 - f) / paths.r_fill
    return {"u_value_w_m2_k": u, "r_value_m2_k_w": 1 / u, "ua_w_k": u * net_area_m2}


def _path_figure(r: float | None, missing: list[dict[str, Any]]) -> dict[str, Any]:
    return {"r_value_m2_k_w": r, "u_value_w_m2_k": None if r is None else 1 / r, "missing_inputs": [dict(m) for m in missing]}


def area_weighted(walls: Sequence[dict[str, Any]], missing: list[dict[str, Any]]) -> dict[str, Any]:
    """Area-weighted figures over wall rows (in row order): ``ua`` summed, ``u = ua / net``, ``r = 1 / u``."""
    net = 0.0
    for wall in walls:
        net += wall["net_area_m2"]
    ua: float | None = None
    if walls and all(wall["ua_w_k"] is not None for wall in walls):
        ua = 0.0
        for wall in walls:
            ua += wall["ua_w_k"]
    u = None if ua is None else ua / net
    return {
        "net_area_m2": net,
        "ua_w_k": ua,
        "u_value_w_m2_k": u,
        "r_value_m2_k_w": None if u is None else 1 / u,
        "missing_inputs": [] if ua is not None else [dict(m) for m in missing],
    }


def thermal_section(paths_by_label: dict[str, Paths], definitions: Sequence[dict[str, Any]], walls: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """The payload's ``thermal`` object, given the wall rows with their figures filled in."""
    entries = []
    union: list[dict[str, Any]] = []
    for definition in definitions:  # sorted by label
        label = definition["label"]
        paths = paths_by_label[label]
        own = [w for w in walls if w["assembly_label"] == label]
        entries.append({
            "assembly_label": label,
            "center_of_cavity": _path_figure(paths.r_fill, paths.missing_fill),
            "framing_path": _path_figure(paths.r_framing, paths.missing_framing),
            "parallel_path": area_weighted(own, paths.missing_all),
        })
        union.extend(paths.missing_all)
    return {
        "method": {"id": METHOD_ID, "notes": list(NOTES)},
        "definitions": entries,
        "all_walls": area_weighted(walls, union),
    }
