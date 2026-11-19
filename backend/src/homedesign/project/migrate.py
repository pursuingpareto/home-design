"""Minimal migration runner: numbered SQL files, recorded in ``schema_migrations`` (MODEL-004 §10, item 3).

Usage:  uv run python -m homedesign.project.migrate postgresql:///homedesign
"""

from __future__ import annotations

import sys
from importlib import resources

import psycopg


def migration_files() -> list[tuple[str, str]]:
    folder = resources.files(__package__).joinpath("migrations")
    names = sorted(p.name for p in folder.iterdir() if p.name.endswith(".sql"))
    return [(name.removesuffix(".sql"), folder.joinpath(name).read_text(encoding="utf-8")) for name in names]


def migrate(conninfo: str) -> list[str]:
    """Apply pending migrations in order, each in its own transaction. Returns the versions applied."""
    applied: list[str] = []
    with psycopg.connect(conninfo, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for version, sql in migration_files():
            if version in done:
                continue
            with conn.transaction():
                conn.execute(sql)
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            applied.append(version)
    return applied


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m homedesign.project.migrate <conninfo>")
    print("applied:", migrate(sys.argv[1]) or "nothing")
