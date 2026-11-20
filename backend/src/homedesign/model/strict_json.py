"""Strict JSON parsing for untrusted snapshot input (MODEL-001 §5.1).

The standard library parser is configured so that it never silently accepts
duplicate keys, NaN/Infinity tokens, or literals that overflow a double. Instead of
failing immediately, such values are marked in the parsed tree so that the
validator can report every problem with a precise path.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from . import codes
from .limits import DEFAULT_MAX_BYTES, DEFAULT_MAX_DEPTH

_MAX_DOUBLE = 1.7976931348623157e308


class NonFinite:
    """Placeholder for a NaN/Infinity token or an overflowing numeric literal."""

    __slots__ = ("literal",)

    def __init__(self, literal: str) -> None:
        self.literal = literal

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"NonFinite({self.literal!r})"


class DuplicateKeyDict(dict):
    """A JSON object in which at least one key appeared more than once.

    Behaves like the standard parser's result (the last value wins) and records
    the duplicated keys for reporting.
    """

    duplicate_keys: tuple[str, ...]


@dataclass(frozen=True)
class FatalParseError:
    """A problem that prevents any further validation."""

    code: str
    message: str


@dataclass(frozen=True)
class ParseOutcome:
    value: Any = None
    fatal: FatalParseError | None = None


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    seen: set[str] = set()
    duplicates: list[str] = []
    for key, _ in pairs:
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
    if not duplicates:
        return dict(pairs)
    result = DuplicateKeyDict(pairs)
    result.duplicate_keys = tuple(duplicates)
    return result


def _parse_float(literal: str) -> float | NonFinite:
    number = float(literal)
    return number if math.isfinite(number) else NonFinite(literal)


def _parse_int(literal: str) -> int | NonFinite:
    try:
        number = int(literal)
    except ValueError:  # exceeds Python's integer string-conversion limit
        return NonFinite(literal)
    return number if abs(number) <= _MAX_DOUBLE else NonFinite(literal)


def parse(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> ParseOutcome:
    """Parse UTF-8 JSON bytes strictly. Never raises."""
    if len(data) > max_bytes:
        return ParseOutcome(
            fatal=FatalParseError(
                codes.PAYLOAD_LIMIT_EXCEEDED, f"Input exceeds the {max_bytes}-byte limit."
            )
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ParseOutcome(fatal=FatalParseError(codes.MALFORMED_JSON, "Input is not valid UTF-8."))
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_float=_parse_float,
            parse_int=_parse_int,
            parse_constant=NonFinite,
        )
    except RecursionError:
        return ParseOutcome(
            fatal=FatalParseError(
                codes.PAYLOAD_LIMIT_EXCEEDED, f"Input is nested more than {max_depth} levels deep."
            )
        )
    except ValueError as exc:  # json.JSONDecodeError is a ValueError
        return ParseOutcome(fatal=FatalParseError(codes.MALFORMED_JSON, f"Input is not valid JSON: {exc}"))
    depth_error = check_depth(value, max_depth)
    if depth_error is not None:
        return ParseOutcome(fatal=depth_error)
    return ParseOutcome(value=value)


def check_depth(value: Any, max_depth: int) -> FatalParseError | None:
    """Iteratively check container nesting depth (the root container is depth 1)."""
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict):
            children = node.values()
        elif isinstance(node, (list, tuple)):
            children = node
        else:
            continue
        if depth > max_depth:
            return FatalParseError(
                codes.PAYLOAD_LIMIT_EXCEEDED, f"Input is nested more than {max_depth} levels deep."
            )
        stack.extend((child, depth + 1) for child in children)
    return None
