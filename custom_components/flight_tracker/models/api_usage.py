"""API usage budget models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiUsageSnapshot:
    """Current AF-KLM request budget state."""

    date: str
    requests_today: int
    daily_limit: int
    remaining: int
    exhausted: bool
    cached_flight_ids: int
    last_request_at: str | None = None
