"""Coordinator snapshot models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .api_usage import ApiUsageSnapshot
from .flight import FlightEvent
from .roster import RosterEvent
from .status import FlightStatus


@dataclass(frozen=True)
class FlightTrackerSnapshot:
    """Current integration data."""

    flights: list[FlightEvent]
    roster_events: list[RosterEvent]
    current_flight: FlightEvent | None
    next_flight: FlightEvent | None
    statuses: dict[str, FlightStatus]
    api_usage: ApiUsageSnapshot
    last_refresh: datetime

    def status_for(self, event: FlightEvent | None) -> FlightStatus | None:
        """Return live status for a flight event."""
        if event is None:
            return None
        return self.statuses.get(event.uid)
