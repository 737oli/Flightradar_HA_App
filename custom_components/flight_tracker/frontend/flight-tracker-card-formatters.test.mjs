import test from "node:test";
import assert from "node:assert/strict";

import {
  airportStatus,
  durationLabel,
  isFlightState,
  routePart,
  timelineText,
} from "./flight-tracker-card-formatters.js";

test("isFlightState requires a non-empty flight_number", () => {
  assert.equal(isFlightState(undefined), false);
  assert.equal(isFlightState({ state: "unknown", attributes: { flight_number: "KL123" } }), false);
  assert.equal(isFlightState({ state: "on_time", attributes: {} }), false);
  assert.equal(isFlightState({ state: "on_time", attributes: { flight_number: "KL123" } }), true);
});

test("timelineText switches phase around departure and arrival", () => {
  const departure = new Date("2026-01-01T10:00:00Z");
  const arrival = new Date("2026-01-01T12:00:00Z");

  assert.deepEqual(timelineText(departure, arrival, departure.getTime() - 60 * 1000), {
    phase: "departure",
    value: "1m",
    label: "Until Departure",
  });
  assert.deepEqual(timelineText(departure, arrival, departure.getTime() + 30 * 60 * 1000), {
    phase: "arrival",
    value: "1h 30m",
    label: "Until Arrival",
  });
  assert.deepEqual(timelineText(departure, arrival, arrival.getTime() + 1), {
    phase: "arrived",
    value: "Arrived",
    label: "Flight Complete",
  });
});

test("airportStatus and routePart preserve display formatting", () => {
  assert.equal(routePart("AMS -> JFK", 1), "JFK");
  assert.equal(airportStatus("3", "D12", "On Time"), "T3 · Gate D12 · On Time");
});

test("durationLabel rounds to whole minutes", () => {
  assert.equal(durationLabel(65 * 60 * 1000), "1h 5m");
  assert.equal(durationLabel(45 * 1000), "1m");
});
