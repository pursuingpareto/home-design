"""RFC 8785 conformance (D029; MODEL-001 §7.3)."""

from __future__ import annotations

import json
import math
import random
import struct

import pytest
from hypothesis import given
from hypothesis import strategies as st

from conftest import VECTORS_PATH
from homedesign.model import CanonicalizationError, canonical_json, fingerprint
from homedesign.model.jcs import format_number

VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("vector", VECTORS["documents"], ids=lambda v: v["name"])
def test_document_vectors(vector):
    value = json.loads(vector["input"])
    canonical = canonical_json(value)
    assert canonical == vector["canonical"].encode("utf-8")
    assert fingerprint(value) == vector["fingerprint"]


@pytest.mark.parametrize("vector", VECTORS["numbers"], ids=lambda v: v["ieee_hex"])
def test_rfc8785_number_vectors(vector):
    (number,) = struct.unpack(">d", bytes.fromhex(vector["ieee_hex"]))
    assert format_number(number) == vector["canonical"]


def test_vectors_cover_required_cases():
    names = {v["name"] for v in VECTORS["documents"]}
    assert {"rfc8785-3.2.2-sample", "rfc8785-3.2.3-sorting", "reference-house-001-doubles"} <= names
    edge = json.loads(next(v for v in VECTORS["documents"] if v["name"] == "number-edge-cases")["input"])
    assert 9007199254740991 in edge and 1.0 in edge  # 2^53 - 1 and 1.0 (MODEL-001 §7.3)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -float("inf"), {"k": float("nan")}, "\ud800", {"\udc00": 1}, {1: "x"}, object(), 10**400],
)
def test_rejects_non_i_json(value):
    with pytest.raises(CanonicalizationError):
        canonical_json(value)


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_float_round_trip(number):
    text = canonical_json(number).decode()
    # JCS numbers are read back as IEEE-754 doubles (an integral spelling such as
    # "35781631049747990" must still denote the same double).
    assert float(json.loads(text)) == number
    if number == 0:
        assert text == "0"  # -0 serializes as 0
    assert not math.isnan(float(text))


@given(st.integers(min_value=-(2**53 - 1), max_value=2**53 - 1))
def test_safe_integers_are_exact(number):
    assert canonical_json(number) == str(number).encode()


@given(st.dictionaries(st.text(), st.integers(min_value=-1000, max_value=1000), max_size=12), st.randoms())
def test_key_order_independent(mapping, rnd: random.Random):
    items = list(mapping.items())
    rnd.shuffle(items)
    assert canonical_json(dict(items)) == canonical_json(mapping)
