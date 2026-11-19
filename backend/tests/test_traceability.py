"""TEST-001 §4: the VS-01 traceability matrix is complete, and every test it names exists."""

from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import REPO_ROOT

MATRIX = REPO_ROOT / "docs" / "implementation" / "acceptance-tests" / "vs-01-traceability.md"
DOCS = REPO_ROOT / "docs"


def _section(path: Path, start: str, end: str) -> str:
    text = path.read_text(encoding="utf-8")
    begin = text.index(start)
    return text[begin : text.index(end, begin + len(start))]


def source_ids() -> set[str]:
    """IDs implied by the five source lists, so a criterion added there must be mapped here."""
    ac = re.findall(r"\*\*AC-(\d\d):\*\*", (DOCS / "implementation/acceptance-tests/vs-01.md").read_text(encoding="utf-8"))
    bm = re.findall(r"^(\d+)\. ", _section(DOCS / "architecture/building-model.md", "## 9. VS-01 model acceptance tests", "\n## "), re.M)
    dep_rows = [line for line in _section(DOCS / "architecture/dependencies.md", "## 8. VS-01 examples and tests", "\n## ").splitlines() if line.startswith("|")][2:]
    art = re.findall(r"^(\d+)\. ", _section(DOCS / "architecture/artifacts.md", "## 10. Acceptance tests", "\n## "), re.M)
    itf = re.findall(r"^(\d+)\. ", _section(DOCS / "architecture/interfaces.md", "## 9. Contract test matrix", "\n## "), re.M)
    return (
        {f"AC-{n}" for n in ac}
        | {f"BM-{n}" for n in bm}
        | {f"DEP-{k}" for k in range(1, len(dep_rows) + 1)}
        | {f"ART-{n}" for n in art}
        | {f"IF-{n}" for n in itf}
    )


def matrix_rows() -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\| ((?:AC|BM|DEP|ART|IF)-\d+) \| [^|]+ \| (.+) \|$", line)
        if match:
            assert match.group(1) not in rows, f"duplicate row {match.group(1)}"
            rows[match.group(1)] = match.group(2)
    return rows


def reference_exists(ref: str) -> bool:
    if "::" in ref:
        path, name = ref.split("::", 1)
        file = REPO_ROOT / path
        return file.exists() and re.search(rf"^def {re.escape(name)}\(", file.read_text(encoding="utf-8"), re.M) is not None
    if ".json#" in ref:
        path, script = ref.split("#", 1)
        file = REPO_ROOT / path
        return file.exists() and script in json.loads(file.read_text(encoding="utf-8")).get("scripts", {})
    if " › " in ref:
        path, title = ref.split(" › ", 1)
        file = REPO_ROOT / path
        return file.exists() and f'"{title}"' in file.read_text(encoding="utf-8")
    return False


def test_every_vs01_item_is_traced():
    rows = matrix_rows()
    expected = source_ids()
    assert len(expected) == 40, f"the source lists changed size ({len(expected)} items); update the matrix and this check"
    assert set(rows) == expected, f"missing rows: {sorted(expected - set(rows))}; unknown rows: {sorted(set(rows) - expected)}"
    problems = []
    for item, cell in rows.items():
        refs = re.findall(r"`([^`]+)`", cell)
        if not refs and not cell.startswith("N/A — "):
            problems.append(f"{item}: no tests and no N/A reason")
        for ref in refs:
            if not reference_exists(ref):
                problems.append(f"{item}: {ref} does not exist")
        live = [r for r in refs if f"`{r}` [quarantined:" not in cell]
        if refs and not live:
            problems.append(f"{item}: every referenced test is quarantined")
    assert not problems, "\n".join(problems)


def test_reference_checks_reject_missing_tests():
    assert reference_exists("backend/tests/test_api.py::test_vs01_flow")
    assert not reference_exists("backend/tests/test_api.py::test_does_not_exist")
    assert reference_exists("frontend/tests/pairing.test.ts › refuses mismatched revisions even when both are CURRENT")
    assert not reference_exists("frontend/tests/pairing.test.ts › refuses mismatched revisions")
    assert reference_exists("frontend/package.json#typecheck")
    assert not reference_exists("frontend/package.json#nope")
