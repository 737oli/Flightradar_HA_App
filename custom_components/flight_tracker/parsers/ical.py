"""Parse iCal flight events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any

from icalendar import Calendar

from ..models.flight import FlightEvent
from .ical_event import (
    KLM_AIRLINE_CODE,
    event_datetime,
    event_text,
    extract_aircraft_type,
    extract_flight_metadata,
)

def parse_flights(
    ics_text: str,
    now: datetime,
    lookahead: timedelta,
    default_tz: tzinfo = timezone.utc,
) -> list[FlightEvent]:
    """Parse future and active flights from iCal text."""
    calendar = Calendar.from_ical(ics_text)
    start_cutoff = now - timedelta(hours=12)
    end_cutoff = now + lookahead
    flights: list[FlightEvent] = []

    for component in calendar.walk("VEVENT"):
        event = _parse_event(component, default_tz)
        if event is None:
            continue
        if event.end < start_cutoff or event.start > end_cutoff:
            continue
        if event.airline_code != KLM_AIRLINE_CODE or not event.flight_number:
            continue
        flights.append(event)

    return sorted(flights, key=lambda event: event.start)


def _parse_event(component: Any, default_tz: tzinfo) -> FlightEvent | None:
    """Parse a single iCal VEVENT into a flight event."""
    summary = event_text(component.get("summary"))
    description = event_text(component.get("description"))
    location = event_text(component.get("location"))
    start = event_datetime(component.get("dtstart"), default_tz)
    end = event_datetime(component.get("dtend"), default_tz)

    if start is None:
        return None
    if end is None:
        end = start + timedelta(hours=2)

    flight_number, airline_code, departure, arrival, is_deadhead = (
        extract_flight_metadata(summary, description, location)
    )

    uid = event_text(component.get("uid")) or f"{summary}-{start.isoformat()}"
    return FlightEvent(
        uid=uid,
        summary=summary,
        description=description,
        location=location,
        start=start,
        end=end,
        flight_number=flight_number,
        airline_code=airline_code,
        departure_airport=departure,
        arrival_airport=arrival,
        aircraft_type=extract_aircraft_type(location),
        is_deadhead=is_deadhead,
    )
