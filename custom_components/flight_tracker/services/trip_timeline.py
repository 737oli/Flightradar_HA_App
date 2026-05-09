"""Trip timeline helpers for iCal Flight Tracker."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

from ..models.roster import RosterEvent
from ..models.status import FlightStatus
from ..models.trip_timeline import TripTimelineSummary

BASE_AIRPORT = "AMS"
LAYOVER_MINIMUM = timedelta(minutes=20)
BASE_RETURN_MINIMUM = timedelta(minutes=10)
AIRPORT_DISPLAY_NAMES = {
    "AMS": "Amsterdam",
    "BIO": "Bilbao",
    "BRU": "Brussels",
    "DBV": "Dubrovnik",
    "JFK": "New York",
    "KRK": "Krakow",
    "LHR": "London Heathrow",
    "LIN": "Milan Linate",
    "MME": "Teesside",
    "STR": "Stuttgart",
}


def build_trip_timeline(
    events: list[RosterEvent],
    statuses: dict[str, FlightStatus],
    now: datetime,
) -> TripTimelineSummary:
    """Build a timeline for the most relevant roster day."""
    if not events:
        return _empty_timeline("No roster events", "No travel day found.", now)

    anchor = _anchor_event(events, now)
    if anchor is None:
        return _empty_timeline("No travel day", "No travel day found.", now)

    tzinfo = now.tzinfo or timezone.utc
    day_anchor = now if anchor.start <= now <= anchor.end else anchor.start
    day_start, day_end = _day_bounds(day_anchor, tzinfo)
    day_events = [
        event for event in events if event.end > day_start and event.start < day_end
    ]
    duty_events = [event for event in day_events if event.kind == "duty"]
    duty_start = min((event.start for event in duty_events), default=None)
    duty_end = max((event.end for event in duty_events), default=None)

    segment_events = _segment_events(day_events)
    segments = _segments_from_events(segment_events, statuses, now, duty_end)
    current_segment = _current_segment(segments)
    previous_flight = _previous_flight(segments)
    current_flight = _current_flight_segment(segments)
    next_flight = _next_flight(segments)
    flight_segments = [segment for segment in segments if segment["kind"] == "flight"]
    origin = _first_value(segment.get("departure_airport") for segment in flight_segments)
    destination = _last_value(segment.get("arrival_airport") for segment in flight_segments)
    hotel = next((segment for segment in segments if segment["kind"] == "hotel"), None)
    has_base_return = any(segment["kind"] == "base_return" for segment in segments)

    headline = _headline(segments)
    detail = _detail(segments)
    phase = _phase(segments, now, day_start, day_end)
    native_value = _native_value(current_segment, next_flight, destination, headline)

    return TripTimelineSummary(
        native_value=native_value,
        headline=headline,
        detail=detail,
        phase=phase,
        day_start=day_start,
        day_end=day_end,
        duty_start=duty_start,
        duty_end=duty_end,
        origin=origin,
        destination=destination,
        segments=segments,
        current_segment=current_segment,
        previous_flight=previous_flight,
        current_flight=current_flight,
        next_flight=next_flight,
    )


def _empty_timeline(headline: str, detail: str, now: datetime) -> TripTimelineSummary:
    """Return an empty timeline summary."""
    day_start, day_end = _day_bounds(now, now.tzinfo or timezone.utc)
    return TripTimelineSummary(
        native_value=headline,
        headline=headline,
        detail=detail,
        phase="idle",
        day_start=day_start,
        day_end=day_end,
        duty_start=None,
        duty_end=None,
        origin=None,
        destination=None,
        segments=[],
        current_segment=None,
        previous_flight=None,
        current_flight=None,
        next_flight=None,
    )


def _anchor_event(events: list[RosterEvent], now: datetime) -> RosterEvent | None:
    """Return the event that defines the displayed travel day."""
    meaningful = [event for event in events if event.kind != "off"] or events
    active = [event for event in meaningful if event.start <= now <= event.end]
    if active:
        return sorted(active, key=_anchor_priority)[0]

    upcoming = [event for event in meaningful if event.start > now]
    if upcoming:
        return min(upcoming, key=lambda event: event.start)

    previous = [event for event in meaningful if event.end < now]
    return max(previous, key=lambda event: event.end) if previous else None


def _anchor_priority(event: RosterEvent) -> tuple[int, float]:
    """Sort active events by usefulness as a timeline anchor."""
    priorities = {
        "flight": 0,
        "ground_time": 1,
        "transfer": 1,
        "hotel": 2,
        "duty": 3,
        "training": 4,
        "event": 5,
        "off": 6,
    }
    duration = (event.end - event.start).total_seconds()
    return priorities.get(event.kind, 5), duration


def _day_bounds(value: datetime, tzinfo: timezone) -> tuple[datetime, datetime]:
    """Return local day bounds for a datetime."""
    local_date = value.astimezone(tzinfo).date()
    start = datetime.combine(local_date, time.min, tzinfo=tzinfo)
    return start, start + timedelta(days=1)


def _segment_events(events: list[RosterEvent]) -> list[RosterEvent]:
    """Return events that should be shown as timeline rows."""
    display_kinds = {
        "flight",
        "ground_time",
        "hotel",
        "transfer",
        "training",
        "event",
    }
    segments = [event for event in events if event.kind in display_kinds]
    if segments:
        return sorted(segments, key=lambda event: (event.start, event.end))
    return sorted(
        [event for event in events if event.kind == "off"],
        key=lambda event: (event.start, event.end),
    )


def _segments_from_events(
    events: list[RosterEvent],
    statuses: dict[str, FlightStatus],
    now: datetime,
    duty_end: datetime | None,
) -> list[dict[str, Any]]:
    """Return display segments with synthetic gaps/base return inserted."""
    segments: list[dict[str, Any]] = []
    previous_flight: RosterEvent | None = None

    for event in events:
        if event.kind == "flight" and previous_flight is not None:
            layover = _layover_segment(previous_flight, event, events, statuses, now)
            if layover:
                segments.append(layover)

        segments.append(_segment_from_event(event, statuses.get(event.uid), now))

        if event.kind == "flight":
            previous_flight = event
        elif event.kind in {"hotel", "training", "off"}:
            previous_flight = None

    base_return = _base_return_segment(events, statuses, now, duty_end)
    if base_return:
        segments.append(base_return)

    return sorted(segments, key=lambda segment: (segment["start"], segment["end"]))


def _segment_from_event(
    event: RosterEvent,
    status: FlightStatus | None,
    now: datetime,
) -> dict[str, Any]:
    """Return a serializable timeline segment from a roster event."""
    start = _effective_start(event, status)
    end = _effective_end(event, status)
    title, detail = _title_detail(event, status)
    segment = {
        "uid": event.uid,
        "kind": event.kind,
        "title": title,
        "detail": detail,
        "status": _status_label(event, status, start, end, now),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "duration_minutes": _duration_minutes(start, end),
        "phase": _segment_phase(start, end, now),
        "airport": event.airport,
        "flight_number": event.flight_number,
        "route": event.route,
        "departure_airport": event.departure_airport,
        "arrival_airport": event.arrival_airport,
        "aircraft_type": event.aircraft_type,
        "is_deadhead": event.is_deadhead,
        "url": event.url or None,
    }
    if event.kind == "flight":
        segment.update(
            {
                "scheduled_start": event.start.isoformat(),
                "scheduled_end": event.end.isoformat(),
                "departure_time_delta_minutes": _time_delta_minutes(
                    event.start,
                    start,
                    status.departure_delay_minutes if status else None,
                ),
                "arrival_time_delta_minutes": _time_delta_minutes(
                    event.end,
                    end,
                    status.arrival_delay_minutes if status else None,
                ),
            }
        )
    return {key: value for key, value in segment.items() if value is not None}


def _layover_segment(
    previous: RosterEvent,
    upcoming: RosterEvent,
    events: list[RosterEvent],
    statuses: dict[str, FlightStatus],
    now: datetime,
) -> dict[str, Any] | None:
    """Return a synthetic layover segment between two flights."""
    if _has_roster_gap_segment(previous, upcoming, events):
        return None

    start = _effective_end(previous, statuses.get(previous.uid))
    end = _effective_start(upcoming, statuses.get(upcoming.uid))
    if end - start < LAYOVER_MINIMUM:
        return None

    airport = previous.arrival_airport or upcoming.departure_airport
    detail = f"Between {previous.flight_number} and {upcoming.flight_number}"
    return _synthetic_segment(
        uid=f"layover-{previous.uid}-{upcoming.uid}",
        kind="layover",
        title=f"Layover {airport}" if airport else "Layover",
        detail=detail,
        status=_duration_label(start, end),
        start=start,
        end=end,
        now=now,
        airport=airport,
    )


def _has_roster_gap_segment(
    previous: RosterEvent,
    upcoming: RosterEvent,
    events: list[RosterEvent],
) -> bool:
    """Return whether a roster row already describes the time between flights."""
    gap_start = previous.end
    gap_end = upcoming.start
    if gap_end <= gap_start:
        return False

    for event in events:
        if event.uid in {previous.uid, upcoming.uid} or event.kind == "flight":
            continue
        if event.end <= gap_start or event.start >= gap_end:
            continue
        return True

    return False


def _base_return_segment(
    events: list[RosterEvent],
    statuses: dict[str, FlightStatus],
    now: datetime,
    duty_end: datetime | None,
) -> dict[str, Any] | None:
    """Return a synthetic base return segment after the final AMS arrival."""
    flights = [event for event in events if event.kind == "flight"]
    if not flights:
        return None

    last_flight = max(flights, key=lambda event: event.end)
    if last_flight.arrival_airport != BASE_AIRPORT:
        return None
    if any(event.kind == "hotel" and event.start >= last_flight.end for event in events):
        return None

    start = _effective_end(last_flight, statuses.get(last_flight.uid))
    end = duty_end or start
    if end - start < BASE_RETURN_MINIMUM:
        return None

    return _synthetic_segment(
        uid=f"base-return-{last_flight.uid}",
        kind="base_return",
        title="Back at Amsterdam",
        detail="",
        status=_duration_label(start, end),
        start=start,
        end=end,
        now=now,
        airport=BASE_AIRPORT,
    )


def _synthetic_segment(
    uid: str,
    kind: str,
    title: str,
    detail: str,
    status: str,
    start: datetime,
    end: datetime,
    now: datetime,
    airport: str | None,
) -> dict[str, Any]:
    """Return a serializable synthetic segment."""
    return {
        "uid": uid,
        "kind": kind,
        "title": title,
        "detail": detail,
        "status": status,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "duration_minutes": _duration_minutes(start, end),
        "phase": _segment_phase(start, end, now),
        "airport": airport,
    }


def _effective_start(event: RosterEvent, status: FlightStatus | None) -> datetime:
    """Return live-adjusted segment start."""
    if event.kind != "flight" or status is None:
        return event.start
    return status.actual_departure or status.estimated_departure or event.start


def _effective_end(event: RosterEvent, status: FlightStatus | None) -> datetime:
    """Return live-adjusted segment end."""
    if event.kind != "flight" or status is None:
        return event.end
    return status.actual_arrival or status.estimated_arrival or event.end


def _title_detail(
    event: RosterEvent,
    status: FlightStatus | None,
) -> tuple[str, str]:
    """Return title and detail for a roster event."""
    if event.kind == "flight":
        prefix = f"DH/{event.flight_number}" if event.is_deadhead else event.flight_number
        detail_parts = [
            _display_route(event.route),
            status.aircraft_type if status else event.aircraft_type,
        ]
        return prefix or event.title, " · ".join(part for part in detail_parts if part)
    if event.kind == "hotel":
        place = f" in {event.airport}" if event.airport else ""
        return event.title, f"Overnight{place}"
    if event.kind == "ground_time":
        return event.title, event.location or "Ground time"
    if event.kind == "transfer":
        return event.title, ""
    return event.title, event.location


def _status_label(
    event: RosterEvent,
    status: FlightStatus | None,
    start: datetime,
    end: datetime,
    now: datetime,
) -> str | None:
    """Return a compact segment status."""
    is_current = start <= now <= end
    if event.kind == "flight":
        delay = _max_delay(status)
        if delay and delay > 5:
            return f"Delayed {delay}m"
        if is_current and status and status.status:
            return status.status
        return "Now" if is_current else None
    if event.kind == "hotel" and start <= now <= end:
        return "At hotel"
    if is_current:
        return "Now"
    return None


def _segment_phase(start: datetime, end: datetime, now: datetime) -> str:
    """Return timeline phase for a segment."""
    if start <= now <= end:
        return "current"
    if end < now:
        return "past"
    return "next"


def _duration_minutes(start: datetime, end: datetime) -> int:
    """Return rounded segment duration in minutes."""
    return max(0, round((end - start).total_seconds() / 60))


def _duration_label(start: datetime, end: datetime) -> str:
    """Return a short duration label."""
    minutes = _duration_minutes(start, end)
    hours = minutes // 60
    remainder = minutes % 60
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def _display_route(route: str | None) -> str | None:
    """Return a softer route separator for timeline display."""
    if not route:
        return None
    return route.replace(" -> ", " - ")


def _time_delta_minutes(
    scheduled: datetime,
    live: datetime,
    provider_delta: int | None,
) -> int | None:
    """Return the displayed live-time delta for a scheduled time."""
    if provider_delta is not None:
        return provider_delta
    delta = round((live - scheduled).total_seconds() / 60)
    return delta if delta else None


def _max_delay(status: FlightStatus | None) -> int | None:
    """Return the largest positive delay from a flight status."""
    if status is None:
        return None
    delays = [
        delay
        for delay in (status.departure_delay_minutes, status.arrival_delay_minutes)
        if delay is not None and delay > 0
    ]
    return max(delays) if delays else None


def _current_segment(segments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the active segment."""
    return next((segment for segment in segments if segment["phase"] == "current"), None)


