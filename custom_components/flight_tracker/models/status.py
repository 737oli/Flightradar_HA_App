"""Live flight status models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FlightStatus:
    """Live status and position for a flight."""

    ident: str
    source: str
    status: str | None = None
    provider_flight_id: str | None = None
    actual_departure: datetime | None = None
    estimated_departure: datetime | None = None
    actual_arrival: datetime | None = None
    estimated_arrival: datetime | None = None
    departure_delay_minutes: int | None = None
    arrival_delay_minutes: int | None = None
    departure_terminal: str | None = None
    departure_gate: str | None = None
    departure_parking_position: str | None = None
    arrival_terminal: str | None = None
    arrival_gate: str | None = None
    arrival_parking_position: str | None = None
    aircraft_registration: str | None = None
    aircraft_type: str | None = None
    delay_code: str | None = None
    delay_sub_code: str | None = None
    delay_duration: str | None = None
    delay_duration_arrival: str | None = None
    delay_duration_public: str | None = None
    delay_reason: str | None = None
    delay_reason_public: str | None = None
    delay_reason_code_public: str | None = None
    public_disruption_reason: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_ft: int | None = None
    groundspeed_kt: int | None = None
    progress_percent: int | None = None
    position_time: datetime | None = None

    @property
    def is_airborne(self) -> bool:
        """Return whether the status looks airborne."""
        if self.actual_departure and not self.actual_arrival:
            return True
        if not self.status:
            return False
        lowered = self.status.lower()
        return any(
            marker in lowered
            for marker in ("en route", "airborne", "in air", "departed")
        )
