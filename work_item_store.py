"""SQLite persistence for Sentinel App work items.

Uses the stdlib sqlite3 module only (no ORM). This layer does not expose HTTP
routes, authentication, or staff accounts. Demonstration WORK_ITEMS in app.py
are not auto-migrated into the database.

Database path is configurable so Docker can later mount persistent storage
(for example SENTINEL_APP_DB_PATH=/data/sentinel.db with a volume on /data).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from app import normalize_work_item_fields, validate_work_item

DEFAULT_DB_ENV_VAR = "SENTINEL_APP_DB_PATH"
DEFAULT_DB_FILENAME = "sentinel_app.db"

_CREATE_WORK_ITEMS_SQL = """
CREATE TABLE IF NOT EXISTS work_items (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL
)
"""

_INSERT_SQL = """
INSERT INTO work_items (id, title, category, severity, status, owner)
VALUES (?, ?, ?, ?, ?, ?)
"""

_UPDATE_SQL = """
UPDATE work_items
SET title = ?, category = ?, severity = ?, status = ?, owner = ?
WHERE id = ?
"""

_SELECT_BY_ID_SQL = """
SELECT id, title, category, severity, status, owner
FROM work_items
WHERE id = ?
"""

_SELECT_ALL_SQL = """
SELECT id, title, category, severity, status, owner
FROM work_items
ORDER BY id
"""


class WorkItemStoreError(ValueError):
    """Raised when a work-item store operation fails validation or constraints."""

    def __init__(self, message: str, *, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = list(errors or [])


def default_database_path() -> Path:
    """Return the configured SQLite file path.

    Prefers SENTINEL_APP_DB_PATH when set; otherwise uses
    ``<cwd>/data/sentinel_app.db`` without creating the file.
    """
    configured = os.environ.get(DEFAULT_DB_ENV_VAR)
    if configured:
        return Path(configured)
    return Path.cwd() / "data" / DEFAULT_DB_FILENAME


def _row_to_item(row: sqlite3.Row) -> dict[str, str]:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "severity": row["severity"],
        "status": row["status"],
        "owner": row["owner"],
    }


class WorkItemStore:
    """Small SQLite-backed store for security work items."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Open (or reuse) a connection with row factory and foreign keys on."""
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            self._connection = connection
        return self._connection

    def close(self) -> None:
        """Close the current connection if open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def initialize_schema(self) -> None:
        """Create the work_items table if it does not exist.

        Idempotent: repeated calls do not drop or overwrite existing rows.
        """
        connection = self.connect()
        with connection:
            connection.execute(_CREATE_WORK_ITEMS_SQL)

    def list_ids(self) -> set[str]:
        """Return the set of stored work-item IDs."""
        connection = self.connect()
        rows = connection.execute("SELECT id FROM work_items").fetchall()
        return {row["id"] for row in rows}

    def insert(self, item: dict[str, Any]) -> dict[str, str]:
        """Insert a validated work item. Raises WorkItemStoreError on failure."""
        if not isinstance(item, dict):
            raise WorkItemStoreError(
                "Work item must be a dictionary",
                errors=["Work item must be a dictionary"],
            )

        normalized = normalize_work_item_fields(item)
        errors = validate_work_item(
            normalized,
            existing_ids=self.list_ids(),
            require_id=True,
        )
        if errors:
            raise WorkItemStoreError(
                "Invalid work item; insert rejected",
                errors=errors,
            )

        connection = self.connect()
        try:
            with connection:
                connection.execute(
                    _INSERT_SQL,
                    (
                        normalized["id"],
                        normalized["title"],
                        normalized["category"],
                        normalized["severity"],
                        normalized["status"],
                        normalized["owner"],
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise WorkItemStoreError(
                f"Duplicate work-item id: {normalized['id']}",
                errors=[f"Duplicate work-item id: {normalized['id']}"],
            ) from exc

        stored = self.get_by_id(normalized["id"])
        assert stored is not None
        return stored

    def get_by_id(self, work_id: str) -> dict[str, str] | None:
        """Return one work item by ID, or None if missing."""
        if not isinstance(work_id, str):
            raise WorkItemStoreError(
                "id must be a string",
                errors=["id must be a string"],
            )
        connection = self.connect()
        row = connection.execute(_SELECT_BY_ID_SQL, (work_id,)).fetchone()
        if row is None:
            return None
        return _row_to_item(row)

    def list_all(self) -> list[dict[str, str]]:
        """Return all work items ordered by ID."""
        connection = self.connect()
        rows = connection.execute(_SELECT_ALL_SQL).fetchall()
        return [_row_to_item(row) for row in rows]

    def update(self, item: dict[str, Any]) -> dict[str, str]:
        """Update an existing work item by ID. Raises WorkItemStoreError on failure."""
        if not isinstance(item, dict):
            raise WorkItemStoreError(
                "Work item must be a dictionary",
                errors=["Work item must be a dictionary"],
            )

        normalized = normalize_work_item_fields(item)
        errors = validate_work_item(normalized, require_id=True)
        if errors:
            raise WorkItemStoreError(
                "Invalid work item; update rejected",
                errors=errors,
            )

        work_id = normalized["id"]
        if self.get_by_id(work_id) is None:
            raise WorkItemStoreError(
                f"Work item not found: {work_id}",
                errors=[f"Work item not found: {work_id}"],
            )

        connection = self.connect()
        with connection:
            connection.execute(
                _UPDATE_SQL,
                (
                    normalized["title"],
                    normalized["category"],
                    normalized["severity"],
                    normalized["status"],
                    normalized["owner"],
                    work_id,
                ),
            )

        stored = self.get_by_id(work_id)
        assert stored is not None
        return stored
