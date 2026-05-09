"""Friendly travel status summaries for iCal Flight Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..parsers.afkl_status import FlightStatus
from ..parsers.ical import FlightEvent

DELAY_THRESHOLD_MINUTES = 5
BOARDING_SOON = timedelta(minutes=45)
DEPARTING_SOON = timedelta(minutes=15)
ARRIVING_SOON = timedelta(minutes=30)


@dataclass(frozen=True)
class TravelStatusSummary:
    """User-friendly flight status for dashboards and notifications."""

    native_value: str
    phase: str
    headline: str
    detail: str
    notification_title: str
    notification_message: str
    notification_key: str
    severity: str
    event_uid: str | None = None
    flight_number: str | None = None
    route: str | None = None
    destination: str | None = None
    minutes_until_departure: int | None = None
    minutes_until_arrival: int | None = None
    max_delay_minutes: int | None = None
    is_active: bool = False
    is_airborne: bool = False
    is_arriving_soon: bool = False
    is_delayed: bool = False


def build_travel_status(
    current_flight: FlightEvent | None,
    next_flight: FlightEvent | None,
    current_status: FlightStatus | None,
    next_status: FlightStatus | None,
    now: datetime,
) -> TravelStatusSummary:
    """Build a friendly trip state from coordinator data."""
    event = current_flight or next_flight
    status = current_status if current_flight else next_status
    is_active = current_flight is not None

    if event is None:
        return TravelStatusSummary(
            native_value="No flights planned",
            phase="idle",
            headline="No flights planned",
            detail="Nothing upcoming in the flight calendar.",
            notification_title="No flights planned",
            notification_message="There are no upcoming roster flights right now.",
            notification_key="idle",
            severity="info",
        )

    departure = _departure_time(event, status)
    arrival = _arrival_time(event, status)
    departure_minutes = _minutes_until(departure, now)
    arrival_minutes = _minutes_until(arrival, now)
    max_delay = _max_delay(status)
    is_delayed = max_delay is not None and max_delay > DELAY_THRESHOLD_MINUTES
    is_airborne = bool(status and status.is_airborne)
    is_landed = bool(status and status.actual_arrival) or (
        is_active and arrival_minutes is not None and arrival_minutes < 0
    )
    is_arriving_soon = (
        is_active
        and not is_landed
        and arrival_minutes is not None
        and 0 <= arrival_minutes <= round(ARRIVING_SOON.total_seconds() / 60)
    )

    route = _route(event)
    destination = event.arrival_airport
    context = _context(event, status)

    if is_landed:
        return _summary(
            event,
            phase="landed",
            native_value=f"Landed: {destination}",
            headline=f"Landed in {destination}",
            detail=f"{event.flight_number or 'The flight'} has arrived in {destination}.",
            notification_key=f"landed:{event.uid}",
            severity="success",
            route=route,
            destination=destination,
            departure_minutes=departure_minutes,
            arrival_minutes=arrival_minutes,
            max_delay=max_delay,
            is_active=is_active,
            is_airborne=False,
            is_arriving_soon=False,
            is_delayed=is_delayed,
        )

    if is_arriving_soon:
        detail = f"Landing in {arrival_minutes}m at {destination}."
        if context:
            detail = f"{detail} {context}."
        return _summary(
            event,
            phase="arriving_soon",
            native_value=f"Arriving soon: {destination}",
            headline=f"Arriving in {destination} soon",
            detail=detail,
            notification_key=f"arriving_soon:{event.uid}",
            severity="info",
            route=route,
            destination=destination,
            departure_minutes=departure_minutes,
            arrival_minutes=arrival_minutes,
            max_delay=max_delay,
            is_active=is_active,
            is_airborne=is_airborne,
            is_arriving_soon=True,
            is_delayed=is_delayed,
        )

    if is_airborne:
        detail = f"Airborne to {destination}."
        if arrival_minutes is not None and arrival_minutes >= 0:
            detail = f"{detail} Arrival in {arrival_minutes}m."
        if context:
            detail = f"{detail} {context}."
        return _summary(
            event,
            phase="airborne",
            native_value=f"Airborne: {route}",
            headline=f"Airborne to {destination}",
            detail=detail,
            notification_key=f"airborne:{event.uid}",
            severity="info",
            route=route,
            destination=destination,
            departure_minutes=departure_minutes,
            arrival_minutes=arrival_minutes,
            max_delay=max_delay,
            is_active=is_active,
            is_airborne=True,
            is_arriving_soon=False,
            is_delayed=is_delayed,
        )

    if is_delayed:
        delay_detail = _delay_detail(status, max_delay)
        return _summary(
            event,
            phase="delayed",
            native_value=f"Delayed: {event.flight_number or route}",
            headline=f"{event.flight_number or 'Flight'} is delayed",
            detail=delay_detail,
            notification_key=f"delayed:{event.uid}:{_delay_bucket(max_delay)}",
            severity="warning",
            route=route,
            destination=destination,
            departure_minutes=departure_minutes,
            arrival_minutes=arrival_minutes,
            max_delay=max_delay,
            is_active=is_active,
            is_airborne=False,
            is_arriving_soon=False,
            is_delayed=True,
        )

    if (
        is_active
        and departure_minutes is not None
        and 0 <= departure_minutes <= round(DEPARTING_SOON.total_seconds() / 60)
    ):
        detail = f"Departure to {destination} in {departure_minutes}m."
        if context:
            detail = f"{detail} {context}."
        return _summary(
            event,
            phase="departing_soon",
            native_value=f"Departing soon: {event.flight_number or route}",
            headline=f"Departing soon to {destination}",
            detail=detail,
            notification_key=f"departing_soon:{event.uid}:{_gate_key(status)}",
            severity="info",
            route=route,
            destination=destination,
            departure_minutes=departure_minutes,
            arrival_minutes=arrival_minutes,
            max_delay=max_delay,
            is_active=is_active,
            is_airborne=False,
            is_arriving_soon=False,
            is_delayed=False,
        )

    if (
        is_active
        and departure_minutes is not None
        and 0 <= departure_minutes <= round(BOARDING_SOON.total_seconds() / 60)
    ):
        detail = f"Boarding window for {event.flight_number or route} is coming up."
        if departure_minutes is not None:
            detail = f"{detail} Departure in {departure_minutes}m."
        if context:
            detail = f"{detail} {context}."
        return _summary(
            event,
            phase="boarding_soon",
            native_value=f"Boarding soon: {event.flight_number or route}",
            headline=f"Boarding soon for {event.flight_number or route}",
            detail=detail,
            notification_key=f"boarding_soon:{event.uid}:{_gate_key(status)}",
            severity="info",
            route=route,
            destination=destination,
            departure_minutes=departure_minutes,
            arrival_minutes=arrival_minutes,
            max_delay=max_delay,
            is_active=is_active,
            is_airborne=False,
            is_arriving_soon=False,
            is_delayed=False,
        )

    detail = f"Next flight is {event.flight_number or route} to {destination}."
    if departure_minutes is not None and departure_minutes >= 0:
        detail = f"{detail} Departure in {_duration_label(departure_minutes)}."
    return _summary(
        event,
        phase="upcoming",
        native_value=f"Next flight: {event.flight_number or route}",
        headline=f"Next flight to {destination}",
        detail=detail,
        notification_key=f"upcoming:{event.uid}",
        severity="info",
        route=route,
        destination=destination,
        departure_minutes=departure_minutes,
        arrival_minutes=arrival_minutes,
        max_delay=max_delay,
        is_active=is_active,
        is_airborne=False,
        is_arriving_soon=False,
        is_delayed=False,
    )


def _summary(
    event: FlightEvent,
    *,
    phase: str,
    native_value: str,
    headline: str,
    detail: str,
    notification_key: str,
    severity: str,
    route: str,
    destination: str,
    departure_minutes: int | None,
    arrival_minutes: int | None,
    max_delay: int | None,
    is_active: bool,
    is_airborne: bool,
    is_arriving_soon: bool,
    is_delayed: bool,
) -> TravelStatusSummary:
    """Create a summary with matching notification fields."""
    return TravelStatusSummary(
        native_value=native_value,
        phase=phase,
        headline=headline,
        detail=detail,
        notification_title=headline,
        notification_message=detail,
        notification_key=notification_key,
        severity=severity,
        event_uid=event.uid,
        flight_number=event.flight_number,
        route=route,
        destination=destination,
        minutes_until_departure=departure_minutes,
        minutes_until_arrival=arrival_minutes,
        max_delay_minutes=max_delay,
        is_active=is_active,
        is_airborne=is_airborne,
        is_arriving_soon=is_arriving_soon,
        is_delayed=is_delayed,
    )


def _departure_time(event: FlightEvent, status: FlightStatus | None) -> datetime:
    """Return the best departure time."""
    if status:
        return status.actual_departure or status.estimated_departure or event.start
    return event.start


def _arrival_time(event: FlightEvent, status: FlightStatus | None) -> datetime:
    """Return the best arrival time."""
    if status:
        return status.actual_arrival or status.estimated_arrival or event.end
    return event.end


def _minutes_until(value: datetime, now: datetime) -> int:
    """Return rounded minutes from now until value."""
    return round((value - now.astimezone(value.tzinfo)).total_seconds() / 60)


def _max_delay(status: FlightStatus | None) -> int | None:
    """Return the largest positive delay."""
    if status is None:
        return None
    delays = [
        delay
        for delay in (status.departure_delay_minutes, status.arrival_delay_minutes)
        if delay is not None
    ]
    if not delays:
        return None
    return max(delays)


def _delay_bucket(delay: int | None) -> str:
    """Bucket delay notifications so small minute changes do not chatter."""
    if delay is None:
        return "unknown"
    return str(max(1, (delay + 14) // 15))


def _delay_detail(status: FlightStatus | None, delay: int | None) -> str:
    """Return a human-friendly delay detail."""
    parts = [f"Delayed {delay}m." if delay else "Delayed."]
    if status:
        reason = (
            status.delay_reason_public
            or status.public_disruption_reason
            or status.delay_reason
        )
        if reason:
            parts.append(str(reason))
        code = status.delay_code or status.delay_reason_code_public
        if code:
            parts.append(f"Code {code}.")
    return " ".join(parts)


def _context(event: FlightEvent, status: FlightStatus | None) -> str:
    """Return compact aircraft/gate context."""
    parts: list[str] = []
    if status:
        if status.departure_gate:
            gate = status.departure_gate
            if status.departure_terminal:
                terminal = str(status.departure_terminal)
                terminal = terminal if terminal.startswith("T") else f"T{terminal}"
                gate = f"{terminal} gate {gate}"
            else:
                gate = f"Gate {gate}"
            parts.append(gate)
        if status.aircraft_registration:
            parts.append(status.aircraft_registration)
        if status.aircraft_type:
            parts.append(status.aircraft_type)
    elif event.aircraft_type:
        parts.append(event.aircraft_type)
    return " · ".join(parts)


def _gate_key(status: FlightStatus | None) -> str:
    """Return a stable gate key for notification de-duplication."""
    if not status or not status.departure_gate:
        return "no_gate"
    if status.departure_terminal:
        return f"t{status.departure_terminal}_{status.departure_gate}"
    return status.departure_gate


def _route(event: FlightEvent) -> str:
    """Return the best route label."""
    if event.route:
        return event.route
    if event.departure_airport and event.arrival_airport:
        return f"{event.departure_airport} -> {event.arrival_airport}"
    return event.summary


def _duration_label(total_minutes: int) -> str:
    """Return a compact duration label."""
    minutes = max(0, total_minutes)
    hours = minutes // 60
    remainder = minutes % 60
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"
