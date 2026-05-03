from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
import sys

ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "flight_tracker"

custom_components = sys.modules.setdefault(
    "custom_components", ModuleType("custom_components")
)
flight_tracker = sys.modules.setdefault(
    "custom_components.flight_tracker", ModuleType("custom_components.flight_tracker")
)
custom_components.__path__ = [str(ROOT / "custom_components")]
flight_tracker.__path__ = [str(PACKAGE_PATH)]


def load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


calendar_module = load_module(
    "custom_components.flight_tracker.calendar", PACKAGE_PATH / "calendar.py"
)
api_module = load_module("custom_components.flight_tracker.api", PACKAGE_PATH / "api.py")
timeline_module = load_module(
    "custom_components.flight_tracker.timeline", PACKAGE_PATH / "timeline.py"
)

parse_roster_events = calendar_module.parse_roster_events
build_trip_timeline = timeline_module.build_trip_timeline


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

    assert timeline.headline == "Travel day: BIO -> STR"
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

    assert timeline.native_value == "Back at base"
    assert timeline.destination == "AMS"
    assert timeline.current_segment["kind"] == "base_return"
    assert timeline.current_segment["airport"] == "AMS"
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
