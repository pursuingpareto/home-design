"""PostgreSQL revision store (MODEL-004 §5): JSONB snapshots, append-only operations, row locks."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .store import ArtifactRow, DuplicateCommand, OperationRow, ProjectRow, RevisionRow

_REVISION_COLUMNS = "revision_id, project_id, parent_revision_id, sequence, model_schema_version, snapshot, fingerprint, created_at"
_OPERATION_COLUMNS = (
    "operation_id, project_id, actor_id, command_id, command_type, command, command_hash, base_revision_id, "
    "result, rejection_code, revision_id, classification, classification_version, created_at"
)


def _s(value: Any) -> Any:
    """UUID columns come back as uuid.UUID; the service works with canonical strings (D030)."""
    return None if value is None else str(value)


def _project(row: dict) -> ProjectRow:
    return ProjectRow(_s(row["project_id"]), _s(row["head_revision_id"]), row["head_sequence"], row["created_at"], _s(row["created_by"]))


def _revision(row: dict) -> RevisionRow:
    return RevisionRow(
        _s(row["revision_id"]), _s(row["project_id"]), _s(row["parent_revision_id"]), row["sequence"],
        row["model_schema_version"], row["snapshot"], row["fingerprint"], row["created_at"],
    )


def _operation(row: dict) -> OperationRow:
    return OperationRow(
        _s(row["operation_id"]), _s(row["project_id"]), _s(row["actor_id"]), _s(row["command_id"]), row["command_type"],
        row["command"], row["command_hash"], _s(row["base_revision_id"]), row["result"], row["rejection_code"],
        _s(row["revision_id"]), row["classification"], row["classification_version"], row["created_at"],
    )


class _PostgresTx:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def _one(self, sql: str, params: tuple) -> dict | None:
        return self.conn.execute(sql, params).fetchone()

    def get_project(self, project_id, *, lock=False):
        row = self._one(
            "SELECT * FROM projects WHERE project_id = %s" + (" FOR UPDATE" if lock else ""),
            (project_id,),
        )
        return _project(row) if row else None

    def get_revision(self, project_id, revision_id):
        row = self._one(
            f"SELECT {_REVISION_COLUMNS} FROM revisions WHERE project_id = %s AND revision_id = %s",
            (project_id, revision_id),
        )
        return _revision(row) if row else None

    def list_revisions(self, project_id):
        rows = self.conn.execute(
            f"SELECT {_REVISION_COLUMNS} FROM revisions WHERE project_id = %s ORDER BY sequence", (project_id,)
        ).fetchall()
        ops = {
            _s(o["revision_id"]): _operation(o)
            for o in self.conn.execute(
                f"SELECT {_OPERATION_COLUMNS} FROM operations WHERE project_id = %s AND result = 'committed'", (project_id,)
            ).fetchall()
        }
        return [(_revision(r), ops.get(_s(r["revision_id"]))) for r in rows]

    def find_operation(self, project_id, actor_id, command_id):
        row = self._one(
            f"SELECT {_OPERATION_COLUMNS} FROM operations WHERE project_id = %s AND actor_id = %s AND command_id = %s"
            " AND result IN ('committed', 'noop') AND command_type <> 'CreateReferenceProject'",
            (project_id, actor_id, command_id),
        )
        return _operation(row) if row else None

    def find_creation(self, actor_id, command_id):
        row = self._one(
            f"SELECT {_OPERATION_COLUMNS} FROM operations WHERE actor_id = %s AND command_id = %s"
            " AND result = 'committed' AND command_type = 'CreateReferenceProject'",
            (actor_id, command_id),
        )
        return _operation(row) if row else None

    def list_operations(self, project_id):
        rows = self.conn.execute(
            f"SELECT {_OPERATION_COLUMNS} FROM operations WHERE project_id = %s ORDER BY log_position",
            (project_id,),
        ).fetchall()
        return [_operation(r) for r in rows]

    def insert_project(self, row):
        self.conn.execute(
            "INSERT INTO projects (project_id, head_revision_id, head_sequence, created_at, created_by) VALUES (%s, %s, %s, %s, %s)",
            (row.project_id, row.head_revision_id, row.head_sequence, row.created_at, row.created_by),
        )

    def insert_revision(self, row):
        self.conn.execute(
            f"INSERT INTO revisions ({_REVISION_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (row.revision_id, row.project_id, row.parent_revision_id, row.sequence, row.model_schema_version,
             Jsonb(row.snapshot), row.fingerprint, row.created_at),
        )

    def insert_operation(self, row):
        try:
            with self.conn.transaction():  # savepoint, so a duplicate does not abort the outer transaction
                self.conn.execute(
                    f"INSERT INTO operations ({_OPERATION_COLUMNS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (row.operation_id, row.project_id, row.actor_id, row.command_id, row.command_type,
                     None if row.command is None else Jsonb(row.command), row.command_hash, row.base_revision_id,
                     row.result, row.rejection_code, row.revision_id, row.classification, row.classification_version,
                     row.created_at),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateCommand() from exc

    def set_head(self, project_id, revision_id, sequence):
        self.conn.execute(
            "UPDATE projects SET head_revision_id = %s, head_sequence = %s WHERE project_id = %s",
            (revision_id, sequence, project_id),
        )

    def get_artifacts(self, revision_id, artifact_type):
        rows = self.conn.execute(
            "SELECT * FROM artifacts WHERE revision_id = %s AND artifact_type = %s ORDER BY generated_at, input_fingerprint",
            (revision_id, artifact_type),
        ).fetchall()
        return [
            ArtifactRow(_s(r["project_id"]), _s(r["revision_id"]), r["artifact_type"], r["input_fingerprint"],
                        r["generator_id"], r["generator_version"], r["status"], r["payload"], r["error"],
                        r["warnings"], r["generated_at"])
            for r in rows
        ]

    def put_artifact(self, row):
        self.conn.execute(
            "INSERT INTO artifacts (project_id, revision_id, artifact_type, input_fingerprint, generator_id,"
            " generator_version, status, payload, error, warnings, generated_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (revision_id, artifact_type, input_fingerprint) DO NOTHING",
            (row.project_id, row.revision_id, row.artifact_type, row.input_fingerprint, row.generator_id,
             row.generator_version, row.status, None if row.payload is None else Jsonb(row.payload),
             None if row.error is None else Jsonb(row.error), Jsonb(row.warnings), row.generated_at),
        )

    def delete_artifacts(self, revision_id):
        self.conn.execute("DELETE FROM artifacts WHERE revision_id = %s", (revision_id,))

    def get_price_book(self, project_id):
        row = self._one("SELECT * FROM price_books WHERE project_id = %s ORDER BY version DESC LIMIT 1", (project_id,))
        if row is None:
            return None
        return {"project_id": _s(row["project_id"]), "version": row["version"], "price_book_id": _s(row["price_book_id"]),
                "book": row["book"], "set_by": _s(row["set_by"]), "set_at": row["set_at"]}

    def insert_price_book(self, row):
        self.conn.execute(
            "INSERT INTO price_books (project_id, version, price_book_id, book, set_by, set_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (row["project_id"], row["version"], row["price_book_id"], Jsonb(row["book"]), row["set_by"], row["set_at"]),
        )


class PostgresStore:
    """One connection per transaction; ``conninfo`` is a libpq connection string or URL."""

    def __init__(self, conninfo: str) -> None:
        self.conninfo = conninfo

    @contextmanager
    def transaction(self) -> Iterator[_PostgresTx]:
        with psycopg.connect(self.conninfo, row_factory=dict_row) as conn:
            with conn.transaction():
                yield _PostgresTx(conn)
