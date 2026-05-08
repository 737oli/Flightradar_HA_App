from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
import asyncio
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

FlightEvent = calendar_module.FlightEvent
_numeric_flight_number = api_module._numeric_flight_number
_flight_status_id = api_module._flight_status_id
_status_from_flight = api_module._status_from_flight
AirFranceKlmClient = api_module.AirFranceKlmClient
AFKL_BASE_URL = api_module.AFKL_BASE_URL


def test_numeric_flight_number_is_padded_for_afkl_query():
    assert _numeric_flight_number("KL1327") == "1327"
    assert _numeric_flight_number("KL 643") == "0643"


def test_flight_status_id_uses_documented_direct_lookup_format():
    event = FlightEvent(
        uid="flight-id",
        summary="KL643 AMS-JFK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 22, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 7, 6, 10, tzinfo=timezone.utc),
        flight_number="KL643",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="JFK",
        aircraft_type=None,
        is_deadhead=False,
    )

    assert _flight_status_id(event) == "20260506+KL+0643"

    krk_event = FlightEvent(
        uid="flight-id-krk",
        summary="KL1327 AMS-KRK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type=None,
        is_deadhead=False,
    )

    assert _flight_status_id(krk_event) == "20260506+KL+1327"


def test_status_from_afkl_flight_maps_live_attributes():
    event = FlightEvent(
        uid="flight-1",
        summary="KL1327 AMS-KRK",
        description="",
        location="E190",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type="E190",
        is_deadhead=False,
    )
    flight = {
        "id": "20260506+KL+1327",
        "flightStatusPublicLangTransl": "On time",
        "flightLegs": [
            {
                "legStatusPublicLangTransl": "Departed",
                "completionPercentage": "42",
                "departureInformation": {
                    "airport": {
                        "places": {
                            "terminalCode": "1",
                            "gateNumber": ["A10"],
                        }
                    },
                    "times": {
                        "scheduled": "2026-05-06T13:20:00Z",
                        "estimatedPublic": "2026-05-06T13:25:00Z",
                        "actualTakeOffTime": "2026-05-06T13:28:00Z",
                    },
                },
                "arrivalInformation": {
                    "airport": {
                        "places": {
                            "terminalCode": "2",
                            "gateNumber": ["B04"],
                        }
                    },
                    "times": {
                        "scheduled": "2026-05-06T15:10:00Z",
                        "estimatedArrival": "2026-05-06T15:05:00Z",
                    },
                },
                "aircraft": {
                    "registration": "PH-EXA",
                    "typeCode": "E75",
                },
                "irregularity": {
                    "delayDurationPublic": "PT8M",
                    "delayInformation": [
                        {
                            "delayCode": "81",
                            "delayDuration": "8",
                            "delayReason": "ATC",
                            "delayReasonCodePublic": "AIRPORT",
                            "delayReasonPublicShort": "Air traffic control",
                            "delaySubCode": "A",
                        }
                    ],
                },
                "trajectories": [
                    {
                        "aircraftPositionTime": "2026-05-06T14:00:00Z",
                        "location": {
                            "latitude": 50.1,
                            "longitude": 4.2,
                            "altitude": 31000,
                        },
                    }
                ],
            }
        ],
    }

    status = _status_from_flight(event, flight)

    assert status.source == "airfranceklm"
    assert status.provider_flight_id == "20260506+KL+1327"
    assert status.status == "Departed"
    assert status.departure_delay_minutes == 8
    assert status.arrival_delay_minutes == -5
    assert status.departure_terminal == "1"
    assert status.departure_gate == "A10"
    assert status.arrival_terminal == "2"
    assert status.arrival_gate == "B04"
    assert status.aircraft_registration == "PH-EXA"
    assert status.aircraft_type == "E75"
    assert status.delay_code == "81"
    assert status.delay_sub_code == "A"
    assert status.delay_duration == "8"
    assert status.delay_duration_public == "PT8M"
    assert status.delay_reason == "ATC"
    assert status.delay_reason_public == "Air traffic control"
    assert status.delay_reason_code_public == "AIRPORT"
    assert status.progress_percent == 42
    assert status.latitude == 50.1
    assert status.longitude == 4.2
    assert status.altitude_ft == 31000


