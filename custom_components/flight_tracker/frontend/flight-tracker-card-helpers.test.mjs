import test from "node:test";
import assert from "node:assert/strict";

import {
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

test("irregularityText includes delay duration, reason, and code", () => {
  const text = irregularityText({
    irregularity_delay_duration_public: "PT1H5M",
    irregularity_delay_reason_public: "Weather",
    irregularity_delay_code: "93",
  });

  assert.equal(text, "Delayed 1h 5m · Weather · Code 93");
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
