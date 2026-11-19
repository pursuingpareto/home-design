"""Regenerate or check the golden scenario record (TEST-001 §6).

Usage (from backend/):
    uv run python tests/integration/golden.py          # write tests/vectors/scenarios/reference-house-001.json
    uv run python tests/integration/golden.py --check  # exit 1 if it is stale
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/tests, for api_support and integration
warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient` is deprecated")

from homedesign.project import MemoryStore  # noqa: E402
from integration.scenario import GOLDEN_PATH, render, run_scenario  # noqa: E402


def main(argv: list[str]) -> int:
    text = render(run_scenario(MemoryStore()))
    if "--check" in argv:
        current = GOLDEN_PATH.read_text(encoding="utf-8") if GOLDEN_PATH.exists() else ""
        if current != text:
            print(f"{GOLDEN_PATH} is out of date; run without --check, review the diff, and commit it.", file=sys.stderr)
            return 1
        return 0
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {GOLDEN_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
