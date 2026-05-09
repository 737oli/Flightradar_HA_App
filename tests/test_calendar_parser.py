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

SPEC = spec_from_file_location(
    "custom_components.flight_tracker.calendar",
    PACKAGE_PATH / "calendar.py",
)
calendar_module = module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = calendar_module
SPEC.loader.exec_module(calendar_module)
parse_flights = calendar_module.parse_flights
parse_roster_events = calendar_module.parse_roster_events


def test_ignores_non_kl_flight_numbers():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-1
DTSTART:20260501T091500Z
DTEND:20260501T112500Z
SUMMARY:SN 3175 BRU -> FCO
DESCRIPTION:Flight to Rome
END:VEVENT
END:VCALENDAR
"""

    flights = parse_flights(
        ics,
        datetime(2026, 4, 30, tzinfo=timezone.utc),
        timedelta(days=10),
    )

    assert flights == []


def test_parse_flight_number_from_description():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-2
DTSTART:20260502T203000Z
DTEND:20260503T073000Z
SUMMARY:Amsterdam to New York
LOCATION:AMS to JFK
DESCRIPTION:Flight KL 643
END:VEVENT
END:VCALENDAR
"""

    flights = parse_flights(
        ics,
        datetime(2026, 4, 30, tzinfo=timezone.utc),
        timedelta(days=10),
    )

    assert len(flights) == 1
    assert flights[0].flight_number == "KL643"
    assert flights[0].route == "AMS -> JFK"


def test_parse_klc_roster_summary_and_aircraft_type():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-4
DTSTART:20260506T132000Z
DTEND:20260506T151000Z
SUMMARY:KL1327 AMS-KRK
LOCATION:Joris Hoekstra (CPT)\\nAmber Trimborn (CS)\\n\\nE190
END:VEVENT
END:VCALENDAR
"""

    flights = parse_flights(
        ics,
        datetime(2026, 4, 30, tzinfo=timezone.utc),
        timedelta(days=10),
    )

    assert len(flights) == 1
    assert flights[0].flight_number == "KL1327"
    assert flights[0].airline_code == "KL"
    assert flights[0].route == "AMS -> KRK"
    assert flights[0].aircraft_type == "E190"
    assert flights[0].is_deadhead is False


def test_parse_deadhead_roster_summary():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-5
DTSTART:20260507T112500Z
DTEND:20260507T135500Z
SUMMARY:DH/KL1978 DBV-AMS
END:VEVENT
END:VCALENDAR
"""

    flights = parse_flights(
        ics,
        datetime(2026, 4, 30, tzinfo=timezone.utc),
        timedelta(days=10),
    )

    assert len(flights) == 1
    assert flights[0].flight_number == "KL1978"
    assert flights[0].route == "DBV -> AMS"
    assert flights[0].is_deadhead is True


def test_parse_roster_events_for_flight_day_hotel_and_taxi():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:duty-1
DTSTART:20260124T152000Z
DTEND:20260124T221000Z
SUMMARY:Flight Day
END:VEVENT
BEGIN:VEVENT
UID:hotel-1
DTSTART:20260124T221000Z
DTEND:20260125T120000Z
SUMMARY:Hotel STR
URL:http://maps.apple.com/?q=Jaz+in+the+City+Stuttgart%2C+Stuttgart
END:VEVENT
BEGIN:VEVENT
UID:taxi-1
DTSTART:20260125T120000Z
DTEND:20260125T123000Z
SUMMARY:Taxi
END:VEVENT
END:VCALENDAR
"""

    events = parse_roster_events(
        ics,
        datetime(2026, 1, 24, tzinfo=timezone.utc),
        timedelta(days=10),
    )

    assert [event.kind for event in events] == ["duty", "hotel", "transfer"]
    assert events[1].airport == "STR"
    assert events[1].url.startswith("http://maps.apple.com/")


def test_ignores_non_flight_events():
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-3
DTSTART:20260502T203000Z
DTEND:20260502T213000Z
SUMMARY:Dinner reservation
END:VEVENT
END:VCALENDAR
"""

    flights = parse_flights(
        ics,
        datetime(2026, 4, 30, tzinfo=timezone.utc),
        timedelta(days=10),
    )

    assert flights == []
