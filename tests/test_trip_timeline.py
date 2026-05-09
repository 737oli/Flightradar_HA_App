from datetime import datetime, timedelta, timezone

from custom_components.flight_tracker.models.status import FlightStatus
from custom_components.flight_tracker.parsers.roster import parse_roster_events
from custom_components.flight_tracker.services.trip_timeline import build_trip_timeline


def test_trip_timeline_shows_layover_between_previous_and_next_flight():
    events = parse_roster_events(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:duty-1
DTSTART:20260124T152000Z
DTEND:20260124T221000Z
SUMMARY:Flight Day
END:VEVENT
BEGIN:VEVENT
UID:flight-1
DTSTART:20260124T162000Z
DTEND:20260124T183500Z
SUMMARY:DH/KL1526 BIO-AMS
END:VEVENT
BEGIN:VEVENT
UID:flight-2
DTSTART:20260124T203000Z
DTEND:20260124T214000Z
SUMMARY:KL1835 AMS-STR
LOCATION:E175
END:VEVENT
BEGIN:VEVENT
UID:hotel-1
DTSTART:20260124T221000Z
DTEND:20260125T120000Z
SUMMARY:Hotel STR
END:VEVENT
END:VCALENDAR
""",
        datetime(2026, 1, 24, 19, 0, tzinfo=timezone.utc),
        timedelta(days=2),
    )

    timeline = build_trip_timeline(
        events,
        {},
        datetime(2026, 1, 24, 19, 0, tzinfo=timezone.utc),
    )

    assert timeline.headline == "Travel day"
    assert timeline.detail == "2 flights · Hotel Stuttgart"
    assert timeline.native_value == "Layover AMS"
    assert [segment["kind"] for segment in timeline.segments] == [
        "flight",
        "layover",
        "flight",
        "hotel",
    ]
    assert timeline.current_segment["kind"] == "layover"
    assert timeline.previous_flight["flight_number"] == "KL1526"
    assert timeline.next_flight["flight_number"] == "KL1835"


def test_trip_timeline_uses_roster_ground_time_instead_of_duplicate_layover():
    events = parse_roster_events(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:duty-1
DTSTART:20260124T142000Z
DTEND:20260124T230500Z
SUMMARY:Flight Day
END:VEVENT
BEGIN:VEVENT
UID:flight-1
DTSTART:20260124T152000Z
DTEND:20260124T171000Z
SUMMARY:KL1327 AMS-KRK
LOCATION:E195
END:VEVENT
BEGIN:VEVENT
UID:turn-1
DTSTART:20260124T171000Z
DTEND:20260124T175500Z
SUMMARY:Omdraai: 00:45
END:VEVENT
BEGIN:VEVENT
UID:flight-2
DTSTART:20260124T175500Z
DTEND:20260124T195500Z
SUMMARY:KL1328 KRK-AMS
LOCATION:E195
END:VEVENT
BEGIN:VEVENT
UID:ground-1
DTSTART:20260124T195500Z
DTEND:20260124T210000Z
SUMMARY:Grondtijd: 01:05
LOCATION:Tijd tot lopen: 00:20 (20:15)
END:VEVENT
BEGIN:VEVENT
UID:flight-3
DTSTART:20260124T210000Z
DTEND:20260124T232500Z
SUMMARY:KL1981 AMS-DBV
LOCATION:E190
END:VEVENT
BEGIN:VEVENT
UID:hotel-1
DTSTART:20260124T235500Z
DTEND:20260125T120500Z
SUMMARY:Hotel DBV
END:VEVENT
END:VCALENDAR
""",
        datetime(2026, 1, 24, 17, 20, tzinfo=timezone.utc),
        timedelta(days=2),
    )

    timeline = build_trip_timeline(
        events,
        {},
        datetime(2026, 1, 24, 17, 20, tzinfo=timezone.utc),
    )

    assert timeline.headline == "Travel day"
    assert timeline.detail == "3 flights · Hotel Dubrovnik"
    assert timeline.native_value == "Omdraai: 00:45"
    assert [segment["kind"] for segment in timeline.segments] == [
        "flight",
        "ground_time",
        "flight",
        "ground_time",
        "flight",
        "hotel",
    ]
    assert "layover" not in [segment["kind"] for segment in timeline.segments]
    assert timeline.current_segment["kind"] == "ground_time"
    assert timeline.current_segment["title"] == "Omdraai: 00:45"
    assert timeline.current_segment["status"] == "Now"
    assert "status" not in timeline.segments[2]
    assert "status" not in timeline.segments[3]
    assert "status" not in timeline.segments[4]
    assert "status" not in timeline.segments[5]


