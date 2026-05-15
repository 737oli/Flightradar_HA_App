"""Deprecated compatibility exports for API usage storage.

These root-level imports are kept temporarily for older local consumers and are
planned for removal in v0.7.0. New integration code should import from
``flight_tracker.models.api_usage`` and ``flight_tracker.storage.api_usage``
directly.
"""

from __future__ import annotations

from .models.api_usage import ApiUsageSnapshot
from .storage.api_usage import (
    DEFAULT_DAILY_REQUEST_LIMIT,
    FLIGHT_ID_CACHE_TTL,
    MIN_REQUEST_INTERVAL_SECONDS,
    STORAGE_VERSION,
    ApiUsageManager,
)

__all__ = [
    "ApiUsageManager",
    "ApiUsageSnapshot",
    "DEFAULT_DAILY_REQUEST_LIMIT",
    "FLIGHT_ID_CACHE_TTL",
    "MIN_REQUEST_INTERVAL_SECONDS",
    "STORAGE_VERSION",
]
