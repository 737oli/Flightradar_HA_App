from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
import sys

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "flight_tracker"


def _bootstrap_custom_component_package() -> None:
    custom_components = sys.modules.setdefault(
        "custom_components", ModuleType("custom_components")
    )
    flight_tracker = sys.modules.setdefault(
        "custom_components.flight_tracker", ModuleType("custom_components.flight_tracker")
    )
    custom_components.__path__ = [str(ROOT / "custom_components")]
    flight_tracker.__path__ = [str(PACKAGE_PATH)]


_bootstrap_custom_component_package()


@pytest.fixture
def homeassistant_stubs(monkeypatch):
    """Install lightweight Home Assistant imports for tests that request them."""
    _install_homeassistant_stubs(monkeypatch)


def _install_homeassistant_stubs(monkeypatch) -> None:
    aiohttp = ModuleType("aiohttp")
    aiohttp.__flight_tracker_test_stub__ = True
    aiohttp.ClientError = Exception
    aiohttp.ClientResponseError = Exception
    aiohttp.ClientSession = object
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp)

    homeassistant = ModuleType("homeassistant")
    homeassistant.__flight_tracker_test_stub__ = True
    homeassistant.__path__ = []
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)

    helpers = ModuleType("homeassistant.helpers")
    helpers.__flight_tracker_test_stub__ = True
    helpers.__path__ = []
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)

    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.__flight_tracker_test_stub__ = True
    config_entries.ConfigEntry = object
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries)

    const = ModuleType("homeassistant.const")
    const.__flight_tracker_test_stub__ = True
    const.CONF_API_KEY = "api_key"
    const.CONF_URL = "url"
    monkeypatch.setitem(sys.modules, "homeassistant.const", const)

    core = ModuleType("homeassistant.core")
    core.__flight_tracker_test_stub__ = True
    core.HomeAssistant = object
    monkeypatch.setitem(sys.modules, "homeassistant.core", core)

    update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.__flight_tracker_test_stub__ = True

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = Exception
    monkeypatch.setitem(
        sys.modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator,
    )

    dt = ModuleType("homeassistant.util.dt")
    dt.__flight_tracker_test_stub__ = True
    util = ModuleType("homeassistant.util")
    util.__flight_tracker_test_stub__ = True
    util.dt = dt
    dt.now = lambda: datetime.now(timezone.utc)
    dt.get_time_zone = lambda time_zone: timezone.utc
    monkeypatch.setitem(sys.modules, "homeassistant.util", util)
    monkeypatch.setitem(sys.modules, "homeassistant.util.dt", dt)
