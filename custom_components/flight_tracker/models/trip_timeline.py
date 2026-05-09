"""Trip timeline models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TripTimelineSummary:
    """Home-friendly travel day timeline."""

    native_value: str
    headline: str
    detail: str
    phase: str
    day_start: datetime | None
    day_end: datetime | None
    duty_start: datetime | None
    duty_end: datetime | None
    origin: str | None
    destination: str | None
    segments: list[dict[str, Any]]
    current_segment: dict[str, Any] | None
    previous_flight: dict[str, Any] | None
    current_flight: dict[str, Any] | None
    next_flight: dict[str, Any] | None
