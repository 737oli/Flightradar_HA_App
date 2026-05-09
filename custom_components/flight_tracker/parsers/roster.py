"""Parse iCal roster events for the trip timeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
import re
from typing import Any

from icalendar import Calendar

from ..models.roster import RosterEvent
from .ical_event import (
    KLM_AIRLINE_CODE,
    event_datetime,
    event_is_all_day,
    event_text,
    extract_aircraft_type,
    extract_flight_metadata,
)


def parse_roster_events(
    ics_text: str,
    now: datetime,
    lookahead: timedelta,
    default_tz: tzinfo = timezone.utc,
) -> list[RosterEvent]:
    """Parse roster events from iCal text for the trip timeline."""
    calendar = Calendar.from_ical(ics_text)
    start_cutoff = now - timedelta(days=2)
    end_cutoff = now + lookahead
    events: list[RosterEvent] = []

    for component in calendar.walk("VEVENT"):
        event = _parse_roster_event(component, default_tz)
        if event is None:
            continue
        if event.end < start_cutoff or event.start > end_cutoff:
            continue
        events.append(event)

    return sorted(events, key=lambda event: (event.start, event.end, event.summary))


def _parse_roster_event(component: Any, default_tz: tzinfo) -> RosterEvent | None:
    """Parse a single iCal VEVENT into a roster event."""
    summary = event_text(component.get("summary"))
    description = event_text(component.get("description"))
    location = event_text(component.get("location"))
    url = event_text(component.get("url"))
    start_value = component.get("dtstart")
    start = event_datetime(start_value, default_tz)
    end = event_datetime(component.get("dtend"), default_tz)

    if start is None:
        return None
    if end is None:
        end = start + timedelta(hours=2)

    flight_number, airline_code, departure, arrival, is_deadhead = (
        extract_flight_metadata(summary, description, location)
    )

    kind = _event_kind(summary, flight_number, airline_code)
    airport = _event_airport(summary, kind, departure, arrival)
    uid = event_text(component.get("uid")) or f"{summary}-{start.isoformat()}"

    return RosterEvent(
        uid=uid,
        summary=summary,
        description=description,
        location=location,
        url=url,
        start=start,
        end=end,
        kind=kind,
        title=_event_title(summary, kind, flight_number, departure, arrival),
        airport=airport,
        flight_number=flight_number,
        airline_code=airline_code,
        departure_airport=departure,
        arrival_airport=arrival,
        aircraft_type=extract_aircraft_type(location),
        is_deadhead=is_deadhead,
        is_all_day=event_is_all_day(start_value),
    )


def _event_kind(
    summary: str,
    flight_number: str | None,
    airline_code: str | None,
) -> str:
    """Classify a roster event for timeline display."""
    normalized = summary.strip().upper()
    if flight_number and airline_code == KLM_AIRLINE_CODE:
        return "flight"
    if normalized == "FLIGHT DAY":
        return "duty"
    if normalized.startswith(
        ("OMDRAAI", "GRONDTIJD", "GROUND TIME", "GROUNDTIME", "TURNAROUND")
    ):
        return "ground_time"
    if normalized.startswith("HOTEL"):
        return "hotel"
    if normalized in {"TAXI", "PICKUP"}:
        return "transfer"
    if normalized.startswith(("LV", "OFF")):
        return "off"
    if normalized.startswith("TSL") or "SESSIE" in normalized:
        return "training"
    return "event"


def _event_airport(
    summary: str,
    kind: str,
    departure: str | None,
    arrival: str | None,
) -> str | None:
    """Return the airport or city code most closely tied to an event."""
    if kind == "hotel":
        match = re.match(r"Hotel\s+([A-Z]{3})\b", summary, re.IGNORECASE)
        return match.group(1).upper() if match else None
    if kind == "flight":
        return arrival or departure
    return None


def _event_title(
    summary: str,
    kind: str,
    flight_number: str | None,
    departure: str | None,
    arrival: str | None,
) -> str:
    """Return a concise timeline title."""
    if kind == "flight" and flight_number:
        route = f" {departure} -> {arrival}" if departure and arrival else ""
        return f"{flight_number}{route}"
    return summary
