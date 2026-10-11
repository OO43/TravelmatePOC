"""Run against an isolated database with TEST_DATABASE_URL set."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from travelmate_api.database import PostgresJourneySessionRepository, journey_sessions
from travelmate_api.schemas import JourneySessionCreate
from travelmate_api.service import JourneySessionService


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to an isolated PostgreSQL database")
class PostgresRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.url = os.environ["TEST_DATABASE_URL"]
        from unittest.mock import patch
        with patch.dict(os.environ, {"DATABASE_URL": self.url}):
            command.upgrade(Config("alembic.ini"), "head")
        self.repository = PostgresJourneySessionRepository(self.url)
        self.repository.initialize()
        self.service = JourneySessionService(self.repository)
        self.vehicle_id = f"test-{uuid4()}"

    def tearDown(self):
        with self.repository.engine.begin() as connection:
            connection.execute(delete(journey_sessions).where(
                journey_sessions.c.vehicle_id == self.vehicle_id))
        self.repository.close()

    def request(self):
        return JourneySessionCreate(passenger_id="test-passenger", journey_id=str(uuid4()),
            vehicle_id=self.vehicle_id, declared_ui_options=["extra_time_exiting"],
            consent_to_support_sharing=True, stop_request=True)

    def test_persistence_after_reconnecting_and_session_replacement(self):
        first = self.service.create(self.request())
        self.repository.close()
        self.assertEqual(self.repository.get(first["session_id"]), first)
        second = self.service.create(self.request())
        self.assertEqual(self.repository.get(first["session_id"])["status"], "completed")
        self.assertEqual(self.repository.get_active_for_vehicle(self.vehicle_id), second)
        self.assertIsNone(self.repository.get(str(uuid4())))

    def test_concurrent_confirmations_leave_one_active_session(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            records = list(executor.map(lambda _: self.service.create(self.request()), range(2)))
        statuses = [self.repository.get(record["session_id"])["status"] for record in records]
        self.assertEqual(sorted(statuses), ["active", "completed"])
