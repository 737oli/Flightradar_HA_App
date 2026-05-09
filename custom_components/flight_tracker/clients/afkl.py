"""Air France-KLM Flight Status API client."""

from __future__ import annotations

from datetime import timezone
from typing import Any, Awaitable, Callable, TYPE_CHECKING
from urllib.parse import quote

from ..parsers.afkl_status import FlightStatus, status_from_flight
from ..parsers.ical import FlightEvent

if TYPE_CHECKING:
    from aiohttp import ClientSession

AFKL_BASE_URL = "https://api.airfranceklm.com/opendata/flightstatus"
KLM_CARRIER_CODE = "KL"
RequestGuard = Callable[[], Awaitable[None]]


class AirFranceKlmRequestBlocked(Exception):
    """Raised when an AF-KLM request is blocked before it is sent."""


class AirFranceKlmClient:
    """Small Air France-KLM Open Data Flight Status API client."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        request_guard: RequestGuard | None = None,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key
        self._request_guard = request_guard

    async def async_get_status(
        self, event: FlightEvent, cached_flight_id: str | None = None
    ) -> FlightStatus | None:
        """Fetch live status for a calendar flight."""
        # This integration intentionally enriches KLM-operated roster flights only.
        # Returning None here lets the coordinator keep non-flight or non-KL calendar
        # events without spending API budget on requests that cannot be useful.
        if not event.flight_number or not event.airline_code:
            return None
        if event.airline_code.upper() != KLM_CARRIER_CODE:
            return None

        # AF-KLM's detail endpoint needs an exact documented flight id. Prefer the
        # cached provider id when we have one, then fall back to the id generated
        # from the roster date and KL flight number.
        flight_ids = _candidate_flight_ids(event, cached_flight_id)
        if not flight_ids:
            return None

        # The cached id can become stale around schedule changes. Try each candidate
        # in order, but only raise the last failure so a stale cache entry does not
        # hide a valid generated lookup.
        for index, flight_id in enumerate(flight_ids):
            try:
                data = await self._async_detail_by_id(flight_id)
            except AirFranceKlmRequestBlocked:
                # Budget exhaustion is deliberate throttling, not a lookup failure.
                # Bubble it up so the coordinator can stop the polling loop.
                raise
            except Exception:  # noqa: BLE001
                if index == len(flight_ids) - 1:
                    raise
                continue
            if data:
                # Keep the transport client thin: all API shape quirks are mapped in
                # one place before Home Assistant entities see the status object.
                return status_from_flight(event, data)
        return None

    async def _async_detail_by_id(self, flight_id: str) -> dict[str, Any] | None:
        """Fetch detailed flight status directly from a flight id."""
        data = await self._request(
            _flight_detail_path(flight_id),
            {},
        )
        return data if isinstance(data, dict) else None

    async def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Request JSON from Air France-KLM."""
        if self._request_guard:
            await self._request_guard()

        headers = {
            "API-Key": self._api_key,
            "accept": "application/hal+json, application/json",
            "accept-language": "en-GB",
            "afkl-travel-host": KLM_CARRIER_CODE,
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


def _flight_detail_path(flight_id: str) -> str:
    """Return the encoded AF-KLM detail path for a flight id."""
    return f"/{quote(str(flight_id), safe='')}"


def _candidate_flight_ids(
    event: FlightEvent,
    cached_flight_id: str | None = None,
) -> list[str]:
    """Return exact AF-KLM flight status ids to try."""
    generated_flight_id = _flight_status_id(event)
    possible_flight_status_ids = [
        flight_id
        for flight_id in (cached_flight_id, generated_flight_id)
        if flight_id
    ]
    return list(dict.fromkeys(possible_flight_status_ids))


def _flight_status_id(event: FlightEvent) -> str | None:
    """Return the documented AF-KLM flight status id for a calendar flight."""
    if not event.flight_number:
        return None
    schedule_date = event.start.astimezone(timezone.utc).strftime("%Y%m%d")
    return (
        f"{schedule_date}+{KLM_CARRIER_CODE}+"
        f"{_numeric_flight_number(event.flight_number)}"
        f"{_operational_suffix(event.flight_number)}"
    )


def _numeric_flight_number(flight_number: str) -> str:
    """Return four-digit numeric flight number for AF-KLM queries."""
    digits = "".join(char for char in flight_number if char.isdigit())
    return digits.zfill(4) if digits else flight_number


def _operational_suffix(flight_number: str) -> str:
    """Return an optional operational suffix from a flight number."""
    suffix = "".join(char for char in flight_number.upper() if char.isalpha())
    if suffix.startswith(KLM_CARRIER_CODE):
        suffix = suffix[len(KLM_CARRIER_CODE) :]
    return suffix[:1]
