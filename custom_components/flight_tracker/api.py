"""Optional live flight data providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, TYPE_CHECKING
from urllib.parse import quote

from .calendar import FlightEvent

if TYPE_CHECKING:
    from aiohttp import ClientSession

AFKL_BASE_URL = "https://api.airfranceklm.com/opendata/flightstatus/v4"


@dataclass(frozen=True)
class FlightStatus:
    """Live status and position for a flight."""

    ident: str
    source: str
    status: str | None = None
    provider_flight_id: str | None = None
    actual_departure: datetime | None = None
    estimated_departure: datetime | None = None
    actual_arrival: datetime | None = None
    estimated_arrival: datetime | None = None
    departure_delay_minutes: int | None = None
    arrival_delay_minutes: int | None = None
    departure_terminal: str | None = None
    departure_gate: str | None = None
    arrival_terminal: str | None = None
    arrival_gate: str | None = None
    aircraft_registration: str | None = None
    aircraft_type: str | None = None
    delay_code: str | None = None
    delay_sub_code: str | None = None
    delay_duration: str | None = None
    delay_duration_public: str | None = None
    delay_reason: str | None = None
    delay_reason_public: str | None = None
    delay_reason_code_public: str | None = None
    public_disruption_reason: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_ft: int | None = None
    groundspeed_kt: int | None = None
    progress_percent: int | None = None
    position_time: datetime | None = None

    @property
    def is_airborne(self) -> bool:
        """Return whether the status looks airborne."""
        if self.actual_departure and not self.actual_arrival:
            return True
        if not self.status:
            return False
        lowered = self.status.lower()
        return any(
            marker in lowered
            for marker in ("en route", "airborne", "in air", "departed")
        )


class AirFranceKlmClient:
    """Small Air France-KLM Open Data Flight Status API client."""

    def __init__(
        self, session: ClientSession, api_key: str, consumer_host: str = "KL"
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key
        self._consumer_host = consumer_host

    async def async_get_status(self, event: FlightEvent) -> FlightStatus | None:
        """Fetch live status for a calendar flight."""
        if not event.flight_number or not event.airline_code:
            return None

        data = await self._request(
            "/flights",
            {
                "startRange": _utc_iso(event.start - timedelta(hours=8)),
                "endRange": _utc_iso(event.start + timedelta(hours=12)),
                "movementType": "D",
                "timeOriginType": "S",
                "timeType": "U",
                "origin": event.departure_airport,
                "destination": event.arrival_airport,
                "carrierCode": event.airline_code,
                "flightNumber": _numeric_flight_number(event.flight_number),
                "pageSize": 10,
                "pageNumber": 0,
                "consumerHost": self._consumer_host,
            },
        )
        flights = _flight_list(data)
        if not flights:
            return None

        best = min(
            flights,
            key=lambda flight: _time_distance(
                _scheduled_departure(flight),
                event.start,
            ),
        )
        try:
            detailed = await self._async_detail(best, event)
        except Exception:  # noqa: BLE001
            detailed = None
        return _status_from_flight(event, detailed or best)

    async def _async_detail(
        self, flight: dict[str, Any], event: FlightEvent
    ) -> dict[str, Any] | None:
        """Fetch detailed flight status, including trajectory when available."""
        flight_id = flight.get("id")
        if not flight_id:
            return None

        data = await self._request(
            f"/flights/{quote(str(flight_id), safe='')}",
            {
                "origin": event.departure_airport,
                "expand": "trajectory",
                "consumerHost": self._consumer_host,
            },
        )
        return data if isinstance(data, dict) else None

    async def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Request JSON from Air France-KLM."""
        headers = {
            "API-Key": self._api_key,
            "accept": "application/hal+json, application/json",
            "accept-language": "en-GB",
            "afkl-travel-host": self._consumer_host,
        }
        clean_params = {
            key: value for key, value in params.items() if value not in (None, "")
        }
        async with self._session.get(
            f"{AFKL_BASE_URL}{path}",
            headers=headers,
            params=clean_params,
            timeout=20,
        ) as response:
            response.raise_for_status()
            return await response.json(content_type=None)


def _status_from_flight(event: FlightEvent, flight: dict[str, Any]) -> FlightStatus:
    """Build a status object from Air France-KLM data."""
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

    scheduled_departure = _parse_datetime(departure_times.get("scheduled")) or event.start
    estimated_departure = (
        _parse_datetime(_estimated_value(departure_times.get("estimated")))
        or _parse_datetime(departure_times.get("estimatedPublic"))
        or _parse_datetime(departure_times.get("estimatedTakeOffTime"))
    )
    actual_departure = (
        _parse_datetime(departure_times.get("actual"))
        or _parse_datetime(departure_times.get("actualTakeOffTime"))
    )

    scheduled_arrival = _parse_datetime(arrival_times.get("scheduled")) or event.end
    estimated_arrival = (
        _parse_datetime(_estimated_value(arrival_times.get("estimated")))
        or _parse_datetime(arrival_times.get("estimatedArrival"))
        or _parse_datetime(arrival_times.get("estimatedPublic"))
        or _parse_datetime(arrival_times.get("estimatedTouchDownTime"))
    )
    actual_arrival = (
        _parse_datetime(arrival_times.get("actual"))
        or _parse_datetime(arrival_times.get("aircraftOnPosition"))
        or _parse_datetime(arrival_times.get("actualTouchDownTime"))
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
        arrival_delay_minutes=_delay_minutes(
            scheduled_arrival, actual_arrival or estimated_arrival
        ),
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


def _flight_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of operational flights from a response."""
    flights = data.get("operationalFlights")
    if isinstance(flights, list):
        return [flight for flight in flights if isinstance(flight, dict)]

    embedded = data.get("_embedded")
    if isinstance(embedded, dict):
        for value in embedded.values():
            if isinstance(value, list):
                return [flight for flight in value if isinstance(flight, dict)]

    return []


def _first_leg(flight: dict[str, Any]) -> dict[str, Any]:
    """Return the first flight leg."""
    legs = flight.get("flightLegs")
    if isinstance(legs, list):
        for leg in legs:
            if isinstance(leg, dict):
                return leg
    return {}


def _scheduled_departure(flight: dict[str, Any]) -> datetime | None:
    """Return the scheduled departure datetime for sorting."""
    leg = _first_leg(flight)
    departure = _get_dict(leg, "departureInformation")
    return _parse_datetime(_get_dict(departure, "times").get("scheduled"))


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


def _numeric_flight_number(flight_number: str) -> str:
    """Return four-digit numeric flight number for AF-KLM queries."""
    digits = "".join(char for char in flight_number if char.isdigit())
    return digits.zfill(4) if digits else flight_number


def _utc_iso(value: datetime) -> str:
    """Return a UTC ISO timestamp with Z suffix."""
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


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


def _time_distance(candidate: datetime | None, target: datetime) -> float:
    """Return absolute seconds between two datetimes."""
    if candidate is None:
        return float("inf")
    return abs((candidate - target.astimezone(candidate.tzinfo)).total_seconds())


def _delay_minutes(scheduled: datetime | None, actual: datetime | None) -> int | None:
    """Return delay in minutes."""
    if not scheduled or not actual:
        return None
    return round((actual - scheduled).total_seconds() / 60)


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
