import { isFlightState } from "./flight-tracker-card-formatters.js";
import { renderFlightCard } from "./flight-tracker-flight-card-render.js";
import { renderTimelineCard } from "./flight-tracker-timeline-card-render.js";

const CARD_VERSION = "0.7.1";

class FlightTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (!config.entity && !config.current_entity) {
      throw new Error("Define entity or current_entity");
    }

    this._config = {
      show_next_when_idle: true,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 2;
  }

  static getStubConfig() {
    return {
      type: "custom:flight-tracker-card",
      current_entity: "sensor.ical_flight_tracker_current_flight",
      next_entity: "sensor.ical_flight_tracker_next_flight",
    };
  }

  _render() {
    if (!this.shadowRoot || !this._config || !this._hass) {
      return;
    }

    const currentEntity =
      this._config.current_entity || this._config.entity || this._config.current;
    const nextEntity = this._config.next_entity || this._config.next;
    const current = this._hass.states[currentEntity];
    const next = nextEntity ? this._hass.states[nextEntity] : undefined;
    const state =
      isFlightState(current) || !this._config.show_next_when_idle ? current : next;

    this.shadowRoot.innerHTML = renderFlightCard(state, Date.now());
  }
}

class FlightTrackerTimelineCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Define entity");
    }

    this._config = {
      title: "Where is Olivier today?",
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig() {
    return {
      type: "custom:flight-tracker-timeline-card",
      entity: "sensor.ical_flight_tracker_trip_timeline",
    };
  }

  _render() {
    if (!this.shadowRoot || !this._config || !this._hass) {
      return;
    }

    const state = this._hass.states[this._config.entity];
    this.shadowRoot.innerHTML = renderTimelineCard(this._config.title, state);
  }
}

customElements.define("flight-tracker-card", FlightTrackerCard);
customElements.define("flight-tracker-timeline-card", FlightTrackerTimelineCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "flight-tracker-card",
  name: "Flight Tracker Card",
  preview: true,
  description: "Compact flight status card for iCal Flight Tracker.",
});
window.customCards.push({
  type: "flight-tracker-timeline-card",
  name: "Flight Tracker Timeline Card",
  preview: true,
  description: "Travel day timeline card for iCal Flight Tracker.",
});

console.info(
  `%c FLIGHT-TRACKER-CARD %c ${CARD_VERSION} `,
  "color: #07100c; background: #00f58a; font-weight: 700;",
  "color: #00f58a; background: #07100c; font-weight: 700;",
);
