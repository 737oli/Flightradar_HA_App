"""Home Assistant integration for tracking flights from an iCal calendar."""

from __future__ import annotations

from inspect import isawaitable
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
]
FRONTEND_URL_PATH = "/flight_tracker_static"
FRONTEND_REGISTERED = f"{DOMAIN}_frontend_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iCal Flight Tracker from a config entry."""
    await _async_register_frontend_path(hass)

    from .coordinator import FlightTrackerCoordinator

    session = async_get_clientsession(hass)
    coordinator = FlightTrackerCoordinator(hass, entry, session)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an iCal Flight Tracker config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_register_frontend_path(hass: HomeAssistant) -> None:
    """Register the Lovelace card static path across supported HA versions."""
    if hass.data.get(FRONTEND_REGISTERED):
        return

    frontend_path = str(Path(__file__).parent / "frontend")

    try:
        from homeassistant.components.http import StaticPathConfig as StaticPath
    except ImportError:
        StaticPath = None

    if StaticPath is not None and hasattr(hass.http, "async_register_static_paths"):
        await hass.http.async_register_static_paths(
            [StaticPath(FRONTEND_URL_PATH, frontend_path, False)]
        )
    elif hasattr(hass.http, "async_register_static_path"):
        result = hass.http.async_register_static_path(
            FRONTEND_URL_PATH, frontend_path, False
        )
        if isawaitable(result):
            await result
    else:
        hass.http.register_static_path(FRONTEND_URL_PATH, frontend_path, False)

    hass.data[FRONTEND_REGISTERED] = True
