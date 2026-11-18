"""RFC 8785 JSON Canonicalization Scheme (D029).

Numbers are serialized with the ECMAScript Number-to-String algorithm, strings with
ECMAScript JSON.stringify escaping, and object keys are sorted by UTF-16 code units.
Correctness is checked against vectors produced by an independent ECMAScript engine
(tests/vectors/jcs/).
"""

from __future__ import annotations

import json
import math
from typing import Any


class CanonicalizationError(ValueError):
    """The value is not I-JSON and cannot be canonicalized."""


def canonical_json(value: Any) -> bytes:
    """Return the RFC 8785 canonical UTF-8 bytes for an I-JSON value.

    Accepts None, bool, int, float, str, list/tuple, and dict with str keys.
    Raises CanonicalizationError for non-finite numbers, lone surrogates,
    non-string keys, or unsupported types.
    """
    parts: list[str] = []
    _write(value, parts)
    return "".join(parts).encode("utf-8")


def _write(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        try:
            as_float = float(value)
        except OverflowError as exc:
            raise CanonicalizationError("integer too large for an IEEE-754 double") from exc
        out.append(format_number(as_float))
    elif isinstance(value, float):
        out.append(format_number(value))
    elif isinstance(value, str):
        out.append(_format_string(value))
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for index, item in enumerate(value):
            if index:
                out.append(",")
            _write(item, out)
        out.append("]")
    elif isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError("object keys must be strings")
            _check_well_formed(key)
        out.append("{")
        for index, key in enumerate(sorted(value, key=_utf16_sort_key)):
            if index:
                out.append(",")
            out.append(_format_string(key))
            out.append(":")
            _write(value[key], out)
        out.append("}")
    else:
        raise CanonicalizationError(f"unsupported type: {type(value).__name__}")


def _utf16_sort_key(key: str) -> bytes:
    # Big-endian UTF-16 byte order equals UTF-16 code-unit order (RFC 8785 §3.2.3).
    return key.encode("utf-16-be")


def _check_well_formed(text: str) -> None:
    for char in text:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise CanonicalizationError("string contains a lone surrogate (not I-JSON)")


def _format_string(text: str) -> str:
    _check_well_formed(text)
    # For well-formed strings, Python's escaping with ensure_ascii=False matches
    # ECMAScript JSON.stringify: \b \f \n \r \t \" \\ short forms, other C0 controls as
    # lowercase \u00xx, everything else literal.
    return json.dumps(text, ensure_ascii=False)


def format_number(number: float) -> str:
    """ECMAScript Number::toString for a finite double (RFC 8785 §3.2.2.3)."""
    if not math.isfinite(number):
        raise CanonicalizationError("non-finite numbers are not I-JSON")
    if number == 0:
        return "0"  # covers -0
    sign = "-" if number < 0 else ""
    # Python's repr yields the shortest round-tripping digits, choosing the closest
    # when several exist, which is the digit string ECMAScript requires.
    text = repr(abs(number))
    mantissa, _, exponent_text = text.partition("e")
    exponent = int(exponent_text) if exponent_text else 0
    integer_part, _, fraction_part = mantissa.partition(".")
    raw_digits = integer_part + fraction_part
    stripped = raw_digits.lstrip("0")
    leading_zeros = len(raw_digits) - len(stripped)
    # value = 0.d1d2...dk × 10^n
    n = len(integer_part) + exponent - leading_zeros
    digits = stripped.rstrip("0")
    k = len(digits)
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        exponent_part = ("+" if e >= 0 else "-") + str(abs(e))
        body = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + exponent_part
    return sign + body
