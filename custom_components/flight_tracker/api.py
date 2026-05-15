"""Deprecated compatibility exports for Air France-KLM API code.

These root-level imports are kept temporarily for older local consumers and are
planned for removal in v0.7.0. New integration code should import from
``flight_tracker.clients.afkl``, ``flight_tracker.models.status``, and
``flight_tracker.parsers.afkl_status`` directly.
"""

from __future__ import annotations

from .clients.afkl import (
    AFKL_BASE_URL,
    KLM_CARRIER_CODE,
    AirFranceKlmClient,
    AirFranceKlmRequestBlocked,
    RequestGuard,
    _candidate_flight_ids,
    _flight_detail_path,
    _flight_status_id,
    _numeric_flight_number,
    _operational_suffix,
)
from .models.status import FlightStatus
from .parsers.afkl_status import status_from_flight

__all__ = [
    "AFKL_BASE_URL",
    "KLM_CARRIER_CODE",
    "AirFranceKlmClient",
    "AirFranceKlmRequestBlocked",
    "FlightStatus",
    "RequestGuard",
    "status_from_flight",
]
