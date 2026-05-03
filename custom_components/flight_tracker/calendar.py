"""iCal parsing for flight events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
import re
from typing import Any

from icalendar import Calendar

AIRLINE_CODE_PATTERN = r"(?:[A-Z]{2,3}|[A-Z][0-9]|[0-9][A-Z])"
KLM_AIRLINE_CODE = "KL"
FLIGHT_NUMBER_RE = re.compile(
    rf"(?<![A-Z0-9])(({KLM_AIRLINE_CODE})\s?\d{{1,4}}[A-Z]?)(?![A-Z0-9])",
    re.IGNORECASE,
)
ROSTER_SUMMARY_RE = re.compile(
    rf"^(?P<deadhead>DH/)?(?P<flight>(?P<airline>{KLM_AIRLINE_CODE})\s?\d{{1,4}}[A-Z]?)\s+"
    r"(?P<departure>[A-Z]{3})\s*[-–—]\s*(?P<arrival>[A-Z]{3})(?:\s|$)",
    re.IGNORECASE,
)
ROUTE_RE = re.compile(
    r"(?<![A-Z])([A-Z]{3})\s*(?:->|→|\bto\b|-|–|—)\s*([A-Z]{3})(?![A-Z])",
    re.IGNORECASE,
)
AIRCRAFT_RE = re.compile(
    r"\b(A\d{3}[A-Z]?|B\d{3}[A-Z]?|B7\d{2}|E\d{3}|CRJ\d{2,3}|F\d{2,3})\b",
    re.IGNORECASE,
)


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


def _parse_event(component: Any, default_tz: tzinfo) -> FlightEvent | None:
    """Parse a single iCal VEVENT into a flight event."""
    summary = _text(component.get("summary"))
    description = _text(component.get("description"))
    location = _text(component.get("location"))
    start = _datetime(component.get("dtstart"), default_tz)
    end = _datetime(component.get("dtend"), default_tz)

    if start is None:
        return None
    if end is None:
        end = start + timedelta(hours=2)

    search_text = "\n".join([summary, description, location])
    roster_match = ROSTER_SUMMARY_RE.search(summary.upper())
    flight_number = _extract_flight_number(search_text)
    airline_code = _airline_code(flight_number)
    departure, arrival = _extract_route(search_text)
    is_deadhead = summary.upper().startswith("DH/")

    if roster_match:
        flight_number = re.sub(r"\s+", "", roster_match.group("flight").upper())
        airline_code = roster_match.group("airline").upper()
        departure = roster_match.group("departure").upper()
        arrival = roster_match.group("arrival").upper()
        is_deadhead = bool(roster_match.group("deadhead"))

    uid = _text(component.get("uid")) or f"{summary}-{start.isoformat()}"
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
        aircraft_type=_extract_aircraft_type(location),
        is_deadhead=is_deadhead,
    )


def _parse_roster_event(component: Any, default_tz: tzinfo) -> RosterEvent | None:
    """Parse a single iCal VEVENT into a roster event."""
    summary = _text(component.get("summary"))
    description = _text(component.get("description"))
    location = _text(component.get("location"))
    url = _text(component.get("url"))
    start_value = component.get("dtstart")
    start = _datetime(start_value, default_tz)
    end = _datetime(component.get("dtend"), default_tz)

    if start is None:
        return None
    if end is None:
        end = start + timedelta(hours=2)

    search_text = "\n".join([summary, description, location])
    roster_match = ROSTER_SUMMARY_RE.search(summary.upper())
    flight_number = _extract_flight_number(search_text)
    airline_code = _airline_code(flight_number)
    departure, arrival = _extract_route(search_text)
    is_deadhead = summary.upper().startswith("DH/")

    if roster_match:
        flight_number = re.sub(r"\s+", "", roster_match.group("flight").upper())
        airline_code = roster_match.group("airline").upper()
        departure = roster_match.group("departure").upper()
        arrival = roster_match.group("arrival").upper()
        is_deadhead = bool(roster_match.group("deadhead"))

    kind = _event_kind(summary, flight_number, airline_code)
    airport = _event_airport(summary, kind, departure, arrival)
    uid = _text(component.get("uid")) or f"{summary}-{start.isoformat()}"

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
        aircraft_type=_extract_aircraft_type(location),
        is_deadhead=is_deadhead,
        is_all_day=_is_all_day(start_value),
    )


def _datetime(value: Any, default_tz: tzinfo) -> datetime | None:
    """Convert an iCal date or datetime into an aware datetime."""
    if value is None:
        return None

    raw = getattr(value, "dt", value)
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=default_tz)
    if isinstance(raw, date):
        return datetime.combine(raw, time.min, tzinfo=default_tz)
    return None


def _text(value: Any) -> str:
    """Return clean text from an iCal property."""
    if value is None:
        return ""
    return str(value).strip()


def _extract_flight_number(text: str) -> str | None:
    """Extract the first likely airline flight number."""
    match = FLIGHT_NUMBER_RE.search(text.upper())
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1).upper())


def _airline_code(flight_number: str | None) -> str | None:
    """Extract the airline code from a flight number."""
    if not flight_number:
        return None
    match = re.match(rf"({AIRLINE_CODE_PATTERN})\d", flight_number.upper())
    return match.group(1) if match else None


def _extract_route(text: str) -> tuple[str | None, str | None]:
    """Extract IATA airport route text."""
    match = ROUTE_RE.search(text.upper())
    if not match:
        return None, None
    return match.group(1).upper(), match.group(2).upper()


def _extract_aircraft_type(text: str) -> str | None:
    """Extract an aircraft type from roster location text."""
    match = AIRCRAFT_RE.search(text.upper())
    return match.group(1).upper() if match else None


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


def _is_all_day(value: Any) -> bool:
    """Return whether an iCal datetime property is an all-day date."""
    raw = getattr(value, "dt", value)
    return isinstance(raw, date) and not isinstance(raw, datetime)
