from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class JourneySessionRepository:
    """Small SQLite repository; the API/service boundary allows PostgreSQL later."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS journey_sessions (
                    session_id TEXT PRIMARY KEY,
                    passenger_id TEXT NOT NULL,
                    journey_id TEXT NOT NULL,
                    vehicle_id TEXT NOT NULL,
                    declared_ui_options TEXT NOT NULL,
                    support_categories TEXT NOT NULL,
                    consent_to_support_sharing INTEGER NOT NULL,
                    consent_enhanced_supervision INTEGER NOT NULL,
                    stop_request INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active', 'completed')),
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_journey_sessions_vehicle_status "
                "ON journey_sessions(vehicle_id, status, created_at DESC)"
            )
            connection.commit()

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE journey_sessions SET status = 'completed' "
                "WHERE vehicle_id = ? AND status = 'active'",
                (record["vehicle_id"],),
            )
            connection.execute(
                """
                INSERT INTO journey_sessions (
                    session_id, passenger_id, journey_id, vehicle_id,
                    declared_ui_options, support_categories,
                    consent_to_support_sharing, consent_enhanced_supervision,
                    stop_request, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["session_id"],
                    record["passenger_id"],
                    record["journey_id"],
                    record["vehicle_id"],
                    json.dumps(record["declared_ui_options"]),
                    json.dumps(record["support_categories"]),
                    int(record["consent_to_support_sharing"]),
                    int(record["consent_enhanced_supervision"]),
                    int(record["stop_request"]),
                    record["status"],
                    record["created_at"],
                ),
            )
            connection.commit()
        return record

    def get(self, session_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM journey_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return _row_to_record(row) if row else None

    def get_active_for_vehicle(self, vehicle_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT * FROM journey_sessions
                WHERE vehicle_id = ? AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
                """,
                (vehicle_id,),
            ).fetchone()
        return _row_to_record(row) if row else None


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["declared_ui_options"] = json.loads(record["declared_ui_options"])
    record["support_categories"] = json.loads(record["support_categories"])
    for key in (
        "consent_to_support_sharing",
        "consent_enhanced_supervision",
        "stop_request",
    ):
        record[key] = bool(record[key])
    return record

