"""Roster event models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RosterEvent:
    """A roster event parsed from an iCal feed."""

    uid: str
    summary: str
    description: str
    location: str
    url: str
    start: datetime
    end: datetime
    kind: str
    title: str
    airport: str | None
    flight_number: str | None
    airline_code: str | None
    departure_airport: str | None
    arrival_airport: str | None
    aircraft_type: str | None
    is_deadhead: bool
    is_all_day: bool

    @property
    def route(self) -> str | None:
        """Return a display route when both airports are known."""
        if self.departure_airport and self.arrival_airport:
            return f"{self.departure_airport} -> {self.arrival_airport}"
        return None