def test_status_prefers_latest_public_arrival_eta_for_delay():
    event = FlightEvent(
        uid="flight-live-eta",
        summary="KL1978 DBV-AMS",
        description="",
        location="E195",
        start=datetime(2026, 5, 7, 11, 25, tzinfo=timezone.utc),
        end=datetime(2026, 5, 7, 13, 55, tzinfo=timezone.utc),
        flight_number="KL1978",
        airline_code="KL",
        departure_airport="DBV",
        arrival_airport="AMS",
        aircraft_type="E195",
        is_deadhead=False,
    )
    flight = {
        "id": "20260507+KL+1978",
        "flightLegs": [
            {
                "departureInformation": {
                    "times": {
                        "scheduled": "2026-05-07T11:25:00Z",
                        "actual": "2026-05-07T11:30:00Z",
                    }
                },
                "arrivalInformation": {
                    "times": {
                        "scheduled": "2026-05-07T13:55:00Z",
                        "estimatedArrival": "2026-05-07T13:55:00Z",
                        "estimatedPublic": "2026-05-07T14:10:00Z",
                        "latestPublished": "2026-05-07T14:17:00Z",
                    }
                },
            }
        ],
    }

    status = _status_from_flight(event, flight)

    assert status.estimated_arrival == datetime(
        2026, 5, 7, 14, 17, tzinfo=timezone.utc
    )
    assert status.arrival_delay_minutes == 22


def test_status_uses_arrival_irregularity_delay_when_eta_is_stale():
    event = FlightEvent(
        uid="flight-arrival-delay",
        summary="KL1978 DBV-AMS",
        description="",
        location="E195",
        start=datetime(2026, 5, 7, 11, 25, tzinfo=timezone.utc),
        end=datetime(2026, 5, 7, 13, 55, tzinfo=timezone.utc),
        flight_number="KL1978",
        airline_code="KL",
        departure_airport="DBV",
        arrival_airport="AMS",
        aircraft_type="E195",
        is_deadhead=False,
    )
    flight = {
        "id": "20260507+KL+1978",
        "flightLegs": [
            {
                "departureInformation": {
                    "times": {"scheduled": "2026-05-07T11:25:00Z"}
                },
                "arrivalInformation": {
                    "times": {
                        "scheduled": "2026-05-07T13:55:00Z",
                        "estimatedArrival": "2026-05-07T13:55:00Z",
                    }
                },
                "irregularity": {
                    "delayDurationArrival": "PT18M",
                    "delayDurationPublic": "PT15M",
                },
            }
        ],
    }

    status = _status_from_flight(event, flight)

    assert status.arrival_delay_minutes == 18
    assert status.delay_duration_arrival == "PT18M"


def test_status_derives_arrival_eta_from_time_to_arrival():
    event = FlightEvent(
        uid="flight-time-to-arrival",
        summary="KL1978 DBV-AMS",
        description="",
        location="E195",
        start=datetime(2026, 5, 7, 11, 25, tzinfo=timezone.utc),
        end=datetime(2026, 5, 7, 13, 55, tzinfo=timezone.utc),
        flight_number="KL1978",
        airline_code="KL",
        departure_airport="DBV",
        arrival_airport="AMS",
        aircraft_type="E195",
        is_deadhead=False,
    )
    flight = {
        "id": "20260507+KL+1978",
        "flightLegs": [
            {
                "timeToArrival": "PT35M",
                "departureInformation": {
                    "times": {"scheduled": "2026-05-07T11:25:00Z"}
                },
                "arrivalInformation": {
                    "times": {"scheduled": "2026-05-07T13:55:00Z"}
                },
            }
        ],
    }

    status = _status_from_flight(
        event,
        flight,
        observed_at=datetime(2026, 5, 7, 13, 40, tzinfo=timezone.utc),
    )

    assert status.estimated_arrival == datetime(
        2026, 5, 7, 14, 15, tzinfo=timezone.utc
    )
    assert status.arrival_delay_minutes == 20