def test_trip_timeline_exposes_live_time_deltas_for_flights():
    events = parse_roster_events(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:flight-1
DTSTART:20260124T152000Z
DTEND:20260124T171000Z
SUMMARY:KL1327 AMS-KRK
LOCATION:E195
END:VEVENT
END:VCALENDAR
""",
        datetime(2026, 1, 24, 18, 0, tzinfo=timezone.utc),
        timedelta(days=1),
    )

    status = FlightStatus(
        ident="KL1327",
        source="airfranceklm",
        status="Landed",
        actual_departure=datetime(2026, 1, 24, 15, 28, tzinfo=timezone.utc),
        actual_arrival=datetime(2026, 1, 24, 17, 6, tzinfo=timezone.utc),
        departure_delay_minutes=8,
        arrival_delay_minutes=-4,
        aircraft_type="E195",
    )

    timeline = build_trip_timeline(
        events,
        {"flight-1": status},
        datetime(2026, 1, 24, 18, 0, tzinfo=timezone.utc),
    )
    segment = timeline.segments[0]

    assert segment["start"] == "2026-01-24T15:28:00+00:00"
    assert segment["end"] == "2026-01-24T17:06:00+00:00"
    assert segment["scheduled_start"] == "2026-01-24T15:20:00+00:00"
    assert segment["scheduled_end"] == "2026-01-24T17:10:00+00:00"
    assert segment["departure_time_delta_minutes"] == 8
    assert segment["arrival_time_delta_minutes"] == -4
    assert segment["detail"] == "AMS - KRK · E195"


def test_trip_timeline_adds_base_return_after_final_ams_arrival():
    events = parse_roster_events(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:duty-1
DTSTART:20260125T123000Z
DTEND:20260125T211000Z
SUMMARY:Flight Day
END:VEVENT
BEGIN:VEVENT
UID:flight-1
DTSTART:20260125T133000Z
DTEND:20260125T150000Z
SUMMARY:KL1832 STR-AMS
END:VEVENT
BEGIN:VEVENT
UID:flight-2
DTSTART:20260125T162500Z
DTEND:20260125T180000Z
SUMMARY:KL1617 AMS-LIN
END:VEVENT
BEGIN:VEVENT
UID:flight-3
DTSTART:20260125T184500Z
DTEND:20260125T204000Z
SUMMARY:KL1618 LIN-AMS
END:VEVENT
END:VCALENDAR
""",
        datetime(2026, 1, 25, 20, 50, tzinfo=timezone.utc),
        timedelta(days=2),
    )

    timeline = build_trip_timeline(
        events,
        {},
        datetime(2026, 1, 25, 20, 50, tzinfo=timezone.utc),
    )

    assert timeline.native_value == "Back at Amsterdam"
    assert timeline.destination == "AMS"
    assert timeline.current_segment["kind"] == "base_return"
    assert timeline.current_segment["airport"] == "AMS"
    assert timeline.current_segment["title"] == "Back at Amsterdam"
    assert timeline.current_segment["detail"] == ""
    assert timeline.detail == "3 flights · base return"


def test_trip_timeline_uses_today_when_hotel_started_yesterday():
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
UID:taxi-1
DTSTART:20260125T120000Z
DTEND:20260125T123000Z
SUMMARY:Taxi
END:VEVENT
BEGIN:VEVENT
UID:duty-1
DTSTART:20260125T123000Z
DTEND:20260125T211000Z
SUMMARY:Flight Day
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

    timeline = build_trip_timeline(
        events,
        {},
        datetime(2026, 1, 25, 8, 0, tzinfo=timezone.utc),
    )

    assert timeline.current_segment["kind"] == "hotel"
    assert timeline.next_flight["flight_number"] == "KL1832"
    assert [segment["kind"] for segment in timeline.segments] == [
        "hotel",
        "transfer",
        "flight",
        "base_return",
    ]
    assert timeline.segments[1]["title"] == "Taxi"
    assert timeline.segments[1]["detail"] == ""
    assert timeline.detail == "Hotel Stuttgart · 1 flight · base return"
