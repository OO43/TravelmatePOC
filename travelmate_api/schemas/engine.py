from __future__ import annotations

from pydantic import BaseModel


class EngineInput(BaseModel):
    support_categories: list[str]
    passenger_event: dict[str, object]
    consent_enhanced_supervision: bool


