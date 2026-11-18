"""Error detail paths (D036).

A path is a sequence of steps rendered as text: identifier keys joined with ``.``,
other keys as ``["…"]`` (JSON string literal), array elements as ``[n]``, and
snapshot entities as ``entities[<id>]`` or ``entities[#<index>]`` when the entity
has no usable ID.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
_UUID_RE = re.compile(UUID_PATTERN)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_canonical_uuid(value: Any) -> bool:
    return isinstance(value, str) and _UUID_RE.match(value) is not None


@dataclass(frozen=True)
class EntityStep:
    """Addresses one element of the snapshot's ``entities`` array."""

    index: int
    usable_id: str | None

    def render(self) -> str:
        return f"[{self.usable_id}]" if self.usable_id is not None else f"[#{self.index}]"


Step = str | int | EntityStep


def render(steps: Sequence[Step]) -> str:
    text = ""
    for step in steps:
        if isinstance(step, EntityStep):
            text += step.render()
        elif isinstance(step, int):
            text += f"[{step}]"
        elif _IDENTIFIER_RE.match(step):
            text += f".{step}" if text else step
        else:
            text += "[" + json.dumps(step, ensure_ascii=False) + "]"
    return text


class EntityAddresser:
    """Decides how each entity is addressed.

    An entity's ID is usable when it is a canonical UUID that occurs exactly once
    across ``building`` and ``entities`` (D036).
    """

    def __init__(self, building_id: Any, entity_ids: Sequence[Any]) -> None:
        candidates = [i for i in [building_id, *entity_ids] if is_canonical_uuid(i)]
        counts = Counter(candidates)
        self._usable = [
            entity_id if is_canonical_uuid(entity_id) and counts[entity_id] == 1 else None
            for entity_id in entity_ids
        ]

    @classmethod
    def from_raw(cls, raw: Any) -> EntityAddresser:
        """Build from an unvalidated parsed snapshot (any JSON value)."""
        building_id = None
        entity_ids: list[Any] = []
        if isinstance(raw, dict):
            building = raw.get("building")
            if isinstance(building, dict):
                building_id = building.get("id")
            entities = raw.get("entities")
            if isinstance(entities, list):
                entity_ids = [e.get("id") if isinstance(e, dict) else None for e in entities]
        return cls(building_id, entity_ids)

    def entity(self, index: int) -> EntityStep:
        usable = self._usable[index] if 0 <= index < len(self._usable) else None
        return EntityStep(index, usable)

    def steps(self, raw_steps: Sequence[str | int]) -> list[Step]:
        """Convert raw steps (keys and indexes) into rendered-path steps."""
        if len(raw_steps) >= 2 and raw_steps[0] == "entities" and isinstance(raw_steps[1], int):
            return ["entities", self.entity(raw_steps[1]), *raw_steps[2:]]
        return list(raw_steps)

    def path(self, raw_steps: Sequence[str | int]) -> str:
        return render(self.steps(raw_steps))
