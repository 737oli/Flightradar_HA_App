"""Sensor entities for iCal Flight Tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_FLIGHTS, DOMAIN
from .coordinator import FlightTrackerCoordinator
from .entity import async_coordinator, compact_flight, flight_attributes

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="current_flight",
        translation_key="current_flight",
        icon="mdi:airplane",
    ),
    SensorEntityDescription(
        key="next_flight",
        translation_key="next_flight",
        icon="mdi:airplane-takeoff",
    ),
    SensorEntityDescription(
        key="tracked_flights",
        translation_key="tracked_flights",
        icon="mdi:calendar-clock",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up iCal Flight Tracker sensors."""
    coordinator = async_coordinator(hass, entry)
    async_add_entities(
        FlightTrackerSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class FlightTrackerSensor(CoordinatorEntity[FlightTrackerCoordinator], SensorEntity):
    """Sensor for iCal Flight Tracker data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FlightTrackerCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Custom",
            model="iCal Flight Tracker",
        )

    @property
    def native_value(self) -> str | int | None:
        """Return the state value."""
        data = self.coordinator.data
        if self.entity_description.key == "tracked_flights":
            return len(data.flights)

        event = (
            data.current_flight
            if self.entity_description.key == "current_flight"
            else data.next_flight
        )
        if event is None:
            return "not_flying" if self.entity_description.key == "current_flight" else None

        status = data.status_for(event)
        if self.entity_description.key == "current_flight" and status:
            if status.is_airborne:
                return "airborne"
            if status.status:
                return status.status

        return event.flight_number or event.summary

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes."""
        data = self.coordinator.data
        if self.entity_description.key == "tracked_flights":
            return {
                ATTR_FLIGHTS: [compact_flight(flight) for flight in data.flights],
                "last_refresh": data.last_refresh.isoformat(),
            }

        event = (
            data.current_flight
            if self.entity_description.key == "current_flight"
            else data.next_flight
        )
        return flight_attributes(event, data.status_for(event), data.last_refresh)

