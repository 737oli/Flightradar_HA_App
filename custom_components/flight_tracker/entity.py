"""Shared entity helpers for iCal Flight Tracker."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import FlightStatus
from .calendar import FlightEvent
from .const import ATTR_LAST_REFRESH, DOMAIN
from .coordinator import FlightTrackerCoordinator


def async_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> FlightTrackerCoordinator:
    """Return the coordinator for a config entry."""
    return hass.data[DOMAIN][entry.entry_id]


def flight_attributes(
    event: FlightEvent | None,
    status: FlightStatus | None,
    last_refresh: datetime,
) -> dict[str, Any]:
    """Return Home Assistant-safe attributes for a flight."""
    attrs: dict[str, Any] = {ATTR_LAST_REFRESH: last_refresh.isoformat()}
    if event:
        attrs.update(event.as_attributes())
        attrs["minutes_until_departure"] = round(
            (event.start - last_refresh).total_seconds() / 60
        )
    if status:
        attrs.update(
            {
                "live_source": status.source,
                "live_status": status.status,
                "flightaware_id": status.fa_flight_id,
                "actual_departure": _isoformat(status.actual_departure),
                "estimated_departure": _isoformat(status.estimated_departure),
                "actual_arrival": _isoformat(status.actual_arrival),
                "estimated_arrival": _isoformat(status.estimated_arrival),
                "departure_delay_minutes": status.departure_delay_minutes,
                "arrival_delay_minutes": status.arrival_delay_minutes,
                "latitude": status.latitude,
                "longitude": status.longitude,
                "altitude_ft": status.altitude_ft,
                "groundspeed_kt": status.groundspeed_kt,
                "progress_percent": status.progress_percent,
                "position_time": _isoformat(status.position_time),
            }
        )
    return attrs


def compact_flight(event: FlightEvent) -> dict[str, Any]:
    """Return compact flight data for list attributes."""
    return {
        "flight_number": event.flight_number,
        "airline_code": event.airline_code,
        "route": event.route,
        "summary": event.summary,
        "scheduled_departure": event.start.isoformat(),
        "scheduled_arrival": event.end.isoformat(),
        "aircraft_type": event.aircraft_type,
        "is_deadhead": event.is_deadhead,
    }


def _isoformat(value: datetime | None) -> str | None:
    """Return an ISO string for datetimes."""
    return value.isoformat() if value else None
