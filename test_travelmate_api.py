from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from adapters.passenger_app_adapter import read_passenger_app_inputs
from travelmate_api.errors import ApiError
from travelmate_api.repository import JourneySessionRepository
from travelmate_api.schemas import JourneySessionCreate, PassengerProfileUpsert
from travelmate_api.service import JourneySessionService, PassengerProfileService, with_engine_input


class JourneySessionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        repository = JourneySessionRepository(Path(self.temp_dir.name) / "test.db")
        repository.initialize()
        self.repository = repository
        self.service = JourneySessionService(repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def request(self, **overrides) -> JourneySessionCreate:
        values = {
            "passenger_id": "passenger-1",
            "journey_id": "journey-1",
            "vehicle_id": "bus-24",
            "declared_ui_options": ["extra time exiting"],
            "consent_to_support_sharing": True,
        }
        values.update(overrides)
        return JourneySessionCreate(**values)

    def test_maps_mobile_option_into_existing_poc_category(self) -> None:
        result = with_engine_input(self.service.create(self.request()))
        self.assertEqual(result["declared_ui_options"], ["extra_time_exiting"])
        self.assertEqual(result["support_categories"], ["mobility_support"])
        self.assertEqual(result["engine_input"]["passenger_event"]["source"], "app")

    def test_rejects_unknown_support_option(self) -> None:
        with self.assertRaises(ApiError) as caught:
            self.service.create(self.request(declared_ui_options=["teleport assistance"]))
        self.assertEqual(caught.exception.code, "UNSUPPORTED_ASSISTANCE_TYPE")
        self.assertEqual(caught.exception.status_code, 422)

    def test_requires_consent_before_sharing_support_needs(self) -> None:
        with self.assertRaises(ApiError) as caught:
            self.service.create(self.request(consent_to_support_sharing=False))
        self.assertEqual(caught.exception.code, "CONSENT_REQUIRED")

    def test_new_vehicle_session_completes_previous_session(self) -> None:
        first = self.service.create(self.request())
        second = self.service.create(self.request(journey_id="journey-2"))
        self.assertEqual(self.repository.get(first["session_id"])["status"], "completed")
        self.assertEqual(self.repository.get(second["session_id"])["status"], "active")

    def test_existing_poc_adapter_reads_active_vehicle_session(self) -> None:
        self.service.create(self.request(stop_request=True, consent_enhanced_supervision=True))
        with patch.dict(
            "os.environ",
            {
                "TRAVELMATE_API_DB": str(self.repository.database_path),
                "TRAVELMATE_VEHICLE_ID": "bus-24",
            },
        ):
            consent, passenger_event, enhanced = read_passenger_app_inputs()
        self.assertEqual(
            [category.value for category in consent.active_support_categories],
            ["mobility_support"],
        )
        self.assertTrue(passenger_event.stop_request)
        self.assertTrue(enhanced)


class PassengerProfileServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = JourneySessionRepository(Path(self.temp_dir.name) / "test.db")
        self.repository.initialize()
        self.service = PassengerProfileService(self.repository)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def profile(self, **overrides) -> PassengerProfileUpsert:
        values = {
            "first_name": "Ooreoluwa",
            "last_name": "Oluwabiyi",
            "preferred_name": "Oore",
            "phone_number": "+44 1234 567890",
            "email_address": "oore@example.com",
            "emergency_contact": "Emergency contact",
            "preferred_language": "English (UK)",
            "home_location": "Leicester",
            "communication_method": "combined",
            "accessibility_needs": {"reduced_mobility": True},
            "assistance_preferences": {
                "audio_guidance": True,
                "vibration_guidance": True,
                "step_free_routes": True,
            },
            "sharing_preference": "needed",
            "personalised_suggestions": True,
            "enhanced_supervision": False,
        }
        values.update(overrides)
        return PassengerProfileUpsert(**values)

    def test_creates_and_reads_profile(self) -> None:
        created = self.service.upsert("passenger-001", self.profile())
        loaded = self.service.get("passenger-001")
        self.assertEqual(loaded, created)
        self.assertEqual(loaded["preferred_name"], "Oore")
        self.assertTrue(loaded["accessibility_needs"]["reduced_mobility"])

    def test_updates_profile_without_changing_created_at(self) -> None:
        created = self.service.upsert("passenger-001", self.profile())
        updated = self.service.upsert(
            "passenger-001",
            self.profile(home_location="London"),
        )
        self.assertEqual(updated["home_location"], "London")
        self.assertEqual(updated["created_at"], created["created_at"])

    def test_missing_profile_returns_api_error(self) -> None:
        with self.assertRaises(ApiError) as caught:
            self.service.get("missing-passenger")
        self.assertEqual(caught.exception.code, "PASSENGER_PROFILE_NOT_FOUND")
        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
