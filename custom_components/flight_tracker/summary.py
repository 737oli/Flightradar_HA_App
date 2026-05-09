"""Compatibility exports for travel status services.

New integration code should import from ``flight_tracker.services.travel_status``
directly.
"""

from __future__ import annotations

from .services.travel_status import TravelStatusSummary, build_travel_status

__all__ = ["TravelStatusSummary", "build_travel_status"]
