"""Friendly travel status models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TravelStatusSummary:
    """User-friendly flight status for dashboards and notifications."""

    native_value: str
    phase: str
    headline: str
    detail: str
    notification_title: str
    notification_message: str
    notification_key: str
    severity: str
    event_uid: str | None = None
    flight_number: str | None = None
    route: str | None = None
    destination: str | None = None
    minutes_until_departure: int | None = None
    minutes_until_arrival: int | None = None
    max_delay_minutes: int | None = None
    is_active: bool = False
    is_airborne: bool = False
    is_arriving_soon: bool = False
    is_delayed: bool = False
