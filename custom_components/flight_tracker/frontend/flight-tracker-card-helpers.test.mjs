import test from "node:test";
import assert from "node:assert/strict";

import {
  flightTimeDeltaLabel,
  irregularityTitle,
  irregularityText,
  progressPercent,
  timeDeltaLabel,
  timelineRoute,
  timelineStatusHtml,
} from "./flight-tracker-card-helpers.js";

test("timelineRoute converts arrows to a dash", () => {
  assert.equal(timelineRoute("AMS → JFK"), "AMS - JFK");
  assert.equal(timelineRoute("AMS->JFK"), "AMS - JFK");
});

test("timeDeltaLabel marks late or early and hides zero delta", () => {
  assert.equal(timeDeltaLabel(0), "");
  assert.match(timeDeltaLabel(12), /timeline-time-delta is-late">\+12m/);
  assert.match(timeDeltaLabel(-4), /timeline-time-delta is-early">-4m/);
});

test("flightTimeDeltaLabel renders compact superscripts outside on-time threshold", () => {
  assert.equal(flightTimeDeltaLabel(5), "");
  assert.match(flightTimeDeltaLabel(12), /flight-time-delta is-late">\+12<\/sup>/);
  assert.match(flightTimeDeltaLabel(-6), /flight-time-delta is-early">-6<\/sup>/);
});

test("irregularityText returns a compact delay duration, reason, and code", () => {
  const text = irregularityText({
    irregularity_delay_duration_public: "PT1H5M",
    irregularity_delay_reason_public: "Restrictions from Air Traffic Control",
    irregularity_delay_code: "93",
    irregularity_delay_sub_code: "A",
  });

  assert.equal(text, "1h 5m · ATC restrictions · 93A");
});

test("irregularityTitle preserves the full reason for hover text", () => {
  const text = irregularityTitle({
    irregularity_delay_duration_public: "PT20M",
    irregularity_delay_reason_public: "Restrictions from Air Traffic Control",
    irregularity_delay_code: "81",
    irregularity_delay_sub_code: "A",
  });

  assert.equal(text, "Delayed 20m · Restrictions from Air Traffic Control · Code 81A");
});

test("irregularityText avoids empty separators when fields are missing", () => {
  assert.equal(irregularityText({ irregularity_delay_code: "81" }), "81");
  assert.equal(irregularityText({ departure_delay_minutes: 20 }), "20m");
  assert.equal(irregularityText({}), "");
});

test("progressPercent clamps progress values", () => {
  const departure = new Date("2026-01-01T10:00:00Z");
  const arrival = new Date("2026-01-01T12:00:00Z");

  assert.equal(progressPercent(120, departure, arrival, Date.now()), 100);
  assert.equal(progressPercent(-15, departure, arrival, Date.now()), 0);
  assert.equal(progressPercent(undefined, departure, arrival, departure.getTime() + 60 * 60 * 1000), 50);
});

test("timelineStatusHtml hides Upcoming and Done chips", () => {
  assert.equal(timelineStatusHtml("Upcoming"), "");
  assert.equal(timelineStatusHtml("Done"), "");
  assert.match(timelineStatusHtml("Delayed"), /class="timeline-status is-delayed"/);
});
