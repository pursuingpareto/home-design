"""TEST-001 §4 and TEST-002 §5: the VS-01 and VS-02 traceability matrices are complete, and every test they name exists."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from conftest import REPO_ROOT

MATRIX = REPO_ROOT / "docs" / "implementation" / "acceptance-tests" / "vs-01-traceability.md"
VS02_MATRIX = REPO_ROOT / "docs" / "implementation" / "acceptance-tests" / "vs-02-traceability.md"
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


SKIP_MARKS = ("pytest.mark.skip", "pytest.mark.skipif", "pytest.mark.xfail")


def _is_skip_mark(node: ast.expr) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    return ast.unparse(target) in SKIP_MARKS


def _pytest_function_exists(file: Path, name: str, quarantined: bool) -> bool:
    """A module-level test function, with no skip or xfail mark unless the matrix quarantines it (TEST-002 §5.3)."""
    tree = ast.parse(file.read_text(encoding="utf-8"))
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), None)
    if function is None:
        return False
    module_marks = [
        mark
        for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets)
        for mark in (n.value.elts if isinstance(n.value, (ast.List, ast.Tuple)) else [n.value])
    ]
    return quarantined or not any(_is_skip_mark(mark) for mark in [*function.decorator_list, *module_marks])


def _title_exists(file: Path, title: str) -> bool:
    """The title occurs once in the file, as the first argument of `it(`, `test(`, or `describe(`, and not of
    `.skip(`, `.only(`, `.fixme(`, or `.todo(` (TEST-002 §5.3). A title in a comment, or a duplicate, fails."""
    text = file.read_text(encoding="utf-8")
    literal = f'"{title}"'
    if text.count(literal) != 1:
        return False
    return re.search(rf"(?<![\w.])(?:it|test|describe)\(\s*{re.escape(literal)}", text) is not None


def reference_exists(ref: str, *, quarantined: bool = False) -> bool:
    if "::" in ref:
        path, name = ref.split("::", 1)
        file = REPO_ROOT / path
        return file.exists() and _pytest_function_exists(file, name, quarantined)
    if ".json#" in ref:
        path, script = ref.split("#", 1)
        file = REPO_ROOT / path
        return file.exists() and script in json.loads(file.read_text(encoding="utf-8")).get("scripts", {})
    if " › " in ref:
        path, title = ref.split(" › ", 1)
        file = REPO_ROOT / path
        return file.exists() and _title_exists(file, title)
    return False


def reference_problems(item: str, cell: str) -> list[str]:
    """TEST-001 §4's checks on one row's tests cell: a test or an `N/A —` reason, every reference live, not all quarantined."""
    problems = []
    refs = re.findall(r"`([^`]+)`", cell)
    if not refs and not cell.startswith("N/A — "):
        problems.append(f"{item}: no tests and no N/A reason")
    quarantined = {r for r in refs if f"`{r}` [quarantined:" in cell}
    for ref in refs:
        if not reference_exists(ref, quarantined=ref in quarantined):
            problems.append(f"{item}: {ref} does not exist, is skipped, or is not a unique test title")
    if refs and not set(refs) - quarantined:
        problems.append(f"{item}: every referenced test is quarantined")
    return problems


def test_every_vs01_item_is_traced():
    rows = matrix_rows()
    expected = source_ids()
    assert len(expected) == 40, f"the source lists changed size ({len(expected)} items); update the matrix and this check"
    assert set(rows) == expected, f"missing rows: {sorted(expected - set(rows))}; unknown rows: {sorted(set(rows) - expected)}"
    problems = [problem for item, cell in rows.items() for problem in reference_problems(item, cell)]
    assert not problems, "\n".join(problems)


# --- VS-02 (TEST-002 §5) ----------------------------------------------------------------------


def normalize(text: str) -> str:
    """Criterion text as compared: Markdown links become their text, bold markers go, whitespace collapses."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return " ".join(text.replace("**", "").split())


def vs02_source_items() -> dict[str, str]:
    """ID -> text for the three VS-02 sources: vs-02.md §12.1 (one item per bullet, or per criterion without
    bullets), artifacts.md §10's "Version 2 reconciliation" bullets, and dependencies.md §8's "VS-02 examples"."""
    items: dict[str, str] = {}
    criteria: dict[str, tuple[str, list[str]]] = {}
    current = None
    for line in _section(DOCS / "implementation/acceptance-tests/vs-02.md", "### 12.1", "### 12.2").splitlines():
        if match := re.match(r"^- \*\*(AC2-\d\d): (.+)$", line):
            current = match.group(1)
            assert current not in criteria, f"duplicate criterion {current}"
            criteria[current] = ("**" + match.group(2), [])
        elif match := re.match(r"^  - (.+)$", line):
            assert current is not None, line
            criteria[current][1].append(match.group(1))
        else:
            assert not line.startswith((" -", "  ")), f"a criterion line the check cannot read: {line!r}"
    for criterion, (text, bullets) in criteria.items():
        if bullets:
            items.update({f"{criterion}.{k}": bullet for k, bullet in enumerate(bullets, 1)})
        else:
            items[criterion] = text
    for prefix, path, start, end in (
        ("ART2", "architecture/artifacts.md", "Version 2 reconciliation", "\n## "),
        ("DEP2", "architecture/dependencies.md", "VS-02 examples", "\n## "),
    ):
        bullets = re.findall(r"^- (.+)$", _section(DOCS / path, start, end), re.M)
        items.update({f"{prefix}-{k}": bullet for k, bullet in enumerate(bullets, 1)})
    return {item: normalize(text) for item, text in items.items()}


