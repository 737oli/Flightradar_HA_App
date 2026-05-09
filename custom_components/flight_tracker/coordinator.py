"""Data coordinator for iCal Flight Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging

from aiohttp import ClientError, ClientResponseError, ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AirFranceKlmClient, AirFranceKlmRequestBlocked, FlightStatus
from .api_usage import ApiUsageManager, ApiUsageSnapshot
from .calendar import FlightEvent, RosterEvent, parse_flights, parse_roster_events
from .const import (
    CONF_LOOKAHEAD_DAYS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

LIVE_TRACKING_BEFORE_DEPARTURE = timedelta(hours=1)
LIVE_TRACKING_AFTER_ARRIVAL = timedelta(hours=1)


@dataclass(frozen=True)
class FlightTrackerSnapshot:
    """Current integration data."""

    flights: list[FlightEvent]
    roster_events: list[RosterEvent]
    current_flight: FlightEvent | None
    next_flight: FlightEvent | None
    statuses: dict[str, FlightStatus]
    api_usage: ApiUsageSnapshot
    last_refresh: datetime

    def status_for(self, event: FlightEvent | None) -> FlightStatus | None:
        """Return live status for a flight event."""
        if event is None:
            return None
        return self.statuses.get(event.uid)


class FlightTrackerCoordinator(DataUpdateCoordinator[FlightTrackerSnapshot]):
    """Fetch and coordinate iCal and live KLM flight data."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, session: ClientSession
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._session = session
        self._api_usage = ApiUsageManager(hass, entry.entry_id)
        minutes = _entry_value(
            entry, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
            config_entry=entry,
        )

    async def _async_update_data(self) -> FlightTrackerSnapshot:
        """Fetch current calendar and live flight data."""
        try:
            ics_text = await self._async_fetch_calendar()
            now = dt_util.now()
            lookahead = timedelta(
                days=_entry_value(
                    self.entry, CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS
                )
            )
            default_tz = dt_util.get_time_zone(self.hass.config.time_zone) or timezone.utc
            flights, roster_events = await self.hass.async_add_executor_job(
                _parse_calendar_data,
                ics_text,
                now,
                lookahead,
                default_tz,
            )
        except ClientResponseError as err:
            raise UpdateFailed(f"Calendar request failed: {err}") from err
        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Calendar request failed: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Calendar parsing failed: {err}") from err

        current_flight = _current_flight(flights, now)
        next_flight = _next_flight(flights, now)
        statuses = await self._async_live_statuses(
            flights, now, current_flight, next_flight
        )
        api_usage = await self._api_usage.async_snapshot(now)

        return FlightTrackerSnapshot(
            flights=flights,
            roster_events=roster_events,
            current_flight=current_flight,
            next_flight=next_flight,
            statuses=statuses,
            api_usage=api_usage,
            last_refresh=now,
        )

    async def _async_fetch_calendar(self) -> str:
        """Download the configured iCal feed."""
        url = _entry_value(self.entry, CONF_URL, self.entry.data[CONF_URL])
        async with self._session.get(url, timeout=20) as response:
            response.raise_for_status()
            return await response.text()

    async def _async_live_statuses(
        self,
        flights: list[FlightEvent],
        now: datetime,
        current_flight: FlightEvent | None,
        next_flight: FlightEvent | None,
    ) -> dict[str, FlightStatus]:
        """Fetch required live statuses for relevant flights."""
        api_key = str(_entry_value(self.entry, CONF_API_KEY, "")).strip()
        if not api_key:
            raise UpdateFailed("Air France-KLM API key is required")

        candidates = _live_candidates(flights, now, current_flight, next_flight)
        if not candidates:
            return {}

        async def request_guard() -> None:
            await self._api_usage.async_acquire_request(dt_util.now())

        client = AirFranceKlmClient(
            self._session,
            api_key,
            request_guard=request_guard,
        )
        statuses: dict[str, FlightStatus] = {}
        for event in candidates:
            try:
                cached_flight_id = await self._api_usage.async_get_flight_id(event, now)
                status = await client.async_get_status(event, cached_flight_id)
            except AirFranceKlmRequestBlocked as err:
                _LOGGER.warning(
                    "Air France-KLM request budget blocked live update for %s: %s",
                    event.flight_number,
                    err,
                )
                break
            except ClientResponseError as err:
                _LOGGER.warning(
                    "Air France-KLM request failed for %s: %s",
                    event.flight_number,
                    err,
                )
                continue
            except (ClientError, TimeoutError) as err:
                _LOGGER.warning(
                    "Air France-KLM request failed for %s: %s",
                    event.flight_number,
                    err,
                )
                continue

            if status:
                statuses[event.uid] = status
                if status.provider_flight_id:
                    await self._api_usage.async_store_flight_id(
                        event, status.provider_flight_id, now
                    )

        return statuses


def _current_flight(flights: list[FlightEvent], now: datetime) -> FlightEvent | None:
    """Return the flight whose travel window is active."""
    for flight in flights:
        if _in_live_window(flight, now):
            return flight
    return None


def _next_flight(flights: list[FlightEvent], now: datetime) -> FlightEvent | None:
    """Return the next upcoming flight."""
    for flight in flights:
        if flight.end >= now:
            return flight
    return None


def _live_candidates(
    flights: list[FlightEvent],
    now: datetime,
    current_flight: FlightEvent | None,
    next_flight: FlightEvent | None,
) -> list[FlightEvent]:
    """Pick a small set of flights to enrich with live API data."""
    candidates: list[FlightEvent] = []
    for flight in flights:
        if _in_live_window(flight, now):
            candidates.append(flight)

    for flight in (current_flight, next_flight):
        if flight and flight not in candidates and _in_live_window(flight, now):
            candidates.append(flight)

    return candidates[:2]


def _in_live_window(flight: FlightEvent, now: datetime) -> bool:
    """Return whether a flight is inside the live status polling window."""
    return (
        flight.start - LIVE_TRACKING_BEFORE_DEPARTURE
        <= now
        <= flight.end + LIVE_TRACKING_AFTER_ARRIVAL
    )


def _entry_value(entry: ConfigEntry, key: str, default: object) -> object:
    """Read an option override with data fallback."""
    return entry.options.get(key, entry.data.get(key, default))


def _parse_calendar_data(
    ics_text: str,
    now: datetime,
    lookahead: timedelta,
    default_tz: timezone,
) -> tuple[list[FlightEvent], list[RosterEvent]]:
    """Parse flights and roster events in one executor job."""
    return (
        parse_flights(ics_text, now, lookahead, default_tz),
        parse_roster_events(ics_text, now, lookahead, default_tz),
    )
