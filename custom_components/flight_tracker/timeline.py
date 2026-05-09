"""Compatibility exports for trip timeline services.

New integration code should import from ``flight_tracker.services.trip_timeline``
directly.
"""

from __future__ import annotations

from .services.trip_timeline import TripTimelineSummary, build_trip_timeline

__all__ = ["TripTimelineSummary", "build_trip_timeline"]
