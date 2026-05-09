"""Shared entity helpers for iCal Flight Tracker."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import ATTR_LAST_REFRESH, DOMAIN
from .coordinator import FlightTrackerCoordinator
from .models.flight import FlightEvent
from .models.status import FlightStatus


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
        if event.aircraft_type:
            attrs["calendar_aircraft_type"] = event.aircraft_type
        attrs["minutes_until_departure"] = round(
            (event.start - last_refresh).total_seconds() / 60
        )
    if status:
        live_attrs = {
            "live_source": status.source,
            "live_status": status.status,
            "live_flight_id": status.provider_flight_id,
            "afkl_flight_id": status.provider_flight_id,
            "actual_departure": _isoformat(status.actual_departure),
            "estimated_departure": _isoformat(status.estimated_departure),
            "actual_arrival": _isoformat(status.actual_arrival),
            "estimated_arrival": _isoformat(status.estimated_arrival),
            "departure_delay_minutes": status.departure_delay_minutes,
            "arrival_delay_minutes": status.arrival_delay_minutes,
            "departure_terminal": status.departure_terminal,
            "departure_gate": status.departure_gate,
            "arrival_terminal": status.arrival_terminal,
            "arrival_gate": status.arrival_gate,
            "aircraft_registration": status.aircraft_registration,
            "live_aircraft_type": status.aircraft_type,
            "irregularity_delay_code": status.delay_code,
            "irregularity_delay_sub_code": status.delay_sub_code,
            "irregularity_delay_duration": status.delay_duration,
            "irregularity_delay_duration_arrival": status.delay_duration_arrival,
            "irregularity_delay_duration_public": status.delay_duration_public,
            "irregularity_delay_reason": status.delay_reason,
            "irregularity_delay_reason_public": status.delay_reason_public,
            "irregularity_delay_reason_code_public": status.delay_reason_code_public,
            "irregularity_public_disruption_reason": status.public_disruption_reason,
            "latitude": status.latitude,
            "longitude": status.longitude,
            "altitude_ft": status.altitude_ft,
            "groundspeed_kt": status.groundspeed_kt,
            "progress_percent": status.progress_percent,
            "position_time": _isoformat(status.position_time),
        }
        if status.aircraft_type:
            live_attrs["aircraft_type"] = status.aircraft_type
            live_attrs["aircraft_type_code"] = status.aircraft_type
        attrs.update(live_attrs)
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
