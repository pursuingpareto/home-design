"""Price book model and validation (artifacts.md §8.2; EST-001 §5).

Errors use D035 codes with D036 paths relative to the book. As in snapshot validation, only
the earliest failing stage's issues are reported: shape and type (stage 1), duplicate row
keys and units that do not match their key family (stage 2, DUPLICATE_PRICE_KEY and
PRICE_UNIT_MISMATCH, ART-002 §7.3), then negative prices (stage 3, OUT_OF_RANGE).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import PydanticCustomError

from homedesign.model import codes
from homedesign.model.codes import Stage
from homedesign.model.paths import render
from homedesign.model.schema import SafeInt
from homedesign.model.validation import ValidationResult, _Collector, code_for_pydantic_error, message_for

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def _calendar_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise PydanticCustomError("invalid_timestamp", "as_of must be a valid ISO date.") from exc
    return value


IsoDate = Annotated[str, Field(pattern=DATE_PATTERN), AfterValidator(_calendar_date)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False, frozen=True)


# ART-002 §7.3: the unit each key family requires. Keys of other families take either unit and are unused.
UNIT_BY_FAMILY = {"timber.": "m", "connection.": "each"}


class PriceRow(_Strict):
    key: str
    unit: Literal["m", "each"]
    unit_price_minor: SafeInt  # non-negative: checked as OUT_OF_RANGE below


class PriceBook(_Strict):
    """A project's price book as submitted (book-level metadata, artifacts.md §8.2)."""

    model_config = ConfigDict(title="Price book (artifacts.md §8.2)")

    currency: Literal["USD"]
    as_of: IsoDate
    source: str
    geography: str
    rows: list[PriceRow]


def validate_price_book(value: Any) -> tuple[PriceBook | None, ValidationResult | None]:
    try:
        book = PriceBook.model_validate(value)
    except ValidationError as exc:
        out = _Collector()
        seen = set()
        for error in exc.errors(include_url=False):
            path = render(list(error["loc"]))
            code = code_for_pydantic_error(error)
            if error["type"] == "string_pattern_mismatch" and (error.get("ctx") or {}).get("pattern") == DATE_PATTERN:
                code = codes.INVALID_TIMESTAMP
            if (path, code) not in seen:
                seen.add((path, code))
                out.add(path, code, message_for(code), None if error["type"] == "missing" else error.get("input"))
        return None, out.result(Stage.SYNTACTIC)

    out = _Collector()
    first: dict[str, int] = {}
    for k, row in enumerate(book.rows):
        if row.key in first:
            out.add(f"rows[{k}].key", codes.DUPLICATE_PRICE_KEY, "Price book row keys must be unique.", row.key, [f"rows[{first[row.key]}].key"])
        else:
            first[row.key] = k
        for prefix, unit in UNIT_BY_FAMILY.items():
            if row.key.startswith(prefix) and row.unit != unit:
                out.add(f"rows[{k}].unit", codes.PRICE_UNIT_MISMATCH, f"A row whose key starts with {prefix!r} must use unit {unit!r}.", row.unit, [f"rows[{k}].key"])
    if (result := out.result(Stage.REFERENTIAL)) is not None:
        return None, result

    out = _Collector()
    for k, row in enumerate(book.rows):
        if row.unit_price_minor < 0:
            out.add(f"rows[{k}].unit_price_minor", codes.OUT_OF_RANGE, "Unit prices must not be negative.", row.unit_price_minor)
    if (result := out.result(Stage.GEOMETRIC)) is not None:
        return None, result
    return book, None
