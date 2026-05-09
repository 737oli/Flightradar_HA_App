from datetime import datetime, timedelta, timezone
from custom_components.flight_tracker.models.flight import FlightEvent


def test_live_data_window_is_one_hour_before_until_one_hour_after_flight(
    homeassistant_stubs,
):
    from custom_components.flight_tracker.coordinator import (
        _current_flight,
        _live_candidates,
    )

    flight = FlightEvent(
        uid="flight-1",
        summary="KL1327 AMS-KRK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type="E190",
        is_deadhead=False,
    )

    assert _current_flight([flight], flight.start - timedelta(minutes=61)) is None
    assert _current_flight([flight], flight.start - timedelta(minutes=60)) == flight
    assert _current_flight([flight], flight.end + timedelta(minutes=60)) == flight
    assert _current_flight([flight], flight.end + timedelta(minutes=61)) is None

    assert not _live_candidates(
        [flight], flight.start - timedelta(minutes=61), None, flight
    )
    assert _live_candidates(
        [flight], flight.start - timedelta(minutes=60), flight, flight
    ) == [flight]
