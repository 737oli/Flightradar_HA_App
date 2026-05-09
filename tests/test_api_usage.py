from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
import asyncio
import sys

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "flight_tracker"

custom_components = sys.modules.setdefault(
    "custom_components", ModuleType("custom_components")
)
flight_tracker = sys.modules.setdefault(
    "custom_components.flight_tracker", ModuleType("custom_components.flight_tracker")
)
clients = sys.modules.setdefault(
    "custom_components.flight_tracker.clients",
    ModuleType("custom_components.flight_tracker.clients"),
)
custom_components.__path__ = [str(ROOT / "custom_components")]
flight_tracker.__path__ = [str(PACKAGE_PATH)]
clients.__path__ = [str(PACKAGE_PATH / "clients")]


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


calendar_module = load_module(
    "custom_components.flight_tracker.calendar", PACKAGE_PATH / "calendar.py"
)
load_module("custom_components.flight_tracker.const", PACKAGE_PATH / "const.py")
afkl_client_module = load_module(
    "custom_components.flight_tracker.clients.afkl",
    PACKAGE_PATH / "clients" / "afkl.py",
)
api_usage_module = load_module(
    "custom_components.flight_tracker.api_usage", PACKAGE_PATH / "api_usage.py"
)

FlightEvent = calendar_module.FlightEvent
AirFranceKlmRequestBlocked = afkl_client_module.AirFranceKlmRequestBlocked
ApiUsageManager = api_usage_module.ApiUsageManager


def test_api_usage_enforces_daily_limit_and_resets_next_day():
    store = FakeStore()
    manager = ApiUsageManager(
        None,
        "entry-1",
        daily_limit=2,
        min_interval_seconds=0,
        store=store,
    )
    day_one = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)

    asyncio.run(manager.async_acquire_request(day_one))
    asyncio.run(manager.async_acquire_request(day_one))

    with pytest.raises(AirFranceKlmRequestBlocked):
        asyncio.run(manager.async_acquire_request(day_one))

    snapshot = asyncio.run(manager.async_snapshot(day_one))
    assert snapshot.requests_today == 2
    assert snapshot.remaining == 0
    assert snapshot.exhausted is True

    day_two = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    asyncio.run(manager.async_acquire_request(day_two))
    snapshot = asyncio.run(manager.async_snapshot(day_two))
    assert snapshot.requests_today == 1
    assert snapshot.remaining == 1
    assert snapshot.exhausted is False


def test_api_usage_throttles_to_one_request_per_second():
    store = FakeStore()
    sleeps = []
    monotonic_values = iter([10.0, 10.2, 11.3])

    async def fake_sleep(duration):
        sleeps.append(duration)

    manager = ApiUsageManager(
        None,
        "entry-1",
        daily_limit=10,
        min_interval_seconds=1.1,
        store=store,
        sleep=fake_sleep,
        monotonic=lambda: next(monotonic_values),
    )
    now = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)

    asyncio.run(manager.async_acquire_request(now))
    asyncio.run(manager.async_acquire_request(now))

    assert sleeps == [pytest.approx(0.9)]


def test_api_usage_caches_and_expires_flight_ids():
    store = FakeStore()
    manager = ApiUsageManager(None, "entry-1", store=store)
    event = FlightEvent(
        uid="flight-1",
        summary="KL1327 AMS-KRK",
        description="",
        location="",
        start=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 5, 5, 14, 0, tzinfo=timezone.utc),
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type="E190",
        is_deadhead=False,
    )
    now = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)

    asyncio.run(manager.async_store_flight_id(event, "20260505+KL+1327", now))
    assert (
        asyncio.run(manager.async_get_flight_id(event, now))
        == "20260505+KL+1327"
    )

    expired = datetime(2026, 5, 8, 14, 1, tzinfo=timezone.utc)
    assert asyncio.run(manager.async_get_flight_id(event, expired)) is None


class FakeStore:
    def __init__(self):
        self.data = None
        self.saves = []

    async def async_load(self):
        return self.data

    async def async_save(self, data):
        self.data = dict(data)
        self.saves.append(dict(data))