def vs02_matrix_rows(text: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        match = re.match(r"^\| ((?:AC2-\d\d(?:\.\d+)?)|(?:ART2|DEP2)-\d+) \| ([^|]+) \| (.+) \|$", line)
        if match:
            assert match.group(1) not in rows, f"duplicate row {match.group(1)}"
            rows[match.group(1)] = (match.group(2), match.group(3))
    return rows


def vs02_problems(rows: dict[str, tuple[str, str]], sources: dict[str, str]) -> list[str]:
    problems = []
    if set(rows) != set(sources):
        problems.append(f"missing rows: {sorted(set(sources) - set(rows))}; unknown rows: {sorted(set(rows) - set(sources))}")
    for item, (criterion, cell) in rows.items():
        if item in sources and normalize(criterion) != sources[item]:
            problems.append(f"{item}: the criterion reads differently in its source; review the row and its tests, then copy the text:\n  {sources[item]}")
        problems += reference_problems(item, cell)
    return problems


def test_every_vs02_item_is_traced():
    sources = vs02_source_items()
    assert len(sources) == 24, f"the source lists changed size ({len(sources)} items); update the matrix and this check"
    problems = vs02_problems(vs02_matrix_rows(VS02_MATRIX.read_text(encoding="utf-8")), sources)
    assert not problems, "\n".join(problems)


def test_vs02_check_rejects_reworded_missing_and_untested_rows():
    sources = vs02_source_items()
    rows = vs02_matrix_rows(VS02_MATRIX.read_text(encoding="utf-8"))
    assert vs02_problems(rows, sources) == []
    criterion, cell = rows["AC2-03.2"]
    reworded = {**rows, "AC2-03.2": (criterion.replace("validated", "checked"), cell)}
    assert [p.split(":")[0] for p in vs02_problems(reworded, sources)] == ["AC2-03.2"]
    spaced = {**rows, "AC2-03.2": ("  " + criterion.replace(" ", "\n "), cell)}  # whitespace alone is not a rewording
    assert vs02_problems(spaced, sources) == []
    missing = {k: v for k, v in rows.items() if k != "DEP2-4"}
    assert vs02_problems(missing, sources) == ["missing rows: ['DEP2-4']; unknown rows: []"]
    untested = {**rows, "ART2-3": (rows["ART2-3"][0], "nothing yet")}
    assert vs02_problems(untested, sources) == ["ART2-3: no tests and no N/A reason"]
    renamed = {**rows, "AC2-01": (rows["AC2-01"][0], "`backend/tests/test_timber.py::test_registry_renamed`")}
    assert vs02_problems(renamed, sources) == ["AC2-01: backend/tests/test_timber.py::test_registry_renamed does not exist, is skipped, or is not a unique test title"]
    assert normalize("**A** [D060](../x.md#y)  rows") == "A D060 rows"


def test_reference_checks_reject_missing_tests(tmp_path):
    assert reference_exists("backend/tests/test_api.py::test_vs01_flow")
    assert not reference_exists("backend/tests/test_api.py::test_does_not_exist")
    assert reference_exists("frontend/tests/pairing.test.ts › refuses mismatched revisions even when both are CURRENT")
    assert not reference_exists("frontend/tests/pairing.test.ts › refuses mismatched revisions")
    assert reference_exists("frontend/package.json#typecheck")
    assert not reference_exists("frontend/package.json#nope")

    # TEST-002 §5.3: a title counts once, as a live test's title; a pytest function counts without a skip mark.
    spec = tmp_path / "cases.test.ts"  # an absolute path stays absolute under REPO_ROOT
    spec.write_text(
        '// "only in a comment"\n'
        'describe("a group", () => {\n'
        '  it("live", () => {});\n'
        '  test(\n    "on its own line", () => {});\n'
        '  it.skip("skipped", () => {});\n'
        '  test.only("focused", () => {});\n'
        '  test.fixme("to fix", () => {});\n'
        '  it.todo("to do");\n'
        '  it("twice", () => {});\n'
        '  it("twice", () => {});\n'
        '  it("also in a comment", () => {}); // "also in a comment"\n'
        '  submit("not a test");\n'
        '});\n',
        encoding="utf-8",
    )
    for title in ("a group", "live", "on its own line"):
        assert reference_exists(f"{spec} › {title}"), title
    for title in ("only in a comment", "skipped", "focused", "to fix", "to do", "twice", "also in a comment", "not a test", "liv"):
        assert not reference_exists(f"{spec} › {title}"), title

    module = tmp_path / "test_cases.py"
    module.write_text(
        "import pytest\n\n"
        "def test_live():\n    pass\n\n"
        "@pytest.mark.skip(reason='later')\ndef test_skipped():\n    pass\n\n"
        "@pytest.mark.skipif(True, reason='never')\ndef test_skipped_if():\n    pass\n\n"
        "@pytest.mark.xfail\ndef test_expected_to_fail():\n    pass\n\n"
        "@pytest.mark.parametrize('x', [1, pytest.param(2, marks=pytest.mark.xfail)])\ndef test_one_case_marked(x):\n    pass\n\n"
        "class TestGroup:\n    def test_method(self):\n        pass\n",
        encoding="utf-8",
    )
    assert reference_exists(f"{module}::test_live")
    assert reference_exists(f"{module}::test_one_case_marked")  # a mark on one case is not a mark on the function
    for name in ("test_skipped", "test_skipped_if", "test_expected_to_fail", "test_method"):
        assert not reference_exists(f"{module}::{name}"), name
    assert reference_exists(f"{module}::test_skipped", quarantined=True)  # the matrix marks it quarantined

    skipped_module = tmp_path / "test_skipped_module.py"
    skipped_module.write_text("import pytest\n\npytestmark = [pytest.mark.slow, pytest.mark.skip]\n\ndef test_live():\n    pass\n", encoding="utf-8")
    assert not reference_exists(f"{skipped_module}::test_live")
