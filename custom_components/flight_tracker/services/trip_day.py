"""Trip day selection helpers for timeline services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from ..models.roster import RosterEvent


@dataclass(frozen=True)
class TripDaySelection:
    """Selected travel day context for timeline building."""

    day_start: datetime
    day_end: datetime
    events: list[RosterEvent]


def select_trip_day(
    events: list[RosterEvent],
    now: datetime,
) -> TripDaySelection | None:
    """Select the roster day to show in the trip timeline."""
    anchor = _anchor_event(events, now)
    if anchor is None:
        return None

    tzinfo = now.tzinfo or timezone.utc
    day_anchor = now if anchor.start <= now <= anchor.end else anchor.start
    day_start, day_end = day_bounds(day_anchor, tzinfo)
    day_events = [
        event for event in events if event.end > day_start and event.start < day_end
    ]
    return TripDaySelection(day_start=day_start, day_end=day_end, events=day_events)


def day_bounds(value: datetime, tzinfo: timezone) -> tuple[datetime, datetime]:
    """Return local day bounds for a datetime."""
    local_date = value.astimezone(tzinfo).date()
    start = datetime.combine(local_date, time.min, tzinfo=tzinfo)
    return start, start + timedelta(days=1)


def _anchor_event(events: list[RosterEvent], now: datetime) -> RosterEvent | None:
    """Return the event that defines the displayed travel day."""
    meaningful = [event for event in events if event.kind != "off"] or events
    active = [event for event in meaningful if event.start <= now <= event.end]
    if active:
        return sorted(active, key=_anchor_priority)[0]

    upcoming = [event for event in meaningful if event.start > now]
    if upcoming:
        return min(upcoming, key=lambda event: event.start)

    previous = [event for event in meaningful if event.end < now]
    return max(previous, key=lambda event: event.end) if previous else None


def _anchor_priority(event: RosterEvent) -> tuple[int, float]:
    """Sort active events by usefulness as a timeline anchor."""
    priorities = {
        "flight": 0,
        "ground_time": 1,
        "transfer": 1,
        "hotel": 2,
        "duty": 3,
        "training": 4,
        "event": 5,
        "off": 6,
    }
    duration = (event.end - event.start).total_seconds()
    return priorities.get(event.kind, 5), duration
