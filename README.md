# Home Assistant iCal Flight Tracker

A custom Home Assistant integration that reads flights from an iCal calendar and exposes the current trip as Home Assistant entities.

The goal is simple: keep the calendar as the source of truth, then let someone at home see your next flight, your current flight window, and live aircraft position when a FlightAware AeroAPI key is configured.

The current parser is tuned for KLC-style roster events such as `KL1327 AMS-KRK` and `DH/KL1978 DBV-AMS`, while still accepting more generic calendar text such as `KL 643 AMS to JFK`.

## What It Creates

- `sensor.<name>_next_flight`
- `sensor.<name>_current_flight`
- `sensor.<name>_tracked_flights`
- `device_tracker.<name>_flight_location`
- A Lovelace custom card at `/flight_tracker_static/flight-tracker-card.js`

The `device_tracker` entity only has GPS coordinates when live position data is available from FlightAware. Without an API key, the integration still works as a calendar-based trip tracker.

## Installation

1. Copy `custom_components/flight_tracker` into your Home Assistant config directory:

   ```text
   /config/custom_components/flight_tracker
   ```

2. Restart Home Assistant.
3. Go to **Settings -> Devices & services -> Add integration**.
4. Search for **iCal Flight Tracker**.
5. Enter your private KLC roster iCal URL.
6. Optionally enter a FlightAware AeroAPI key for live flight status and aircraft position.

## Dashboard Card

The integration serves a no-build Lovelace card that is styled after the compact flight status card in your reference screenshots.

Add this dashboard resource:

```text
/flight_tracker_static/flight-tracker-card.js
```

Resource type:

```text
JavaScript module
```

Then add this card:

```yaml
type: custom:flight-tracker-card
current_entity: sensor.ical_flight_tracker_current_flight
next_entity: sensor.ical_flight_tracker_next_flight
```

If you prefer to use existing HACS frontend cards instead, the same entity attributes can also be styled with `button-card` plus `card-mod`, but this repository includes its own card so the first version does not depend on extra frontend plugins.

## Calendar Format

The parser looks for common flight numbers such as:

- `BA 391`
- `SN3175`
- `UAL 950`
- `KL1234`

It also tries to detect route text like:

- `BRU -> JFK`
- `AMS to LHR`
- `CDG → NRT`
- `AMS-KRK`

This works well with TripIt-style calendars, airline booking calendars, and hand-authored calendar events, as long as the flight number appears in the event summary, description, or location.

## Basic Built-In Dashboard Card

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Olivier's Flights
    entities:
      - sensor.ical_flight_tracker_current_flight
      - sensor.ical_flight_tracker_next_flight
      - sensor.ical_flight_tracker_tracked_flights
  - type: map
    entities:
      - device_tracker.ical_flight_tracker_flight_location
    hours_to_show: 12
```

## FlightAware Notes

FlightAware AeroAPI is optional and usage-based. This integration limits live enrichment to flights that are close to the current time so it does not repeatedly query every future calendar event.

Relevant endpoints:

- `GET /flights/{ident}`
- `GET /flights/{id}/position`

## Development

Install test dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python3 -m pytest
```
