"""Deprecated compatibility exports for iCal parsing.

These root-level imports are kept temporarily for older local consumers and are
planned for removal in v0.7.0. New integration code should import from
``flight_tracker.models.flight``, ``flight_tracker.models.roster``,
``flight_tracker.parsers.ical``, and ``flight_tracker.parsers.roster`` directly.
"""

from __future__ import annotations

from .models.flight import FlightEvent
from .models.roster import RosterEvent
from .parsers.ical import KLM_AIRLINE_CODE, parse_flights
from .parsers.roster import parse_roster_events

__all__ = [
    "KLM_AIRLINE_CODE",
    "FlightEvent",
    "RosterEvent",
    "parse_flights",
    "parse_roster_events",
]
