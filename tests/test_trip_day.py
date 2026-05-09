from datetime import datetime, timedelta, timezone

from custom_components.flight_tracker.parsers.roster import parse_roster_events
from custom_components.flight_tracker.services.trip_day import day_bounds, select_trip_day


def test_select_trip_day_uses_current_day_for_overnight_hotel():
    events = parse_roster_events(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:hotel-1
DTSTART:20260124T221000Z
DTEND:20260125T120000Z
SUMMARY:Hotel STR
END:VEVENT
BEGIN:VEVENT
UID:flight-1
DTSTART:20260125T133000Z
DTEND:20260125T150000Z
SUMMARY:KL1832 STR-AMS
END:VEVENT
END:VCALENDAR
""",
        datetime(2026, 1, 25, 8, 0, tzinfo=timezone.utc),
        timedelta(days=2),
    )

    selection = select_trip_day(events, datetime(2026, 1, 25, 8, 0, tzinfo=timezone.utc))

    assert selection is not None
    assert selection.day_start == datetime(2026, 1, 25, 0, 0, tzinfo=timezone.utc)
    assert selection.day_end == datetime(2026, 1, 26, 0, 0, tzinfo=timezone.utc)
    assert [event.uid for event in selection.events] == ["hotel-1", "flight-1"]


def test_select_trip_day_ignores_active_off_event_for_anchor_selection():
    events = parse_roster_events(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:off-1
DTSTART:20260124T000000Z
DTEND:20260124T235900Z
SUMMARY:Off
END:VEVENT
BEGIN:VEVENT
UID:flight-1
DTSTART:20260125T133000Z
DTEND:20260125T150000Z
SUMMARY:KL1832 STR-AMS
END:VEVENT
END:VCALENDAR
""",
        datetime(2026, 1, 24, 8, 0, tzinfo=timezone.utc),
        timedelta(days=3),
    )

    selection = select_trip_day(events, datetime(2026, 1, 24, 8, 0, tzinfo=timezone.utc))

    assert selection is not None
    assert selection.day_start == datetime(2026, 1, 25, 0, 0, tzinfo=timezone.utc)
    assert selection.day_end == datetime(2026, 1, 26, 0, 0, tzinfo=timezone.utc)
    assert [event.uid for event in selection.events] == ["flight-1"]


def test_day_bounds_uses_local_date():
    tzinfo = timezone(timedelta(hours=2))

    start, end = day_bounds(datetime(2026, 1, 24, 23, 30, tzinfo=timezone.utc), tzinfo)

    assert start == datetime(2026, 1, 25, 0, 0, tzinfo=tzinfo)
    assert end == datetime(2026, 1, 26, 0, 0, tzinfo=tzinfo)
