"""PostgreSQL tables and repository; schema changes are managed by Alembic."""
from datetime import datetime
from functools import lru_cache

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Index, MetaData, String,
    Table, create_engine, inspect, select, text, update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import make_url

metadata = MetaData()
journey_sessions = Table(
    "journey_sessions", metadata,
    Column("session_id", String, primary_key=True),
    Column("passenger_id", String, nullable=False),
    Column("journey_id", String, nullable=False),
    Column("vehicle_id", String, nullable=False),
    Column("declared_ui_options", JSONB, nullable=False),
    Column("support_categories", JSONB, nullable=False),
    Column("consent_to_support_sharing", Boolean, nullable=False),
    Column("consent_enhanced_supervision", Boolean, nullable=False),
    Column("stop_request", Boolean, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("status IN ('active', 'completed')", name="ck_journey_sessions_status"),
)
Index("idx_journey_sessions_vehicle_status", journey_sessions.c.vehicle_id,
      journey_sessions.c.status, journey_sessions.c.created_at.desc())
passenger_profiles = Table(
    "passenger_profiles", metadata,
    Column("passenger_id", String(100), primary_key=True),
    Column("first_name", String(100), nullable=False),
    Column("last_name", String(100), nullable=False),
    Column("preferred_name", String(100), nullable=False),
    Column("phone_number", String(50), nullable=False),
    Column("email_address", String(320), nullable=False),
    Column("emergency_contact", String(255), nullable=False),
    Column("preferred_language", String(100), nullable=False),
    Column("home_location", String(255), nullable=False),
    Column("communication_method", String(20), nullable=False),
    Column("accessibility_needs", JSONB, nullable=False),
    Column("assistance_preferences", JSONB, nullable=False),
    Column("sharing_preference", String(20), nullable=False),
    Column("personalised_suggestions", Boolean, nullable=False),
    Column("enhanced_supervision", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "communication_method IN ('audio', 'visual', 'combined')",
        name="ck_passenger_profiles_communication_method",
    ),
    CheckConstraint(
        "sharing_preference IN ('needed', 'always', 'never')",
        name="ck_passenger_profiles_sharing_preference",
    ),
)
Index("idx_passenger_profiles_email_address", passenger_profiles.c.email_address)


def postgres_url(raw_url):
    url = make_url(raw_url)
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg driver.")
    return url.set(drivername="postgresql+psycopg")


class PostgresJourneySessionRepository:
    def __init__(self, database_url):
        self.engine = create_engine(postgres_url(database_url), pool_pre_ping=True,
                                    connect_args={"connect_timeout": 10})

    def initialize(self):
        with self.engine.connect() as connection:
            inspector = inspect(connection)
            if not inspector.has_table("journey_sessions") or not inspector.has_table("passenger_profiles"):
                raise RuntimeError("Database schema is missing. Run: python -m alembic upgrade head")

    def close(self):
        self.engine.dispose()

    def create(self, record):
        values = {**record, "created_at": datetime.fromisoformat(record["created_at"])}
        with self.engine.begin() as connection:
            # Preserve the POC's one-active-session-per-vehicle behaviour, including
            # simultaneous confirmations when no previous row exists to lock.
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:vehicle, 0))"),
                               {"vehicle": record["vehicle_id"]})
            connection.execute(update(journey_sessions).where(
                journey_sessions.c.vehicle_id == record["vehicle_id"],
                journey_sessions.c.status == "active",
            ).values(status="completed"))
            connection.execute(journey_sessions.insert().values(**values))
        return record

    def get(self, session_id):
        return self._get(select(journey_sessions).where(journey_sessions.c.session_id == session_id))

    def get_active_for_vehicle(self, vehicle_id):
        return self._get(select(journey_sessions).where(
            journey_sessions.c.vehicle_id == vehicle_id,
            journey_sessions.c.status == "active",
        ).order_by(journey_sessions.c.created_at.desc()).limit(1))

    def upsert_profile(self, record):
        values = {
            **record,
            "created_at": datetime.fromisoformat(record["created_at"]),
            "updated_at": datetime.fromisoformat(record["updated_at"]),
        }
        statement = postgresql_insert(passenger_profiles).values(**values)
        update_values = {
            column.name: getattr(statement.excluded, column.name)
            for column in passenger_profiles.columns
            if column.name not in {"passenger_id", "created_at"}
        }
        statement = statement.on_conflict_do_update(
            index_elements=[passenger_profiles.c.passenger_id],
            set_=update_values,
        ).returning(*passenger_profiles.c)
        with self.engine.begin() as connection:
            row = connection.execute(statement).mappings().one()
        return self._profile_record(row)

    def get_profile(self, passenger_id):
        with self.engine.connect() as connection:
            row = connection.execute(select(passenger_profiles).where(
                passenger_profiles.c.passenger_id == passenger_id
            )).mappings().first()
        return self._profile_record(row) if row is not None else None

    @staticmethod
    def _profile_record(row):
        record = dict(row)
        record["created_at"] = record["created_at"].isoformat()
        record["updated_at"] = record["updated_at"].isoformat()
        return record

    def _get(self, statement):
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        if row is None:
            return None
        record = dict(row)
        record["created_at"] = record["created_at"].isoformat()
        return record


@lru_cache(maxsize=4)
def postgres_repository(database_url):
    return PostgresJourneySessionRepository(database_url)
