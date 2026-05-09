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
def homeassistant_stubs():
    aiohttp = sys.modules.setdefault("aiohttp", ModuleType("aiohttp"))
    aiohttp.ClientError = Exception
    aiohttp.ClientResponseError = Exception
    aiohttp.ClientSession = object

    homeassistant = sys.modules.setdefault("homeassistant", ModuleType("homeassistant"))
    homeassistant.__path__ = []

    helpers = sys.modules.setdefault(
        "homeassistant.helpers", ModuleType("homeassistant.helpers")
    )
    helpers.__path__ = []

    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries", ModuleType("homeassistant.config_entries")
    )
    config_entries.ConfigEntry = object

    const = sys.modules.setdefault("homeassistant.const", ModuleType("homeassistant.const"))
    const.CONF_API_KEY = "api_key"
    const.CONF_URL = "url"

    core = sys.modules.setdefault("homeassistant.core", ModuleType("homeassistant.core"))
    core.HomeAssistant = object

    update_coordinator = sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator",
        ModuleType("homeassistant.helpers.update_coordinator"),
    )

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = Exception

    dt = sys.modules.setdefault("homeassistant.util.dt", ModuleType("homeassistant.util.dt"))
    util = sys.modules.setdefault("homeassistant.util", ModuleType("homeassistant.util"))
    util.dt = dt
    dt.now = lambda: None
    dt.get_time_zone = lambda time_zone: None
