"""VS-01 supported-configuration constants.

Each value cites the decision that defines it. These are supported-range limits,
not structural, headroom, or building-code limits.
"""

from __future__ import annotations

import math

# D026: published coordinate comparison epsilon (not a fabrication tolerance).
LENGTH_EPSILON_M = 1e-6
# D032: tolerance for pitch comparisons.
ANGLE_EPSILON_RAD = 1e-9

# D029: integers must be exactly representable as IEEE-754 doubles.
MAX_SAFE_INTEGER = 2**53 - 1

# Schema versions accepted by this implementation (building-model.md §8).
MODEL_SCHEMA_VERSION = 1
RECORD_SCHEMA_VERSION = 1

# D032: footprint, bay, grid, roof bounds (inclusive).
FOOTPRINT_MIN_M = 3.6576  # 12'-0"
FOOTPRINT_MAX_M = 24.384  # 80'-0"
BAY_MIN_M = 1.2192  # 4'-0"
BAY_MAX_M = 7.3152  # 24'-0"
GRID_STATIONS_MIN = 2
GRID_STATIONS_MAX = 7
PITCH_MIN_RAD = math.atan(0.25)  # 3/12
PITCH_MAX_RAD = math.atan(1.0)  # 12/12
EAVE_OVERHANG_MAX_M = 0.9144  # 3'-0"

# D034: level datum and story-height bounds (inclusive).
LEVEL_COUNT = 2
STORY_HEIGHT_MIN_M = 2.4384  # 8'-0"
STORY_HEIGHT_MAX_M = 4.2672  # 14'-0"

# The only supported generation mode. Supported generation rules are those registered
# in homedesign.timber.rules (TIMBER-001 §6).
SUPPORTED_GENERATION_MODE = "DETERMINISTIC_RULE"

# MODEL-001 §5.1 parser defaults.
DEFAULT_MAX_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_DEPTH = 32


def within(value: float, low: float, high: float, tolerance: float) -> bool:
    """Inclusive range check with a symmetric tolerance."""
    return low - tolerance <= value <= high + tolerance
