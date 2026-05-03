# Home Assistant iCal Flight Tracker

A custom Home Assistant integration that reads flights from an iCal calendar and exposes the current trip as Home Assistant entities.

The goal is simple: keep the calendar as the source of truth, then let someone at home see your next KLM flight, your current flight window, and live aircraft position through the Air France-KLM Open Data API.

The parser is tuned for KLC-style roster events such as `KL1327 AMS-KRK` and `DH/KL1978 DBV-AMS`, while still accepting more generic KLM calendar text such as `KL 643 AMS to JFK`. Non-`KL` flight numbers are ignored.

## What It Creates

- `sensor.<name>_next_flight`
- `sensor.<name>_current_flight`
- `sensor.<name>_trip_timeline`
- `sensor.<name>_travel_status`
- `sensor.<name>_tracked_flights`
- `binary_sensor.<name>_flight_active`
- `binary_sensor.<name>_flight_airborne`
- `binary_sensor.<name>_flight_arriving_soon`
- `binary_sensor.<name>_flight_delayed`
- `binary_sensor.<name>_flight_landed`
- `device_tracker.<name>_flight_location`
- A Lovelace custom card at `/flight_tracker_static/flight-tracker-card.js`

The `device_tracker` entity only has GPS coordinates when live trajectory data is available from the Air France-KLM Flight Status API. Live status is requested from one hour before scheduled departure until one hour after scheduled arrival. An Air France-KLM Open Data API key is required during setup.

## Installation

1. Copy `custom_components/flight_tracker` into your Home Assistant config directory:

   ```text
   /config/custom_components/flight_tracker
   ```

2. Restart Home Assistant.
3. Go to **Settings -> Devices & services -> Add integration**.
4. Search for **iCal Flight Tracker**.
5. Enter your private KLC roster iCal URL.
6. Enter your Air France-KLM Open Data API key for live flight status, gates, terminals, aircraft details, and trajectory position.

## Dashboard Card

The integration serves a no-build Lovelace card that is styled after the compact flight status card in your reference screenshots.

Add this dashboard resource:

```text
/flight_tracker_static/flight-tracker-card.js?v=0.4.1
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

For the whole travel day view, add the timeline card:

```yaml
type: custom:flight-tracker-timeline-card
entity: sensor.ical_flight_tracker_trip_timeline
```

The timeline card shows the relevant roster day with hotel, taxi/transfer, previous flight, current flight, next flight, layovers between flights, and a base return segment when the final leg returns to AMS without a hotel afterward.

If you prefer to use existing HACS frontend cards instead, the same entity attributes can also be styled with `button-card` plus `card-mod`, but this repository includes its own card so the first version does not depend on extra frontend plugins.

## Friendly Status And Notifications

The `travel_status` sensor turns the raw flight data into a home-friendly summary such as `Next flight: KL1327`, `Airborne: AMS -> KRK`, `Arriving soon: KRK`, or `Delayed: KL1327`.

Useful attributes on the travel status sensor:

- `headline`
- `detail`
- `notification_title`
- `notification_message`
- `notification_key`
- `phase`
- `minutes_until_departure`
- `minutes_until_arrival`
- `max_delay_minutes`

The `trip_timeline` sensor exposes:

- `headline`
- `detail`
- `segments`
- `current_segment`
- `previous_flight`
- `current_flight`
- `next_flight`
- `duty_start`
- `duty_end`

The binary sensors are designed as simple notification triggers. For example, notify when the flight is delayed:

```yaml
alias: Flight delayed notification
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.ical_flight_tracker_flight_delayed
    to: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: "{{ state_attr('sensor.ical_flight_tracker_travel_status', 'notification_title') }}"
      message: "{{ state_attr('sensor.ical_flight_tracker_travel_status', 'notification_message') }}"
```

Or notify when the trip status changes between meaningful phases:

```yaml
alias: Flight status changed
mode: single
trigger:
  - platform: state
    entity_id: sensor.ical_flight_tracker_travel_status
    attribute: notification_key
condition:
  - condition: template
    value_template: "{{ trigger.from_state is not none and trigger.from_state.attributes.notification_key != trigger.to_state.attributes.notification_key }}"
action:
  - service: notify.mobile_app_phone
    data:
      title: "{{ trigger.to_state.attributes.notification_title }}"
      message: "{{ trigger.to_state.attributes.notification_message }}"
```

## Calendar Format

The parser only tracks KLM flight numbers such as:

- `KL1234`
- `KL 643`
- `DH/KL1978`

It also tries to detect route text like:

- `BRU -> JFK`
- `AMS to LHR`
- `CDG → NRT`
- `AMS-KRK`

This works well with KLC rosters, TripIt-style calendars, airline booking calendars, and hand-authored calendar events, as long as the `KL` flight number appears in the event summary, description, or location.

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

## Air France-KLM API Notes

The Air France-KLM Flight Status API is required. This integration limits live enrichment to KLM flights that are close to the current time so it does not repeatedly query every future calendar event.

Relevant endpoints:

- `GET https://api.airfranceklm.com/opendata/flightstatus/v4/flights`
- `GET https://api.airfranceklm.com/opendata/flightstatus/v4/flights/{flightId}`

The integration sends your API key in the `API-Key` header and always uses `KL` as the carrier code and consumer host.

Live attributes include actual/estimated departure and arrival times, terminal/gate, aircraft registration, `typeCode`, and AF-KLM irregularity details such as delay duration, delay reason, and delay code. The bundled card treats delays of 5 minutes or less as on time and marks later positive delays in red.

## Development

Install test dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python3 -m pytest
```
