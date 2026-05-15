"""Deprecated compatibility exports for travel status services.

These root-level imports are kept temporarily for older local consumers and are
planned for removal in v0.7.0. New integration code should import from
``flight_tracker.models.travel_status`` and
``flight_tracker.services.travel_status`` directly.
"""

from __future__ import annotations

from .models.travel_status import TravelStatusSummary
from .services.travel_status import build_travel_status

__all__ = ["TravelStatusSummary", "build_travel_status"]
