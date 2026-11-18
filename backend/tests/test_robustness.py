"""Never-raises and determinism properties (MODEL-001 §7.4)."""

from __future__ import annotations

import copy
import json
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from conftest import FIXTURE, FIXTURE_BYTES
from homedesign.model import codes, validate_bytes, validate_value
from homedesign.model.validation import ValidationResult

json_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=True, allow_infinity=True)
    | st.text(max_size=12)
)
json_values = st.recursive(
    json_scalars,
    lambda children: st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=8), children, max_size=4),
    max_leaves=24,
)


def _paths(value: Any, prefix: tuple = ()) -> list[tuple]:
    found = [prefix]
    if isinstance(value, dict):
        for key, child in value.items():
            found += _paths(child, (*prefix, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found += _paths(child, (*prefix, index))
    return found


FIXTURE_PATHS = [p for p in _paths(FIXTURE) if p]


def _check_invariants(result: ValidationResult) -> None:
    assert isinstance(result, ValidationResult)
    assert result.valid == (result.code is None) == (not result.issues)
    for issue in result.issues:
        assert issue.code in codes.CATALOG
        assert codes.CATALOG[issue.code].top_level_code == result.code
        assert isinstance(issue.path, str)
    json.dumps(result.to_dict(), allow_nan=False)  # result itself is serializable I-JSON


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(json_values)
def test_arbitrary_values_never_raise(value):
    _check_invariants(validate_value(value))


@settings(max_examples=300)
@given(st.binary(max_size=256))
def test_arbitrary_bytes_never_raise(data):
    _check_invariants(validate_bytes(data))


@settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
@given(st.sampled_from(FIXTURE_PATHS), json_values | st.just("<delete>"))
def test_random_fixture_mutations_never_raise(path, replacement):
    doc = copy.deepcopy(FIXTURE)
    parent = doc
    for step in path[:-1]:
        parent = parent[step]
    if replacement == "<delete>":
        if isinstance(parent, dict):
            del parent[path[-1]]
        else:
            parent.pop(path[-1])
    else:
        parent[path[-1]] = replacement
    result = validate_value(doc)
    _check_invariants(result)
    assert validate_value(doc).to_dict() == result.to_dict()  # deterministic


def test_repeated_validation_is_byte_identical():
    first = json.dumps(validate_bytes(FIXTURE_BYTES).to_dict(), sort_keys=True)
    second = json.dumps(validate_bytes(FIXTURE_BYTES).to_dict(), sort_keys=True)
    assert first == second
