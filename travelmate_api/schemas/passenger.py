from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .consent import PassengerConsentRequest
from .engine import EngineInput
from .support import PassengerSupportRequest


class AccessibilityNeeds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visual_impairment: bool = False
    hearing_impairment: bool = False
    reduced_mobility: bool = False
    wheelchair_user: bool = False
    cognitive_support_required: bool = False
    assistance_animal_support: bool = False
    temporary_accessibility_need: bool = False


class AssistancePreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_guidance: bool = False
    vibration_guidance: bool = False
    boarding_assistance: bool = False
    alighting_assistance: bool = False
    extra_boarding_time: bool = False
    stop_announcements: bool = False
    large_text: bool = False
    high_contrast: bool = False
    step_free_routes: bool = False
    extra_transfer_time: bool = False
    priority_seating: bool = False


class PassengerProfileUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    preferred_name: str = Field(min_length=1, max_length=100)
    phone_number: str = Field(default="", max_length=50)
    email_address: str = Field(default="", max_length=320)
    emergency_contact: str = Field(default="", max_length=255)
    preferred_language: str = Field(min_length=1, max_length=100)
    home_location: str = Field(default="", max_length=255)
    communication_method: Literal["audio", "visual", "combined"]
    accessibility_needs: AccessibilityNeeds = Field(default_factory=AccessibilityNeeds)
    assistance_preferences: AssistancePreferences = Field(default_factory=AssistancePreferences)
    sharing_preference: Literal["needed", "always", "never"] = "needed"
    personalised_suggestions: bool = True
    enhanced_supervision: bool = False


class PassengerProfileResponse(PassengerProfileUpsert):
    passenger_id: str
    created_at: datetime
    updated_at: datetime


class JourneySessionCreate(PassengerSupportRequest, PassengerConsentRequest):
    """Compose support and consent while retaining the existing flat JSON API."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    passenger_id: str = Field(min_length=1, max_length=100)
    journey_id: str = Field(min_length=1, max_length=100)
    vehicle_id: str = Field(min_length=1, max_length=100)
    stop_request: bool = False


class JourneySessionResponse(BaseModel):
    session_id: str
    passenger_id: str
    journey_id: str
    vehicle_id: str
    declared_ui_options: list[str]
    support_categories: list[str]
    consent_to_support_sharing: bool
    consent_enhanced_supervision: bool
    stop_request: bool
    status: Literal["active", "completed"]
    created_at: datetime
    engine_input: EngineInput


