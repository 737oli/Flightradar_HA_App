import sys


def test_parser_and_service_imports_do_not_install_homeassistant_stubs():
    from custom_components.flight_tracker.parsers.roster import parse_roster_events
    from custom_components.flight_tracker.services.travel_status import build_travel_status

    assert parse_roster_events is not None
    assert build_travel_status is not None
    assert not _is_flight_tracker_test_stub("homeassistant")
    assert not _is_flight_tracker_test_stub("aiohttp")


def _is_flight_tracker_test_stub(module_name: str) -> bool:
    module = sys.modules.get(module_name)
    return bool(getattr(module, "__flight_tracker_test_stub__", False))
