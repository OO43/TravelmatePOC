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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS passenger_profiles (
                    passenger_id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    preferred_name TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    email_address TEXT NOT NULL,
                    emergency_contact TEXT NOT NULL,
                    preferred_language TEXT NOT NULL,
                    home_location TEXT NOT NULL,
                    communication_method TEXT NOT NULL
                        CHECK(communication_method IN ('audio', 'visual', 'combined')),
                    accessibility_needs TEXT NOT NULL,
                    assistance_preferences TEXT NOT NULL,
                    sharing_preference TEXT NOT NULL
                        CHECK(sharing_preference IN ('needed', 'always', 'never')),
                    personalised_suggestions INTEGER NOT NULL,
                    enhanced_supervision INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_passenger_profiles_email_address "
                "ON passenger_profiles(email_address)"
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

    def upsert_profile(self, record: dict[str, Any]) -> dict[str, Any]:
        stored = {
            **record,
            "accessibility_needs": json.dumps(record["accessibility_needs"]),
            "assistance_preferences": json.dumps(record["assistance_preferences"]),
            "personalised_suggestions": int(record["personalised_suggestions"]),
            "enhanced_supervision": int(record["enhanced_supervision"]),
        }
        columns = tuple(stored)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in columns
            if column not in {"passenger_id", "created_at"}
        )
        with closing(self._connect()) as connection:
            connection.execute(
                f"INSERT INTO passenger_profiles ({', '.join(columns)}) VALUES ({placeholders}) "
                f"ON CONFLICT(passenger_id) DO UPDATE SET {updates}",
                tuple(stored[column] for column in columns),
            )
            connection.commit()
        profile = self.get_profile(record["passenger_id"])
        if profile is None:
            raise RuntimeError("Passenger profile was not saved.")
        return profile

    def get_profile(self, passenger_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM passenger_profiles WHERE passenger_id = ?",
                (passenger_id,),
            ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["accessibility_needs"] = json.loads(record["accessibility_needs"])
        record["assistance_preferences"] = json.loads(record["assistance_preferences"])
        record["personalised_suggestions"] = bool(record["personalised_suggestions"])
        record["enhanced_supervision"] = bool(record["enhanced_supervision"])
        return record


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


def create_repository(settings):
    if settings.database_url:
        from .database import postgres_repository
        return postgres_repository(settings.database_url)
    return JourneySessionRepository(settings.database_path)