def _previous_flight(segments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the latest past flight segment."""
    flights = [
        segment
        for segment in segments
        if segment["kind"] == "flight" and segment["phase"] == "past"
    ]
    return flights[-1] if flights else None


def _current_flight_segment(segments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the current flight segment."""
    return next(
        (
            segment
            for segment in segments
            if segment["kind"] == "flight" and segment["phase"] == "current"
        ),
        None,
    )


def _next_flight(segments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the next upcoming flight segment."""
    return next(
        (
            segment
            for segment in segments
            if segment["kind"] == "flight" and segment["phase"] == "next"
        ),
        None,
    )


def _headline(
    segments: list[dict[str, Any]],
) -> str:
    """Return the timeline headline."""
    return "Travel day" if segments else "Roster day"


def _detail(segments: list[dict[str, Any]]) -> str:
    """Return a concise timeline detail in travel-day order."""
    parts: list[str] = []
    pending_flights = 0

    def flush_flights() -> None:
        nonlocal pending_flights
        if pending_flights:
            parts.append(
                f"{pending_flights} flight{'s' if pending_flights != 1 else ''}"
            )
            pending_flights = 0

    for segment in segments:
        kind = segment["kind"]
        if kind == "flight":
            pending_flights += 1
            continue
        if kind in {"transfer", "ground_time", "layover"}:
            continue

        flush_flights()
        if kind == "hotel":
            parts.append(_hotel_detail(segment))
        elif kind == "base_return":
            parts.append("base return")

    flush_flights()
    return " · ".join(parts) if parts else "No flights on this roster day"


def _hotel_detail(segment: dict[str, Any]) -> str:
    """Return a human-friendly hotel summary."""
    airport = str(segment.get("airport") or "").upper()
    place = AIRPORT_DISPLAY_NAMES.get(airport, airport)
    return f"Hotel {place}" if place else "Hotel"


def _phase(
    segments: list[dict[str, Any]],
    now: datetime,
    day_start: datetime,
    day_end: datetime,
) -> str:
    """Return whole-day phase."""
    if any(segment["phase"] == "current" for segment in segments):
        return "current"
    if now < day_start:
        return "upcoming"
    if now > day_end:
        return "past"
    return "between"


def _native_value(
    current_segment: dict[str, Any] | None,
    next_flight: dict[str, Any] | None,
    destination: str | None,
    headline: str,
) -> str:
    """Return the sensor state."""
    if current_segment:
        return str(current_segment["title"])
    if next_flight:
        return f"Next: {next_flight['title']}"
    if destination:
        return f"Done: {destination}"
    return headline


def _first_value(values) -> str | None:
    """Return the first non-empty value from an iterable."""
    return next((value for value in values if value), None)


def _last_value(values) -> str | None:
    """Return the last non-empty value from an iterable."""
    found = None
    for value in values:
        if value:
            found = value
    return found
