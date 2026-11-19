"""RFC 3339 UTC timestamps as used in snapshots and tokens (``YYYY-MM-DDTHH:MM:SS.ffffffZ``)."""

from __future__ import annotations

from datetime import UTC, datetime


def format_timestamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_timestamp(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)
