"""The code catalog in codes.py must match building-model.md §6.1 (D035, D046)."""

from __future__ import annotations

import re

from conftest import BUILDING_MODEL_DOC
from homedesign.model import codes


def test_catalog_matches_documentation():
    text = BUILDING_MODEL_DOC.read_text(encoding="utf-8")
    section = text[text.index("### 6.1 Detail codes") : text.index("## 7.")]
    documented = {
        code: codes.Stage(int(stage))
        for code, stage in re.findall(r"^\| `([A-Z_]+)` \| ([1-5]) \|", section, flags=re.MULTILINE)
    }
    assert documented == codes.CATALOG
