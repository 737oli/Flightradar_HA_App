import test from "node:test";
import assert from "node:assert/strict";

import { formatTime } from "./flight-tracker-card-formatters.js";
import { renderFlightCard } from "./flight-tracker-flight-card-render.js";

test("flight card shows stand-only detail and scheduled time with live delta", () => {
  const scheduledDeparture = "2099-01-01T10:00:00Z";
  const actualDeparture = "2099-01-01T10:20:00Z";
  const html = renderFlightCard(
    {
      state: "delayed",
      attributes: {
        flight_number: "KL1937",
        airline_code: "KL",
        departure_airport: "AMS",
        arrival_airport: "GVA",
        scheduled_departure: scheduledDeparture,
        scheduled_arrival: "2099-01-01T11:30:00Z",
        actual_departure: actualDeparture,
        estimated_arrival: "2099-01-01T11:43:00Z",
        departure_terminal: "1",
        departure_gate: "B06",
        departure_parking_position: "B06",
        arrival_terminal: "2",
        arrival_gate: "A4",
        arrival_parking_position: "44",
        departure_delay_minutes: 20,
        arrival_delay_minutes: 13,
      },
    },
    new Date("2099-01-01T09:30:00Z").getTime(),
  );

  assert.match(html, /Stand B06/);
  assert.match(html, /Stand 44/);
  assert.match(html, /flight-time-delta is-late">\+20<\/sup>/);
  assert.match(html, /flight-time-delta is-late">\+13<\/sup>/);
  assert.match(html, new RegExp(escapeRegExp(formatTime(new Date(scheduledDeparture)))));
  assert.doesNotMatch(html, new RegExp(escapeRegExp(formatTime(new Date(actualDeparture)))));
  assert.doesNotMatch(html, /T1/);
  assert.doesNotMatch(html, /20m Late/);
  assert.doesNotMatch(html, /Gate B06/);
});

test("flight card falls back to gate when stand is unavailable", () => {
  const html = renderFlightCard({
    state: "on_time",
    attributes: {
      flight_number: "KL1001",
      departure_airport: "AMS",
      arrival_airport: "LHR",
      scheduled_departure: "2099-01-01T10:00:00Z",
      scheduled_arrival: "2099-01-01T11:00:00Z",
      departure_gate: "C12",
      arrival_gate: "A10",
    },
  });

  assert.match(html, /Gate C12/);
  assert.match(html, /Gate A10/);
});

test("flight card renders compact delay text with full hover title", () => {
  const html = renderFlightCard({
    state: "delayed",
    attributes: {
      flight_number: "KL1937",
      departure_airport: "AMS",
      arrival_airport: "GVA",
      scheduled_departure: "2099-01-01T10:00:00Z",
      scheduled_arrival: "2099-01-01T11:30:00Z",
      departure_delay_minutes: 20,
      irregularity_delay_duration_public: "PT20M",
      irregularity_delay_reason_public: "Restrictions from Air Traffic Control",
      irregularity_delay_code: "81",
      irregularity_delay_sub_code: "A",
    },
  });

  assert.match(html, /20m · ATC restrictions · 81A/);
  assert.match(
    html,
    /title="Delayed 20m · Restrictions from Air Traffic Control · Code 81A"/,
  );
});

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
