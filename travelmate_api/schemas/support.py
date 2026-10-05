from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PassengerSupportRequest(BaseModel):
    """Support options accepted by the existing passenger app adapter.

    Categories are derived by the service, not supplied by the passenger.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    declared_ui_options: list[str] = Field(default_factory=list, max_length=20)