def test_afkl_client_uses_direct_flight_status_endpoint_and_api_key_header():
    event = FlightEvent(
        uid="flight-2",
        summary="KL0643 AMS-JFK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 21, 10, tzinfo=timezone.utc),
        flight_number="KL643",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="JFK",
        aircraft_type=None,
        is_deadhead=False,
    )
    session = FakeSession(
        [
            {
                "id": "20260506+KL+0643",
                "flightLegs": [
                    {
                        "departureInformation": {
                            "times": {
                                "scheduled": "2026-05-06T13:20:00Z",
                            }
                        },
                        "arrivalInformation": {
                            "times": {
                                "scheduled": "2026-05-06T21:10:00Z",
                            }
                        },
                    }
                ],
            },
        ]
    )

    status = asyncio.run(
        AirFranceKlmClient(session, "secret-key", "AF").async_get_status(event)
    )

    assert status.provider_flight_id == "20260506+KL+0643"
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{AFKL_BASE_URL}/20260506%2BKL%2B0643"
    assert session.calls[0]["headers"]["API-Key"] == "secret-key"
    assert session.calls[0]["headers"]["afkl-travel-host"] == "KL"
    assert session.calls[0]["params"] == {}


def test_afkl_client_ignores_non_kl_events():
    event = FlightEvent(
        uid="flight-3",
        summary="AF1341 AMS-CDG",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
        flight_number="AF1341",
        airline_code="AF",
        departure_airport="AMS",
        arrival_airport="CDG",
        aircraft_type=None,
        is_deadhead=False,
    )
    session = FakeSession([])

    status = asyncio.run(
        AirFranceKlmClient(session, "secret-key", "AF").async_get_status(event)
    )

    assert status is None
    assert session.calls == []


def test_afkl_client_uses_cached_flight_id_for_detail_request_only():
    event = FlightEvent(
        uid="flight-4",
        summary="KL0643 AMS-JFK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 21, 10, tzinfo=timezone.utc),
        flight_number="KL643",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="JFK",
        aircraft_type=None,
        is_deadhead=False,
    )
    session = FakeSession(
        [
            {
                "id": "20260506+KL+0643",
                "flightLegs": [
                    {
                        "departureInformation": {
                            "times": {
                                "scheduled": "2026-05-06T13:20:00Z",
                            }
                        },
                        "arrivalInformation": {
                            "times": {
                                "scheduled": "2026-05-06T21:10:00Z",
                            }
                        },
                    }
                ],
            },
        ]
    )

    status = asyncio.run(
        AirFranceKlmClient(session, "secret-key").async_get_status(
            event, "20260506+KL+0643"
        )
    )

    assert status.provider_flight_id == "20260506+KL+0643"
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{AFKL_BASE_URL}/20260506%2BKL%2B0643"


def test_afkl_client_calls_request_guard_for_each_api_request():
    event = FlightEvent(
        uid="flight-5",
        summary="KL1327 AMS-KRK",
        description="",
        location="",
        start=datetime(2026, 5, 6, 13, 20, tzinfo=timezone.utc),
        end=datetime(2026, 5, 6, 15, 10, tzinfo=timezone.utc),
        flight_number="KL1327",
        airline_code="KL",
        departure_airport="AMS",
        arrival_airport="KRK",
        aircraft_type=None,
        is_deadhead=False,
    )
    session = FakeSession(
        [
            {
                "id": "20260506+KL+1327",
                "flightLegs": [
                    {
                        "departureInformation": {
                            "times": {
                                "scheduled": "2026-05-06T13:20:00Z",
                            }
                        },
                        "arrivalInformation": {
                            "times": {
                                "scheduled": "2026-05-06T15:10:00Z",
                            }
                        },
                    }
                ],
            },
        ]
    )
    guard_calls = 0

    async def request_guard():
        nonlocal guard_calls
        guard_calls += 1

    asyncio.run(
        AirFranceKlmClient(
            session, "secret-key", request_guard=request_guard
        ).async_get_status(event)
    )

    assert guard_calls == 1


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, headers, params, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return FakeResponse(self.payloads.pop(0))


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self):
        return None

    async def json(self, content_type=None):
        return self.payload
