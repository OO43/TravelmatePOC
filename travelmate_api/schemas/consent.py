from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PassengerConsentRequest(BaseModel):
    """Consent flags used by the current journey-session integration."""
    model_config = ConfigDict(extra="forbid")

    consent_to_support_sharing: bool
    consent_enhanced_supervision: bool = False
