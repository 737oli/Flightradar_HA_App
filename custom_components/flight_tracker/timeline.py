"""Deprecated compatibility exports for trip timeline services.

These root-level imports are kept temporarily for older local consumers and are
planned for removal in v0.7.0. New integration code should import from
``flight_tracker.models.trip_timeline`` and
``flight_tracker.services.trip_timeline`` directly.
"""

from __future__ import annotations

from .models.trip_timeline import TripTimelineSummary
from .services.trip_timeline import build_trip_timeline

__all__ = ["TripTimelineSummary", "build_trip_timeline"]
