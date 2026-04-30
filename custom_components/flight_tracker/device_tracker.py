"""Device tracker entity for live flight position."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FlightTrackerCoordinator
from .entity import async_coordinator, flight_attributes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the flight location tracker."""
    coordinator = async_coordinator(hass, entry)
    async_add_entities([FlightLocationTracker(coordinator, entry)])


class FlightLocationTracker(CoordinatorEntity[FlightTrackerCoordinator], TrackerEntity):
    """GPS tracker for the active flight."""

    _attr_has_entity_name = True
    _attr_translation_key = "flight_location"

    def __init__(self, coordinator: FlightTrackerCoordinator, entry: ConfigEntry) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_flight_location"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Custom",
            model="iCal Flight Tracker",
        )

    @property
    def latitude(self) -> float | None:
        """Return latitude from live flight data."""
        status = self.coordinator.data.status_for(self.coordinator.data.current_flight)
        return status.latitude if status else None

    @property
    def longitude(self) -> float | None:
        """Return longitude from live flight data."""
        status = self.coordinator.data.status_for(self.coordinator.data.current_flight)
        return status.longitude if status else None

    @property
    def location_accuracy(self) -> float:
        """Return GPS location accuracy in meters."""
        return 10000

    @property
    def source_type(self) -> SourceType:
        """Return the tracker source type."""
        return SourceType.GPS

    @property
    def location_name(self) -> str | None:
        """Return a location label when coordinates are unavailable."""
        if self.latitude is not None and self.longitude is not None:
            return None
        event = self.coordinator.data.current_flight or self.coordinator.data.next_flight
        if event and event.route:
            return event.route
        if event and event.flight_number:
            return event.flight_number
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for the active flight."""
        event = self.coordinator.data.current_flight
        status = self.coordinator.data.status_for(event)
        return flight_attributes(event, status, self.coordinator.data.last_refresh)

