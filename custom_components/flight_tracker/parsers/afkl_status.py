"""Parse Air France-KLM flight status responses."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..models.flight import FlightEvent
from ..models.status import FlightStatus


def status_from_flight(
    event: FlightEvent,
    flight: dict[str, Any],
    observed_at: datetime | None = None,
) -> FlightStatus:
    """Build a status object from Air France-KLM data."""
    if observed_at is None:
        observed_at = datetime.now(timezone.utc)
    elif observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    leg = _first_leg(flight)
    departure = _get_dict(leg, "departureInformation")
    arrival = _get_dict(leg, "arrivalInformation")
    departure_times = _get_dict(departure, "times")
    arrival_times = _get_dict(arrival, "times")
    departure_places = _get_dict(_get_dict(departure, "airport"), "places")
    arrival_places = _get_dict(_get_dict(arrival, "airport"), "places")
    aircraft = _get_dict(leg, "aircraft")
    irregularity = _get_dict(leg, "irregularity")
    delay_information = _first_dict_item(irregularity.get("delayInformation"))
    trajectory = _latest_trajectory(leg)
    location = _get_dict(trajectory, "location")
    time_to_arrival_minutes = _duration_minutes(leg.get("timeToArrival"))

    scheduled_departure = (
        _parse_datetime(departure_times.get("scheduled")) or event.start
    )
    estimated_departure = (
        _parse_datetime(_estimated_value(departure_times.get("estimated")))
        or _parse_datetime(departure_times.get("latestPublished"))
        or _parse_datetime(departure_times.get("estimatedPublic"))
        or _parse_datetime(departure_times.get("modified"))
        or _parse_datetime(departure_times.get("targetOffBlock"))
        or _parse_datetime(departure_times.get("departureSlotTime"))
        or _parse_datetime(departure_times.get("estimatedTakeOffTime"))
    )
    actual_departure = (
        _parse_datetime(departure_times.get("actual"))
        or _parse_datetime(departure_times.get("actualTakeOffTime"))
    )

    scheduled_arrival = _parse_datetime(arrival_times.get("scheduled")) or event.end
    actual_arrival = (
        _parse_datetime(arrival_times.get("actual"))
        or _parse_datetime(arrival_times.get("aircraftOnPosition"))
    )
    time_to_arrival_eta = (
        observed_at.astimezone(timezone.utc) + timedelta(minutes=time_to_arrival_minutes)
        if time_to_arrival_minutes is not None and actual_arrival is None
        else None
    )
    estimated_arrival = (
        _parse_datetime(_estimated_value(arrival_times.get("estimated")))
        or _parse_datetime(arrival_times.get("latestPublished"))
        or _parse_datetime(arrival_times.get("estimatedPublic"))
        or _parse_datetime(arrival_times.get("estimatedArrival"))
        or _parse_datetime(arrival_times.get("estimatedInternal"))
        or _parse_datetime(arrival_times.get("modified"))
        or time_to_arrival_eta
        or _parse_datetime(arrival_times.get("estimatedTouchDownTime"))
    )
    arrival_delay = _first_integer(
        _duration_minutes(irregularity.get("delayDurationArrival")),
        _delay_minutes(scheduled_arrival, actual_arrival or estimated_arrival),
    )

    return FlightStatus(
        ident=event.flight_number or str(flight.get("id") or ""),
        source="airfranceklm",
        status=_status_text(flight, leg),
        provider_flight_id=_string(flight.get("id")),
        actual_departure=actual_departure,
        estimated_departure=estimated_departure,
        actual_arrival=actual_arrival,
        estimated_arrival=estimated_arrival,
        departure_delay_minutes=_delay_minutes(
            scheduled_departure, actual_departure or estimated_departure
        ),
        arrival_delay_minutes=arrival_delay,
        departure_terminal=_first_string(
            departure_places.get("terminalCode"),
            departure_places.get("departureTerminal"),
            departure_places.get("boardingTerminal"),
        ),
        departure_gate=_first_list_item(departure_places.get("gateNumber")),
        arrival_terminal=_first_string(
            arrival_places.get("terminalCode"),
            arrival_places.get("arrivalTerminal"),
            arrival_places.get("arrivalPositionTerminal"),
        ),
        arrival_gate=_first_list_item(arrival_places.get("gateNumber")),
        aircraft_registration=_string(aircraft.get("registration")),
        aircraft_type=_first_string(aircraft.get("typeCode"), aircraft.get("typeName")),
        delay_code=_first_string(
            delay_information.get("delayCode"),
            _first_list_item(irregularity.get("delayCode")),
        ),
        delay_sub_code=_first_string(
            delay_information.get("delaySubCode"),
            _first_list_item(irregularity.get("delaySubCode")),
        ),
        delay_duration=_first_string(
            delay_information.get("delayDuration"),
            _first_list_item(irregularity.get("delayDuration")),
        ),
        delay_duration_arrival=_first_string(irregularity.get("delayDurationArrival")),
        delay_duration_public=_first_string(irregularity.get("delayDurationPublic")),
        delay_reason=_first_string(
            delay_information.get("delayReason"),
            _first_list_item(irregularity.get("delayReason")),
        ),
        delay_reason_public=_first_string(
            delay_information.get("delayReasonPublicShort"),
            delay_information.get("delayReasonPublicLong"),
            _first_list_item(irregularity.get("delayReasonPublicLangTransl")),
            _first_list_item(irregularity.get("delayReasonPublic")),
        ),
        delay_reason_code_public=_first_string(
            delay_information.get("delayReasonCodePublic"),
            _first_list_item(irregularity.get("delayReasonCodePublic")),
        ),
        public_disruption_reason=_first_string(
            irregularity.get("publicDisruptionReason")
        ),
        latitude=_number(location, "latitude"),
        longitude=_number(location, "longitude"),
        altitude_ft=_integer(location, "altitude"),
        progress_percent=_integer(leg, "completionPercentage"),
        position_time=_parse_datetime(trajectory.get("aircraftPositionTime")),
    )


def _first_leg(flight: dict[str, Any]) -> dict[str, Any]:
    """Return the first flight leg."""
    legs = flight.get("flightLegs")
    if isinstance(legs, list):
        for leg in legs:
            if isinstance(leg, dict):
                return leg
    return {}


def _latest_trajectory(leg: dict[str, Any]) -> dict[str, Any]:
    """Return the most recent trajectory entry."""
    trajectories = leg.get("trajectories")
    if not isinstance(trajectories, list):
        return {}
    trajectory_items = [
        item for item in trajectories if isinstance(item, dict) and item.get("location")
    ]
    if not trajectory_items:
        return {}
    return max(
        trajectory_items,
        key=lambda item: _parse_datetime(item.get("aircraftPositionTime"))
        or datetime.min.replace(tzinfo=timezone.utc),
    )


def _status_text(flight: dict[str, Any], leg: dict[str, Any]) -> str | None:
    """Return the most useful public status text."""
    for value in (
        leg.get("legStatusPublicLangTransl"),
        leg.get("statusName"),
        leg.get("publishedStatus"),
        leg.get("legStatusPublic"),
        flight.get("flightStatusPublicLangTransl"),
        flight.get("flightStatusPublic"),
    ):
        if value:
            return str(value)
    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO timestamp into an aware datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _estimated_value(value: Any) -> Any:
    """Return the value field from an AF-KLM estimated object."""
    if isinstance(value, dict):
        return value.get("value")
    return value


def _delay_minutes(scheduled: datetime | None, actual: datetime | None) -> int | None:
    """Return delay in minutes."""
    if not scheduled or not actual:
        return None
    return round((actual - scheduled).total_seconds() / 60)


def _duration_minutes(value: Any) -> int | None:
    """Return minutes from an AF-KLM duration value."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return round(float(value))

    text = str(value).strip().upper()
    if not text:
        return None
    if text.lstrip("+-").isdigit():
        return int(text)

    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("+-")
    if not text.startswith("P"):
        return None

    date_part, _, time_part = text[1:].partition("T")
    total = 0.0
    number = ""
    for char in date_part:
        if char.isdigit() or char == ".":
            number += char
        elif char == "D" and number:
            total += float(number) * 24 * 60
            number = ""

    number = ""
    for char in time_part:
        if char.isdigit() or char == ".":
            number += char
        elif char == "H" and number:
            total += float(number) * 60
            number = ""
        elif char == "M" and number:
            total += float(number)
            number = ""
        elif char == "S" and number:
            total += float(number) / 60
            number = ""

    return sign * round(total)


def _get_dict(data: dict[str, Any] | None, key: str) -> dict[str, Any]:
    """Safely read a nested dict."""
    if not data:
        return {}
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _number(data: dict[str, Any] | None, key: str) -> float | None:
    """Read a float from a dict."""
    if not data:
        return None
    value = data.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(data: dict[str, Any] | None, key: str) -> int | None:
    """Read an int from a dict."""
    if not data:
        return None
    value = data.get(key)
    if value is None:
        return None
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None


def _first_string(*values: Any) -> str | None:
    """Return the first non-empty string value."""
    for value in values:
        if value:
            return str(value)
    return None


def _first_integer(*values: int | None) -> int | None:
    """Return the first integer value, allowing zero."""
    for value in values:
        if value is not None:
            return value
    return None


def _first_list_item(value: Any) -> str | None:
    """Return the first item from a list, or the value itself."""
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def _first_dict_item(value: Any) -> dict[str, Any]:
    """Return the first dict from a list, or an empty dict."""
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return {}


def _string(value: Any) -> str | None:
    """Return a string or None."""
    return str(value) if value else None
