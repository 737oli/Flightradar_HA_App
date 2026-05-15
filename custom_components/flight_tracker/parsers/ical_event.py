"""Shared iCal VEVENT parsing helpers."""

from __future__ import annotations

from datetime import date, datetime, time, tzinfo
import re
from typing import Any

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


def event_text(value: Any) -> str:
    """Return clean text from an iCal property."""
    if value is None:
        return ""
    return str(value).strip()


def event_datetime(value: Any, default_tz: tzinfo) -> datetime | None:
    """Convert an iCal date or datetime into an aware datetime."""
    if value is None:
        return None

    raw = getattr(value, "dt", value)
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=default_tz)
    if isinstance(raw, date):
        return datetime.combine(raw, time.min, tzinfo=default_tz)
    return None


def event_is_all_day(value: Any) -> bool:
    """Return whether an iCal datetime property is an all-day date."""
    raw = getattr(value, "dt", value)
    return isinstance(raw, date) and not isinstance(raw, datetime)


def extract_flight_metadata(
    summary: str,
    description: str,
    location: str,
) -> tuple[str | None, str | None, str | None, str | None, bool]:
    """Extract shared flight metadata from a VEVENT's text fields."""
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

    return flight_number, airline_code, departure, arrival, is_deadhead


def extract_aircraft_type(text: str) -> str | None:
    """Extract an aircraft type from roster location text."""
    match = AIRCRAFT_RE.search(text.upper())
    return match.group(1).upper() if match else None


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
