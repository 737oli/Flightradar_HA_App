"""Domain models for the flight tracker integration."""

from .api_usage import ApiUsageSnapshot
from .flight import FlightEvent
from .roster import RosterEvent
from .snapshot import FlightTrackerSnapshot
from .status import FlightStatus
from .travel_status import TravelStatusSummary
from .trip_timeline import TripTimelineSummary

__all__ = [
    "ApiUsageSnapshot",
    "FlightEvent",
    "FlightStatus",
    "FlightTrackerSnapshot",
    "RosterEvent",
    "TravelStatusSummary",
    "TripTimelineSummary",
]
