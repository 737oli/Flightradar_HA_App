from custom_components.flight_tracker import api, api_usage, calendar, summary, timeline
from custom_components.flight_tracker.clients import afkl
from custom_components.flight_tracker.models import (
    ApiUsageSnapshot,
    FlightEvent,
    FlightStatus,
    RosterEvent,
    TravelStatusSummary,
    TripTimelineSummary,
)
from custom_components.flight_tracker.parsers import afkl_status, ical, roster
from custom_components.flight_tracker.services import travel_status, trip_timeline
from custom_components.flight_tracker.storage import api_usage as storage_api_usage


def test_api_wrapper_exports_air_france_klm_compatibility_symbols():
    assert api.__all__ == [
        "AFKL_BASE_URL",
        "KLM_CARRIER_CODE",
        "AirFranceKlmClient",
        "AirFranceKlmRequestBlocked",
        "FlightStatus",
        "RequestGuard",
        "status_from_flight",
    ]
    assert api.AFKL_BASE_URL == afkl.AFKL_BASE_URL
    assert api.KLM_CARRIER_CODE == afkl.KLM_CARRIER_CODE
    assert api.AirFranceKlmClient is afkl.AirFranceKlmClient
    assert api.AirFranceKlmRequestBlocked is afkl.AirFranceKlmRequestBlocked
    assert api.RequestGuard is afkl.RequestGuard
    assert api.FlightStatus is FlightStatus
    assert api.status_from_flight is afkl_status.status_from_flight


def test_api_usage_wrapper_exports_storage_compatibility_symbols():
    assert api_usage.__all__ == [
        "ApiUsageManager",
        "ApiUsageSnapshot",
        "DEFAULT_DAILY_REQUEST_LIMIT",
        "FLIGHT_ID_CACHE_TTL",
        "MIN_REQUEST_INTERVAL_SECONDS",
        "STORAGE_VERSION",
    ]
    assert api_usage.ApiUsageManager is storage_api_usage.ApiUsageManager
    assert api_usage.ApiUsageSnapshot is ApiUsageSnapshot
    assert (
        api_usage.DEFAULT_DAILY_REQUEST_LIMIT
        == storage_api_usage.DEFAULT_DAILY_REQUEST_LIMIT
    )
    assert api_usage.FLIGHT_ID_CACHE_TTL == storage_api_usage.FLIGHT_ID_CACHE_TTL
    assert (
        api_usage.MIN_REQUEST_INTERVAL_SECONDS
        == storage_api_usage.MIN_REQUEST_INTERVAL_SECONDS
    )
    assert api_usage.STORAGE_VERSION == storage_api_usage.STORAGE_VERSION


def test_calendar_wrapper_exports_parser_compatibility_symbols():
    assert calendar.__all__ == [
        "KLM_AIRLINE_CODE",
        "FlightEvent",
        "RosterEvent",
        "parse_flights",
        "parse_roster_events",
    ]
    assert calendar.KLM_AIRLINE_CODE == ical.KLM_AIRLINE_CODE
    assert calendar.FlightEvent is FlightEvent
    assert calendar.RosterEvent is RosterEvent
    assert calendar.parse_flights is ical.parse_flights
    assert calendar.parse_roster_events is roster.parse_roster_events


def test_summary_wrapper_exports_travel_status_compatibility_symbols():
    assert summary.__all__ == ["TravelStatusSummary", "build_travel_status"]
    assert summary.TravelStatusSummary is TravelStatusSummary
    assert summary.build_travel_status is travel_status.build_travel_status


def test_timeline_wrapper_exports_trip_timeline_compatibility_symbols():
    assert timeline.__all__ == ["TripTimelineSummary", "build_trip_timeline"]
    assert timeline.TripTimelineSummary is TripTimelineSummary
    assert timeline.build_trip_timeline is trip_timeline.build_trip_timeline
