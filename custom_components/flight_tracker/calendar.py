"""Compatibility exports for iCal parsing.

New integration code should import from ``flight_tracker.parsers.ical`` and
``flight_tracker.parsers.roster`` directly.
"""

from __future__ import annotations

from .parsers.ical import (
    KLM_AIRLINE_CODE,
    FlightEvent,
    parse_flights,
)
from .parsers.roster import RosterEvent, parse_roster_events

__all__ = [
    "KLM_AIRLINE_CODE",
    "FlightEvent",
    "RosterEvent",
    "parse_flights",
    "parse_roster_events",
]
