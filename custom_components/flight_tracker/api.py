"""Compatibility exports for Air France-KLM API code.

New integration code should import from ``flight_tracker.clients.afkl`` and
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
from .parsers.afkl_status import FlightStatus, status_from_flight

__all__ = [
    "AFKL_BASE_URL",
    "KLM_CARRIER_CODE",
    "AirFranceKlmClient",
    "AirFranceKlmRequestBlocked",
    "FlightStatus",
    "RequestGuard",
    "status_from_flight",
]
