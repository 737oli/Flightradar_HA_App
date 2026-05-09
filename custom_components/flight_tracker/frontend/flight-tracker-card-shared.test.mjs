import test from "node:test";
import assert from "node:assert/strict";

import {
  durationLabel,
  escapeHtml,
  flightPrefix,
  parseDate,
  routePart,
} from "./flight-tracker-card-shared.js";

test("durationLabel formats hours and minutes", () => {
  assert.equal(durationLabel(65 * 60000), "1h 5m");
  assert.equal(durationLabel(120 * 60000), "2h");
  assert.equal(durationLabel(5 * 60000), "5m");
});

test("routePart reads route segments", () => {
  assert.equal(routePart("AMS->JFK", 0), "AMS");
  assert.equal(routePart("AMS -> JFK", 1), "JFK");
});

test("flightPrefix normalizes prefix", () => {
  assert.equal(flightPrefix("kl1234"), "KL1");
  assert.equal(flightPrefix(" AF56"), "");
});

test("parseDate returns undefined for invalid input", () => {
  assert.equal(parseDate(undefined), undefined);
  assert.equal(parseDate("not-a-date"), undefined);
  assert.ok(parseDate("2026-01-01T10:00:00Z") instanceof Date);
});

test("escapeHtml escapes unsafe characters", () => {
  assert.equal(escapeHtml('<tag attr="x">&\''), "&lt;tag attr=&quot;x&quot;&gt;&amp;&#039;");
});
