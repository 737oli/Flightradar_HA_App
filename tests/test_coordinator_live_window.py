from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
import sys

ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "flight_tracker"

custom_components = sys.modules.setdefault(
    "custom_components", ModuleType("custom_components")
)
flight_tracker = sys.modules.setdefault(
    "custom_components.flight_tracker", ModuleType("custom_components.flight_tracker")
)
custom_components.__path__ = [str(ROOT / "custom_components")]
flight_tracker.__path__ = [str(PACKAGE_PATH)]


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install_homeassistant_stubs():
    aiohttp = ModuleType("aiohttp")
    aiohttp.ClientError = Exception
    aiohttp.ClientResponseError = Exception
    aiohttp.ClientSession = object
    sys.modules["aiohttp"] = aiohttp

    homeassistant = ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules["homeassistant"] = homeassistant

    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    sys.modules["homeassistant.config_entries"] = config_entries

    const = ModuleType("homeassistant.const")
    const.CONF_API_KEY = "api_key"
    const.CONF_URL = "url"
    sys.modules["homeassistant.const"] = const

    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant.core"] = core

    update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = Exception
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator

    dt = ModuleType("homeassistant.util.dt")
    dt.now = lambda: datetime.now(timezone.utc)
    dt.get_time_zone = lambda time_zone: timezone.utc
    util = ModuleType("homeassistant.util")
    util.dt = dt
    sys.modules["homeassistant.util"] = util
    sys.modules["homeassistant.util.dt"] = dt


calendar_module = load_module(
    "custom_components.flight_tracker.calendar", PACKAGE_PATH / "calendar.py"
)
load_module("custom_components.flight_tracker.const", PACKAGE_PATH / "const.py")
load_module("custom_components.flight_tracker.api", PACKAGE_PATH / "api.py")
install_homeassistant_stubs()
coordinator_module = load_module(
    "custom_components.flight_tracker.coordinator", PACKAGE_PATH / "coordinator.py"
)

FlightEvent = calendar_module.FlightEvent
_current_flight = coordinator_module._current_flight
_live_candidates = coordinator_module._live_candidates


def test_live_data_window_is_one_hour_before_until_one_hour_after_flight():
    flight = FlightEvent(
        uid="flight-1",
        summary="KL1327 AMS-KRK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type="E190",
        is_deadhead=False,
    )

    assert _current_flight([flight], flight.start - timedelta(minutes=61)) is None
    assert _current_flight([flight], flight.start - timedelta(minutes=60)) == flight
    assert _current_flight([flight], flight.end + timedelta(minutes=60)) == flight
    assert _current_flight([flight], flight.end + timedelta(minutes=61)) is None

    assert not _live_candidates(
        [flight], flight.start - timedelta(minutes=61), None, flight
    )
    assert _live_candidates(
        [flight], flight.start - timedelta(minutes=60), flight, flight
    ) == [flight]
