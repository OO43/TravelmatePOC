from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .consent import PassengerConsentRequest
from .engine import EngineInput
from .support import PassengerSupportRequest


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


