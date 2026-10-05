from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from adapters.passenger_app_adapter import (
    CONSENT_UI_OPTION_TO_SUPPORT,
    _normalize_ui_token,
    consent_context_from_declared_ui_options,
)

from .errors import ApiError
from .repository import JourneySessionRepository
from .schemas import JourneySessionCreate


class JourneySessionService:
    def __init__(self, repository: JourneySessionRepository) -> None:
        self.repository = repository

    def create(self, request: JourneySessionCreate) -> dict:
        normalized = _normalize_options(request.declared_ui_options)
        unsupported = [item for item in normalized if item not in CONSENT_UI_OPTION_TO_SUPPORT]
        if unsupported:
            raise ApiError(
                code="UNSUPPORTED_ASSISTANCE_TYPE",
                message="One or more support options are not supported.",
                status_code=422,
                details={
                    "unsupported": unsupported,
                    "supported": sorted(CONSENT_UI_OPTION_TO_SUPPORT),
                },
            )

        if normalized and not request.consent_to_support_sharing:
            raise ApiError(
                code="CONSENT_REQUIRED",
                message="Consent is required before support needs can be shared.",
                status_code=403,
                details={"field": "consent_to_support_sharing"},
            )

        consent = consent_context_from_declared_ui_options(normalized)
        categories = sorted(category.value for category in consent.active_support_categories)
        record = {
            "session_id": str(uuid4()),
            "passenger_id": request.passenger_id,
            "journey_id": request.journey_id,
            "vehicle_id": request.vehicle_id,
            "declared_ui_options": normalized,
            "support_categories": categories,
            "consent_to_support_sharing": request.consent_to_support_sharing,
            "consent_enhanced_supervision": request.consent_enhanced_supervision,
            "stop_request": request.stop_request,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.repository.create(record)

    def get(self, session_id: str) -> dict:
        record = self.repository.get(session_id)
        if record is None:
            raise ApiError(
                code="JOURNEY_NOT_FOUND",
                message="Journey session was not found.",
                status_code=404,
                details={"session_id": session_id},
            )
        return record


def _normalize_options(options: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in options:
        normalized = _normalize_ui_token(raw)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def with_engine_input(record: dict) -> dict:
    return {
        **record,
        "engine_input": {
            "support_categories": record["support_categories"] or ["undeclared"],
            "passenger_event": {
                "stop_request": record["stop_request"],
                "source": "app",
                "consented": record["consent_to_support_sharing"],
            },
            "consent_enhanced_supervision": record["consent_enhanced_supervision"],
        },
    }

