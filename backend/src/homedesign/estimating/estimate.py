"""`preliminary_estimate` payload, builder, and money rounding (artifacts.md §8; EST-001 §4; ART-002 §7).

Timber lines are priced per meter of reference-axis length; connection lines per piece, one line per
connection type in use (D054). Both use one exact rounding rule, which is exact for integer counts.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from homedesign.dependencies.registry import Derivation, DerivationContext, Outcome
from homedesign.model.connections import ConnectionType
from homedesign.model.schema import MemberRole, SafeInt, Uuid
from homedesign.timber.schedule import Assumption

COST_INPUTS_MISSING = {"code": "COST_INPUTS_MISSING", "message": "Some or all unit prices are not configured; no complete total is reported."}


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


class PriceBookInfo(_Strict):
    price_book_id: Uuid
    price_book_version: int
    currency: Literal["USD"]
    as_of: str
    source: str
    geography: str


class TimberLine(_Strict):
    kind: Literal["timber"]
    key: str
    role: MemberRole
    nominal_section: str
    quantity_value: float
    quantity_unit: Literal["m"]
    unit_price_minor: SafeInt | None
    amount_minor: SafeInt | None
    priced: bool


class ConnectionLine(_Strict):
    kind: Literal["connection"]
    key: str
    connection_type: ConnectionType
    quantity_value: Annotated[SafeInt, Field(ge=1)]
    quantity_unit: Literal["each"]
    unit_price_minor: SafeInt | None
    amount_minor: SafeInt | None
    priced: bool


LineItem = Annotated[TimberLine | ConnectionLine, Field(discriminator="kind")]


class Totals(_Strict):
    priced_amount_minor: SafeInt | None
    unpriced_line_count: int
    grand_total_minor: SafeInt | None


class PreliminaryEstimatePayload(_Strict):
    model_config = ConfigDict(title="preliminary_estimate payload (artifacts.md §8)")

    coverage: Literal["none", "partial", "complete"]
    currency: Literal["USD"] | None
    price_book: PriceBookInfo | None
    line_items: list[LineItem]
    totals: Totals
    assumptions: list[Assumption]  # the schedule's, copied (ART-002 §7.2)


def amount_minor(unit_price_minor: int, quantity: float | int) -> int:
    """Exact product of an integer price and a double's exact binary value (or an integer count), rounded half-even."""
    exact = Decimal(unit_price_minor) * Decimal(quantity)  # Decimal(float) is exact
    return int(exact.to_integral_value(rounding=ROUND_HALF_EVEN))


def _utf16(text: str) -> bytes:
    return text.encode("utf-16-be")


def build_estimate(schedule: dict[str, Any], price_book: dict[str, Any] | None) -> tuple[str, dict[str, Any], tuple[dict, ...]]:
    """(status, payload, warnings) from a CURRENT schedule's `aggregates`, `connection_aggregates`, and
    `assumptions` (its selection, or the whole schedule payload) and the project's book row."""
    prices = {}
    if price_book is not None:
        prices = {row["key"]: row["unit_price_minor"] for row in price_book["book"]["rows"]}

    def pricing(key: str, quantity: float | int) -> dict[str, Any]:
        unit_price = prices.get(key)
        return {
            "unit_price_minor": unit_price,
            "amount_minor": None if unit_price is None else amount_minor(unit_price, quantity),
            "priced": unit_price is not None,
        }

    lines = []
    for aggregate in schedule["aggregates"]:
        key = f"timber.{aggregate['role']}.{aggregate['nominal_section']}"
        lines.append({
            "kind": "timber",
            "key": key,
            "role": aggregate["role"],
            "nominal_section": aggregate["nominal_section"],
            "quantity_value": aggregate["total_length_m"],
            "quantity_unit": "m",
            **pricing(key, aggregate["total_length_m"]),
        })
    per_type: dict[str, int] = {}
    for aggregate in schedule["connection_aggregates"]:  # one line per type in use (D054)
        per_type[aggregate["connection_type"]] = per_type.get(aggregate["connection_type"], 0) + aggregate["count"]
    for connection_type, count in per_type.items():
        key = f"connection.{connection_type}"
        lines.append({
            "kind": "connection",
            "key": key,
            "connection_type": connection_type,
            "quantity_value": count,
            "quantity_unit": "each",
            **pricing(key, count),
        })
    lines.sort(key=lambda line: _utf16(line["key"]))
    amounts = [line["amount_minor"] for line in lines if line["priced"]]
    unpriced = len(lines) - len(amounts)
    if price_book is None:
        coverage = "none"
    elif unpriced == 0:
        coverage = "complete"
    else:
        coverage = "partial"
    info = None
    if price_book is not None:
        book = price_book["book"]
        info = {"price_book_id": price_book["price_book_id"], "price_book_version": price_book["version"],
                "currency": book["currency"], "as_of": book["as_of"], "source": book["source"], "geography": book["geography"]}
    payload = {
        "coverage": coverage,
        "currency": None if coverage == "none" else info["currency"],
        "price_book": info,
        "line_items": lines,
        "totals": {
            "priced_amount_minor": sum(amounts) if amounts else None,
            "unpriced_line_count": unpriced,
            # Never 0 for missing inputs; only a complete book yields a grand total (artifacts.md §8.1).
            "grand_total_minor": sum(amounts) if coverage == "complete" else None,
        },
        "assumptions": [dict(a) for a in schedule["assumptions"]],
    }
    warnings: list[dict] = []
    if coverage in ("none", "partial"):
        warnings.append(COST_INPUTS_MISSING)
    unused = sorted(set(prices) - {line["key"] for line in lines}, key=_utf16)
    if unused:
        warnings.append({"code": "PRICE_ROWS_UNUSED", "message": "Price book rows match no line item: " + ", ".join(unused) + "."})
    status = "UNAVAILABLE" if coverage == "none" else "CURRENT"
    return status, PreliminaryEstimatePayload.model_validate(payload).model_dump(mode="json"), tuple(warnings)


def _external(tx, project_id: str) -> dict[str, Any]:
    row = tx.get_price_book(project_id)
    if row is None:
        return {"price_book": None}
    # artifacts.md §2.3: the fingerprint covers id, version, as_of, currency; "_book" is context only
    # (a version identifies its rows exactly, because versions are append-only).
    return {
        "price_book_id": row["price_book_id"],
        "price_book_version": row["version"],
        "as_of": row["book"]["as_of"],
        "currency": row["book"]["currency"],
        "_book": row,
    }


SCHEDULE_LISTS = ("aggregates", "connection_aggregates", "assumptions")  # what build_estimate reads (DEP-001 §4.2)


def select_estimate(upstream: Mapping[str, Outcome]) -> dict[str, Any]:
    """DEP-001 §4.2: the schedule's three lists, or null when the schedule is not CURRENT.

    Not the schedule's fingerprint: re-identifying a grid line changes schedule rows but not these
    lists, and then the estimate's payload does not change either.
    """
    schedule = upstream.get("timber_schedule")
    if schedule is None or schedule.status != "CURRENT" or schedule.payload is None:
        return {"timber_schedule": None}
    return {"timber_schedule": {key: schedule.payload[key] for key in SCHEDULE_LISTS}}


def _derive(context: DerivationContext) -> Outcome:
    status, payload, warnings = build_estimate(context.selection["timber_schedule"], context.external.get("_book"))
    return Outcome(status, payload, warnings)


ESTIMATE = Derivation(
    "preliminary_estimate", "estimate-vs01", "2", select_estimate, _derive, depends_on=("timber_schedule",), external_inputs=_external
)
