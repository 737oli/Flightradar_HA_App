"""Flight calendar models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FlightEvent:
    """A flight-like event parsed from an iCal feed."""

    uid: str
    summary: str
    description: str
    location: str
    start: datetime
    end: datetime
    flight_number: str | None
    airline_code: str | None
    departure_airport: str | None
    arrival_airport: str | None
    aircraft_type: str | None
    is_deadhead: bool

    @property
    def route(self) -> str | None:
        """Return a display route when both airports are known."""
        if self.departure_airport and self.arrival_airport:
            return f"{self.departure_airport} -> {self.arrival_airport}"
        return None

    def as_attributes(self) -> dict[str, Any]:
        """Return Home Assistant-safe attributes."""
        return {
            "uid": self.uid,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "flight_number": self.flight_number,
            "departure_airport": self.departure_airport,
            "arrival_airport": self.arrival_airport,
            "route": self.route,
            "scheduled_departure": self.start.isoformat(),
            "scheduled_arrival": self.end.isoformat(),
            "airline_code": self.airline_code,
            "aircraft_type": self.aircraft_type,
            "is_deadhead": self.is_deadhead,
        }
