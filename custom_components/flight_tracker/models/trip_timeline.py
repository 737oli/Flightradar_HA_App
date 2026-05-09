"""Trip timeline models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TimelineSegment:
    """A single typed row in the trip timeline."""

    uid: str
    kind: str
    title: str
    detail: str
    phase: str
    start: datetime
    end: datetime
    duration_minutes: int
    status: str | None = None
    airport: str | None = None
    flight_number: str | None = None
    route: str | None = None
    departure_airport: str | None = None
    arrival_airport: str | None = None
    aircraft_type: str | None = None
    is_deadhead: bool | None = None
    url: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    departure_time_delta_minutes: int | None = None
    arrival_time_delta_minutes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this segment for use in Home Assistant sensor attributes."""
        result: dict[str, Any] = {
            "uid": self.uid,
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
            "status": self.status,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
            "phase": self.phase,
            "airport": self.airport,
            "flight_number": self.flight_number,
            "route": self.route,
            "departure_airport": self.departure_airport,
            "arrival_airport": self.arrival_airport,
            "aircraft_type": self.aircraft_type,
            "is_deadhead": self.is_deadhead,
            "url": self.url,
        }
        if self.scheduled_start is not None:
            result["scheduled_start"] = self.scheduled_start.isoformat()
        if self.scheduled_end is not None:
            result["scheduled_end"] = self.scheduled_end.isoformat()
        if self.departure_time_delta_minutes is not None:
            result["departure_time_delta_minutes"] = self.departure_time_delta_minutes
        if self.arrival_time_delta_minutes is not None:
            result["arrival_time_delta_minutes"] = self.arrival_time_delta_minutes
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True)
class TripTimelineSummary:
    """Home-friendly travel day timeline."""

    native_value: str
    headline: str
    detail: str
    phase: str
    day_start: datetime | None
    day_end: datetime | None
    duty_start: datetime | None
    duty_end: datetime | None
    origin: str | None
    destination: str | None
    segments: list[dict[str, Any]]
    current_segment: dict[str, Any] | None
    previous_flight: dict[str, Any] | None
    current_flight: dict[str, Any] | None
    next_flight: dict[str, Any] | None
