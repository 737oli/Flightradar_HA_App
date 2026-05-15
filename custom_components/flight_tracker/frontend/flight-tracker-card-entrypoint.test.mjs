import test from "node:test";
import assert from "node:assert/strict";

test("entrypoint registers and renders the flight tracker cards", async (t) => {
  const browser = installBrowserStubs();
  const originalConsoleInfo = console.info;
  console.info = () => {};

  t.after(() => {
    browser.restore();
    console.info = originalConsoleInfo;
  });

  const moduleUrl = new URL("./flight-tracker-card.js", import.meta.url);
  moduleUrl.searchParams.set("smoke", "entrypoint");
  await import(moduleUrl.href);

  const FlightTrackerCard = customElements.get("flight-tracker-card");
  const FlightTrackerTimelineCard = customElements.get("flight-tracker-timeline-card");

  assert.equal(typeof FlightTrackerCard, "function");
  assert.equal(typeof FlightTrackerTimelineCard, "function");
  assert.deepEqual(
    window.customCards.map((card) => card.type),
    ["flight-tracker-card", "flight-tracker-timeline-card"],
  );

  const flightCard = new FlightTrackerCard();
  flightCard.setConfig({ current_entity: "sensor.current_flight" });
  flightCard.hass = {
    states: {
      "sensor.current_flight": {
        state: "on_time",
        attributes: {
          flight_number: "KL1234",
          route: "AMS -> LHR",
          departure_airport: "AMS",
          arrival_airport: "LHR",
          scheduled_departure: "2099-01-01T10:00:00Z",
          scheduled_arrival: "2099-01-01T11:00:00Z",
          aircraft_type_code: "E195",
          live_status: "On roster",
        },
      },
    },
  };

  assert.match(flightCard.shadowRoot.innerHTML, /KL1234/);
  assert.match(flightCard.shadowRoot.innerHTML, /AMS/);
  assert.match(flightCard.shadowRoot.innerHTML, /LHR/);

  const timelineCard = new FlightTrackerTimelineCard();
  timelineCard.setConfig({
    entity: "sensor.trip_timeline",
    title: "Where is Olivier today?",
  });
  timelineCard.hass = {
    states: {
      "sensor.trip_timeline": {
        state: "Travel day",
        attributes: {
          headline: "Travel day",
          detail: "Hotel DBV, 1 flight, base return",
          segments: [
            {
              kind: "flight",
              phase: "current",
              title: "KL1978",
              route: "DBV -> AMS",
              aircraft_type: "E195",
              start: "2099-01-01T13:25:00Z",
              end: "2099-01-01T15:55:00Z",
              duration_minutes: 150,
            },
          ],
        },
      },
    },
  };

  assert.match(timelineCard.shadowRoot.innerHTML, /Where is Olivier today/);
  assert.match(timelineCard.shadowRoot.innerHTML, /KL1978/);
  assert.match(timelineCard.shadowRoot.innerHTML, /DBV - AMS/);
  assert.match(timelineCard.shadowRoot.innerHTML, /E195/);
});

function installBrowserStubs() {
  const previousGlobals = {
    HTMLElement: globalThis.HTMLElement,
    customElements: globalThis.customElements,
    window: globalThis.window,
  };
  const registry = new Map();

  globalThis.HTMLElement = class {
    attachShadow() {
      this.shadowRoot = { innerHTML: "" };
      return this.shadowRoot;
    }
  };
  globalThis.customElements = {
    define(name, constructor) {
      if (registry.has(name)) {
        throw new Error(`Custom element already registered: ${name}`);
      }
      registry.set(name, constructor);
    },
    get(name) {
      return registry.get(name);
    },
  };
  globalThis.window = { customCards: [] };

  return {
    restore() {
      restoreGlobal("HTMLElement", previousGlobals.HTMLElement);
      restoreGlobal("customElements", previousGlobals.customElements);
      restoreGlobal("window", previousGlobals.window);
    },
  };
}

function restoreGlobal(name, value) {
  if (value === undefined) {
    delete globalThis[name];
    return;
  }
  globalThis[name] = value;
}
