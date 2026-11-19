"""TEST-001 §5–§6: the Reference House 001 scenario on both stores, matching the golden record."""

from __future__ import annotations

import json

from integration.scenario import GOLDEN_PATH, render, run_scenario


def test_reference_house_scenario_matches_golden(store):
    data = run_scenario(store)
    golden = GOLDEN_PATH.read_text(encoding="utf-8") if GOLDEN_PATH.exists() else ""
    assert render(data) == golden, (
        "The scenario's output differs from tests/vectors/scenarios/reference-house-001.json. If the change is intended, "
        "regenerate with `uv run python tests/integration/golden.py`, review the diff, and record why (TEST-001 §6)."
    )
    assert [s["step"] for s in json.loads(golden)["steps"]][:2] == ["create", "price-book"]
