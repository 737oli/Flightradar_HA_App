"""Optional live flight data providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .calendar import FlightEvent

FLIGHTAWARE_BASE_URL = "https://aeroapi.flightaware.com/aeroapi"


@dataclass(frozen=True)
class FlightStatus:
    """Live status and position for a flight."""

    ident: str
    source: str
    status: str | None = None
    fa_flight_id: str | None = None
    actual_departure: datetime | None = None
    estimated_departure: datetime | None = None
    actual_arrival: datetime | None = None
    estimated_arrival: datetime | None = None
    departure_delay_minutes: int | None = None
    arrival_delay_minutes: int | None = None
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
        return "en route" in lowered or "airborne" in lowered or "in air" in lowered


class FlightAwareClient:
    """Small FlightAware AeroAPI client."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key

    async def async_get_status(self, event: FlightEvent) -> FlightStatus | None:
        """Fetch live status for a calendar flight."""
        if not event.flight_number:
            return None

        start = (event.start.astimezone(timezone.utc) - timedelta(hours=12)).isoformat()
        end = (event.start.astimezone(timezone.utc) + timedelta(hours=18)).isoformat()

        data = await self._request(
            f"/flights/{event.flight_number}",
            {"start": start, "end": end, "max_pages": 1},
        )
        flights = data.get("flights") or []
        if not flights:
            return None

        best = min(
            flights,
            key=lambda flight: _time_distance(
                _parse_datetime(
                    flight.get("scheduled_out")
                    or flight.get("scheduled_off")
                    or flight.get("estimated_out")
                ),
                event.start,
            ),
        )

        fa_flight_id = best.get("fa_flight_id") or best.get("id")
        position = None
        if fa_flight_id and _looks_active(best):
            try:
                position = await self._request(f"/flights/{fa_flight_id}/position", {})
            except (ClientError, ClientResponseError, TimeoutError):
                position = None

        return _status_from_flight(event.flight_number, best, position)

    async def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Request JSON from FlightAware."""
        headers = {"x-apikey": self._api_key}
        async with self._session.get(
            f"{FLIGHTAWARE_BASE_URL}{path}",
            headers=headers,
            params=params,
            timeout=20,
        ) as response:
            response.raise_for_status()
            return await response.json()


def _status_from_flight(
    ident: str, flight: dict[str, Any], position: dict[str, Any] | None
) -> FlightStatus:
    """Build a status object from FlightAware data."""
    last_position = None
    if position:
        last_position = position.get("last_position") or position.get("position") or position

    scheduled_out = _parse_datetime(flight.get("scheduled_out"))
    estimated_out = _parse_datetime(flight.get("estimated_out"))
    actual_out = _parse_datetime(flight.get("actual_out") or flight.get("actual_off"))
    scheduled_in = _parse_datetime(flight.get("scheduled_in"))
    estimated_in = _parse_datetime(flight.get("estimated_in"))
    actual_in = _parse_datetime(flight.get("actual_in") or flight.get("actual_on"))

    return FlightStatus(
        ident=ident,
        source="flightaware",
        status=flight.get("status"),
        fa_flight_id=flight.get("fa_flight_id") or flight.get("id"),
        actual_departure=actual_out,
        estimated_departure=estimated_out,
        actual_arrival=actual_in,
        estimated_arrival=estimated_in,
        departure_delay_minutes=_delay_minutes(scheduled_out, actual_out or estimated_out),
        arrival_delay_minutes=_delay_minutes(scheduled_in, actual_in or estimated_in),
        latitude=_number(last_position, "latitude"),
        longitude=_number(last_position, "longitude"),
        altitude_ft=_integer(last_position, "altitude"),
        groundspeed_kt=_integer(last_position, "groundspeed"),
        progress_percent=_integer(position, "progress_percent"),
        position_time=_parse_datetime(
            _get(last_position, "timestamp") or _get(last_position, "time")
        ),
    )


def _looks_active(flight: dict[str, Any]) -> bool:
    """Return whether a flight may have a current position."""
    status = str(flight.get("status") or "").lower()
    return bool(flight.get("actual_out") or "en route" in status or "airborne" in status)


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


def _get(data: dict[str, Any] | None, key: str) -> Any:
    """Safely read a dict key."""
    if not data:
        return None
    return data.get(key)


def _number(data: dict[str, Any] | None, key: str) -> float | None:
    """Read a float from a dict."""
    value = _get(data, key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(data: dict[str, Any] | None, key: str) -> int | None:
    """Read an int from a dict."""
    value = _get(data, key)
    if value is None:
        return None
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None
