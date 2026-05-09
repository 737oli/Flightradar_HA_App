"""Air France-KLM API usage budget and cache helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from typing import Any

try:
    from homeassistant.helpers.storage import Store
except ImportError:  # pragma: no cover - used by lightweight unit tests
    Store = None

from .clients.afkl import AirFranceKlmRequestBlocked
from .const import DOMAIN
from .parsers.ical import FlightEvent

STORAGE_VERSION = 1
DEFAULT_DAILY_REQUEST_LIMIT = 95
MIN_REQUEST_INTERVAL_SECONDS = 1.1
FLIGHT_ID_CACHE_TTL = timedelta(days=2)


@dataclass(frozen=True)
class ApiUsageSnapshot:
    """Current AF-KLM request budget state."""

    date: str
    requests_today: int
    daily_limit: int
    remaining: int
    exhausted: bool
    cached_flight_ids: int
    last_request_at: str | None = None


class ApiUsageManager:
    """Persist and enforce AF-KLM request limits."""

    def __init__(
        self,
        hass,
        entry_id: str,
        daily_limit: int = DEFAULT_DAILY_REQUEST_LIMIT,
        min_interval_seconds: float = MIN_REQUEST_INTERVAL_SECONDS,
        store=None,
        sleep=asyncio.sleep,
        monotonic=time.monotonic,
    ) -> None:
        """Initialize the usage manager."""
        if store is None:
            if Store is None:
                raise RuntimeError("Home Assistant storage Store is unavailable")
            store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_api_usage_{entry_id}")

        self._store = store
        self._daily_limit = daily_limit
        self._min_interval_seconds = min_interval_seconds
        self._sleep = sleep
        self._monotonic = monotonic
        self._lock: asyncio.Lock | None = None
        self._data: dict[str, Any] | None = None
        self._last_request_monotonic: float | None = None

    async def async_acquire_request(self, now: datetime) -> None:
        """Reserve one API request and throttle to the configured pace."""
        async with self._async_lock():
            data = await self._async_data(now)
            if data["requests_today"] >= self._daily_limit:
                raise AirFranceKlmRequestBlocked(
                    f"AF-KLM daily API budget exhausted "
                    f"({data['requests_today']}/{self._daily_limit})"
                )

            current_monotonic = self._monotonic()
            if self._last_request_monotonic is not None:
                elapsed = current_monotonic - self._last_request_monotonic
                wait_time = self._min_interval_seconds - elapsed
                if wait_time > 0:
                    await self._sleep(wait_time)
                    current_monotonic = self._monotonic()

            data["requests_today"] += 1
            data["last_request_at"] = now.isoformat()
            await self._async_save()
            self._last_request_monotonic = current_monotonic

    async def async_get_flight_id(
        self, event: FlightEvent, now: datetime
    ) -> str | None:
        """Return a cached AF-KLM flight id for an event."""
        data = await self._async_data(now)
        self._prune_flight_ids(data, now)
        item = data["flight_ids"].get(_flight_cache_key(event))
        if not isinstance(item, dict):
            return None
        flight_id = item.get("flight_id")
        return str(flight_id) if flight_id else None

    async def async_store_flight_id(
        self, event: FlightEvent, flight_id: str, now: datetime
    ) -> None:
        """Cache an AF-KLM flight id for an event."""
        data = await self._async_data(now)
        self._prune_flight_ids(data, now)
        data["flight_ids"][_flight_cache_key(event)] = {
            "flight_id": flight_id,
            "expires_at": (event.end + FLIGHT_ID_CACHE_TTL).isoformat(),
        }
        await self._async_save()

    async def async_snapshot(self, now: datetime) -> ApiUsageSnapshot:
        """Return current request budget state."""
        data = await self._async_data(now)
        self._prune_flight_ids(data, now)
        remaining = max(0, self._daily_limit - int(data["requests_today"]))
        return ApiUsageSnapshot(
            date=data["date"],
            requests_today=int(data["requests_today"]),
            daily_limit=self._daily_limit,
            remaining=remaining,
            exhausted=remaining <= 0,
            cached_flight_ids=len(data["flight_ids"]),
            last_request_at=data.get("last_request_at"),
        )

    async def _async_data(self, now: datetime) -> dict[str, Any]:
        """Load and normalize storage data."""
        today = _date_key(now)
        if self._data is None:
            loaded = await self._store.async_load()
            self._data = loaded if isinstance(loaded, dict) else {}

        if self._data.get("date") != today:
            self._data["date"] = today
            self._data["requests_today"] = 0
            self._data["last_request_at"] = None

        self._data.setdefault("requests_today", 0)
        self._data.setdefault("flight_ids", {})
        if not isinstance(self._data["flight_ids"], dict):
            self._data["flight_ids"] = {}
        return self._data

    def _async_lock(self) -> asyncio.Lock:
        """Return a lock created inside the running event loop."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def _async_save(self) -> None:
        """Persist usage data."""
        await self._store.async_save(self._data or {})

    def _prune_flight_ids(self, data: dict[str, Any], now: datetime) -> None:
        """Remove expired flight id cache entries."""
        flight_ids = data.get("flight_ids")
        if not isinstance(flight_ids, dict):
            data["flight_ids"] = {}
            return

        expired = [
            key
            for key, item in flight_ids.items()
            if not isinstance(item, dict)
            or _parse_datetime(item.get("expires_at")) <= now
        ]
        for key in expired:
            flight_ids.pop(key, None)


def _flight_cache_key(event: FlightEvent) -> str:
    """Return a stable cache key for a flight event."""
    parts = [
        event.uid,
        event.flight_number or "",
        event.departure_airport or "",
        event.arrival_airport or "",
        event.start.isoformat(),
    ]
    return "|".join(parts)


def _date_key(now: datetime) -> str:
    """Return the local date key for request accounting."""
    return now.date().isoformat()


def _parse_datetime(value: Any) -> datetime:
    """Parse a stored datetime, returning an expired fallback on failure."""
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
