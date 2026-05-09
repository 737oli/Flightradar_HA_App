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
services = sys.modules.setdefault(
    "custom_components.flight_tracker.services",
    ModuleType("custom_components.flight_tracker.services"),
)
custom_components.__path__ = [str(ROOT / "custom_components")]
flight_tracker.__path__ = [str(PACKAGE_PATH)]
services.__path__ = [str(PACKAGE_PATH / "services")]


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
travel_status_module = load_module(
    "custom_components.flight_tracker.services.travel_status",
    PACKAGE_PATH / "services" / "travel_status.py",
)

FlightEvent = calendar_module.FlightEvent
FlightStatus = api_module.FlightStatus
build_travel_status = travel_status_module.build_travel_status


def flight_event(start, end):
    return FlightEvent(
        uid="flight-1",
        summary="KL1327 AMS-KRK",
        description="",
        location="",
        start=start,
        end=end,
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type="E75",
        is_deadhead=False,
    )


def test_travel_status_summarizes_next_flight():
    now = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    event = flight_event(now + timedelta(hours=4), now + timedelta(hours=6))

    summary = build_travel_status(None, event, None, None, now)

    assert summary.phase == "upcoming"
    assert summary.native_value == "Next flight: KL1327"
    assert summary.headline == "Next flight to KRK"
    assert summary.minutes_until_departure == 240
    assert summary.is_active is False
    assert summary.is_delayed is False


def test_travel_status_marks_arriving_soon_while_airborne():
    now = datetime(2026, 5, 6, 14, 45, tzinfo=timezone.utc)
    event = flight_event(
        datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
    )
    status = FlightStatus(
        ident="KL1327",
        source="airfranceklm",
        actual_departure=datetime(2026, 5, 6, 13, 28, tzinfo=timezone.utc),
        estimated_arrival=datetime(2026, 5, 6, 15, 5, tzinfo=timezone.utc),
        departure_delay_minutes=8,
        arrival_delay_minutes=-5,
        aircraft_registration="PH-EXA",
        aircraft_type="E75",
    )

    summary = build_travel_status(event, None, status, None, now)

    assert summary.phase == "arriving_soon"
    assert summary.native_value == "Arriving soon: KRK"
    assert summary.minutes_until_arrival == 20
    assert summary.is_active is True
    assert summary.is_airborne is True
    assert summary.is_arriving_soon is True
    assert summary.is_delayed is True


def test_travel_status_marks_pre_departure_delay_with_reason_and_code():
    now = datetime(2026, 5, 6, 12, 30, tzinfo=timezone.utc)
    event = flight_event(
        datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
    )
    status = FlightStatus(
        ident="KL1327",
        source="airfranceklm",
        estimated_departure=datetime(2026, 5, 6, 13, 40, tzinfo=timezone.utc),
        estimated_arrival=datetime(2026, 5, 6, 15, 30, tzinfo=timezone.utc),
        departure_delay_minutes=20,
        arrival_delay_minutes=20,
        delay_code="93",
        delay_reason_public="Late inbound aircraft",
        departure_terminal="1",
        departure_gate="A10",
    )

    summary = build_travel_status(event, None, status, None, now)

    assert summary.phase == "delayed"
    assert summary.native_value == "Delayed: KL1327"
    assert summary.max_delay_minutes == 20
    assert summary.notification_key == "delayed:flight-1:2"
    assert "Late inbound aircraft" in summary.notification_message
    assert "Code 93" in summary.notification_message
