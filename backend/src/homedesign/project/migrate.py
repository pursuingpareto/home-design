"""Minimal migration runner: numbered SQL files, recorded in ``schema_migrations`` (MODEL-004 §10, item 3).

Usage:  uv run python -m homedesign.project.migrate postgresql:///homedesign

Before migrating, the runner refuses a database that still holds revisions of an older model
schema. Pre-release, those are not migrated or read (D055); the database is recreated instead
(MODEL-005 §8.3). Nothing is ever deleted here.
"""

from __future__ import annotations

import sys
from importlib import resources

import psycopg
from psycopg.conninfo import conninfo_to_dict

from homedesign.model.limits import MODEL_SCHEMA_VERSION


class OutdatedDatabase(RuntimeError):
    """The database holds revisions this version cannot read (D055)."""


def migration_files() -> list[tuple[str, str]]:
    folder = resources.files(__package__).joinpath("migrations")
    names = sorted(p.name for p in folder.iterdir() if p.name.endswith(".sql"))
    return [(name.removesuffix(".sql"), folder.joinpath(name).read_text(encoding="utf-8")) for name in names]


def migrate(conninfo: str) -> list[str]:
    """Apply pending migrations in order, each in its own transaction. Returns the versions applied."""
    applied: list[str] = []
    with psycopg.connect(conninfo, autocommit=True) as conn:
        _refuse_outdated(conn, conninfo)  # before any write
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


def _refuse_outdated(conn: psycopg.Connection, conninfo: str) -> None:
    has_revisions = conn.execute("SELECT to_regclass('revisions') IS NOT NULL").fetchone()[0]
    if not has_revisions:
        return
    row = conn.execute("SELECT min(model_schema_version) FROM revisions WHERE model_schema_version < %s", (MODEL_SCHEMA_VERSION,)).fetchone()
    if row[0] is not None:
        name = conninfo_to_dict(conninfo).get("dbname") or conninfo
        raise OutdatedDatabase(
            f"Database {name!r} holds projects of model schema version {row[0]}; this version reads only "
            f"version {MODEL_SCHEMA_VERSION}, and older projects are not migrated before the first release (D055). "
            f"Recreate it: scripts/dev.sh --reset (or dropdb {name} && createdb {name}). Nothing was changed."
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m homedesign.project.migrate <conninfo>")
    try:
        print("applied:", migrate(sys.argv[1]) or "nothing")
    except OutdatedDatabase as exc:
        raise SystemExit(str(exc)) from None
