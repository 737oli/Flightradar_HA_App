"""Binary sensors for iCal Flight Tracker notification triggers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FlightTrackerCoordinator
from .entity import async_coordinator
from .services.travel_status import TravelStatusSummary, build_travel_status

BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="flight_active",
        translation_key="flight_active",
        icon="mdi:airplane-marker",
    ),
    BinarySensorEntityDescription(
        key="flight_airborne",
        translation_key="flight_airborne",
        icon="mdi:airplane",
    ),
    BinarySensorEntityDescription(
        key="flight_arriving_soon",
        translation_key="flight_arriving_soon",
        icon="mdi:airplane-landing",
    ),
    BinarySensorEntityDescription(
        key="flight_delayed",
        translation_key="flight_delayed",
        icon="mdi:clock-alert",
    ),
    BinarySensorEntityDescription(
        key="flight_landed",
        translation_key="flight_landed",
        icon="mdi:airplane-check",
    ),
    BinarySensorEntityDescription(
        key="api_budget_exhausted",
        translation_key="api_budget_exhausted",
        icon="mdi:api-off",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up iCal Flight Tracker binary sensors."""
    coordinator = async_coordinator(hass, entry)
    async_add_entities(
        FlightTrackerBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class FlightTrackerBinarySensor(
    CoordinatorEntity[FlightTrackerCoordinator], BinarySensorEntity
):
    """Binary sensor for flight notification-friendly states."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FlightTrackerCoordinator,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool:
        """Return the binary sensor state."""
        if self.entity_description.key == "api_budget_exhausted":
            return self.coordinator.data.api_usage.exhausted

        summary = _travel_status(self.coordinator.data)
        if self.entity_description.key == "flight_active":
            return summary.is_active
        if self.entity_description.key == "flight_airborne":
            return summary.is_airborne
        if self.entity_description.key == "flight_arriving_soon":
            return summary.is_arriving_soon
        if self.entity_description.key == "flight_delayed":
            return summary.is_delayed
        if self.entity_description.key == "flight_landed":
            return summary.phase == "landed"
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return notification context attributes."""
        if self.entity_description.key == "api_budget_exhausted":
            usage = self.coordinator.data.api_usage
            return {
                "date": usage.date,
                "requests_today": usage.requests_today,
                "daily_limit": usage.daily_limit,
                "requests_remaining": usage.remaining,
                "cached_flight_ids": usage.cached_flight_ids,
                "last_request_at": usage.last_request_at,
            }

        summary = _travel_status(self.coordinator.data)
        return {
            "phase": summary.phase,
            "headline": summary.headline,
            "detail": summary.detail,
            "notification_title": summary.notification_title,
            "notification_message": summary.notification_message,
            "notification_key": summary.notification_key,
            "flight_number": summary.flight_number,
            "route": summary.route,
            "destination": summary.destination,
            "max_delay_minutes": summary.max_delay_minutes,
        }


def _travel_status(data) -> TravelStatusSummary:
    """Return the current friendly travel status."""
    return build_travel_status(
        data.current_flight,
        data.next_flight,
        data.status_for(data.current_flight),
        data.status_for(data.next_flight),
        data.last_refresh,
    )
