const CARD_VERSION = "0.1.0";
const EMPTY_STATES = new Set(["unknown", "unavailable", "none", "not_flying"]);

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

    if (!isFlightState(state)) {
      this.shadowRoot.innerHTML = `${styles()}${emptyCard()}`;
      return;
    }

    const attrs = state.attributes || {};
    const now = Date.now();
    const scheduledDeparture = parseDate(attrs.scheduled_departure);
    const scheduledArrival = parseDate(attrs.scheduled_arrival);
    const departure = parseDate(attrs.estimated_departure) || scheduledDeparture;
    const arrival = parseDate(attrs.estimated_arrival) || scheduledArrival;
    const progress = progressPercent(attrs.progress_percent, scheduledDeparture, arrival, now);
    const timeline = timelineText(scheduledDeparture, arrival, now);
    const departureStatus = statusText(attrs.departure_delay_minutes);
    const arrivalStatus = statusText(attrs.arrival_delay_minutes);
    const airline = attrs.airline_code || flightPrefix(attrs.flight_number) || "";
    const flightNumber = attrs.flight_number || state.state || "Flight";
    const departureAirport = attrs.departure_airport || routePart(attrs.route, 0) || "---";
    const arrivalAirport = attrs.arrival_airport || routePart(attrs.route, 1) || "---";
    const aircraft = attrs.aircraft_type || "";
    const label = attrs.is_deadhead ? "Deadhead" : aircraft || airline || "Flight";
    const rightLabel = attrs.live_status || (attrs.is_deadhead ? "Positioning" : "On roster");
    const phaseClass = timeline.phase === "arrival" ? "is-active" : "";

    this.shadowRoot.innerHTML = `
      ${styles()}
      <ha-card>
        <article class="flight-card ${phaseClass}" aria-label="${escapeHtml(flightNumber)}">
          <div class="glow"></div>
          <header class="meta">
            <span class="airline">
              <span class="airline-dot">${escapeHtml(airline || "FT")}</span>
              <span>${escapeHtml(label)}</span>
            </span>
            <span class="record">${escapeHtml(rightLabel)}</span>
          </header>

          <section class="route">
            <div class="airport origin">
              <div>
                <strong>${escapeHtml(departureAirport)}</strong>
                <span>${formatTime(departure)}</span>
              </div>
              <small>${escapeHtml(departureStatus)}</small>
            </div>

            <div class="plane-line" aria-hidden="true">
              <span></span>
              <b>&#9992;</b>
              <span></span>
            </div>

            <div class="airport destination">
              <div>
                <span>${formatTime(arrival)}</span>
                <strong>${escapeHtml(arrivalAirport)}</strong>
              </div>
              <small>${escapeHtml(arrivalStatus)}</small>
            </div>
          </section>

          <section class="progress">
            <div class="track">
              <i style="width: ${progress}%"></i>
            </div>
            <div class="countdown">
              <strong>${escapeHtml(timeline.value)}</strong>
              <span>${escapeHtml(timeline.label)}</span>
            </div>
          </section>

          <footer class="footer">
            <span>${escapeHtml(flightNumber)}</span>
            <span>${escapeHtml(attrs.route || `${departureAirport} -> ${arrivalAirport}`)}</span>
          </footer>
        </article>
      </ha-card>
    `;
  }
}

function styles() {
  return `
    <style>
      :host {
        display: block;
        --flight-card-green: #00f58a;
        --flight-card-muted: rgba(255, 255, 255, 0.62);
        --flight-card-border: rgba(255, 255, 255, 0.12);
      }

      ha-card {
        background: transparent;
        box-shadow: none;
        border: 0;
      }

      .flight-card {
        position: relative;
        overflow: hidden;
        min-height: 184px;
        padding: 22px 26px 18px;
        border: 1px solid var(--flight-card-border);
        border-radius: 32px;
        color: #f8fbff;
        background:
          radial-gradient(circle at 78% 0%, rgba(104, 82, 255, 0.36), transparent 34%),
          radial-gradient(circle at 68% 118%, rgba(0, 245, 138, 0.30), transparent 40%),
          linear-gradient(155deg, #050506 0%, #16111f 52%, #070808 100%);
        box-sizing: border-box;
        font-family: var(--primary-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
      }

      .flight-card.is-active {
        background:
          radial-gradient(circle at 84% 10%, rgba(121, 93, 255, 0.38), transparent 32%),
          radial-gradient(circle at 64% 96%, rgba(0, 245, 138, 0.34), transparent 45%),
          linear-gradient(160deg, #08070b 0%, #1b1323 58%, #07090a 100%);
      }

      .glow {
        position: absolute;
        inset: auto -20% -46% 16%;
        height: 92px;
        background: rgba(0, 245, 138, 0.18);
        filter: blur(36px);
        pointer-events: none;
      }

      .meta,
      .route,
      .footer {
        position: relative;
        z-index: 1;
      }

      .meta,
      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
      }

      .meta {
        color: var(--flight-card-muted);
        font-size: 15px;
        line-height: 1;
      }

      .airline {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        min-width: 0;
      }

      .airline-dot {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 30px;
        height: 20px;
        padding: 0 6px;
        border-radius: 999px;
        color: #07100c;
        background: var(--flight-card-green);
        font-size: 11px;
        font-weight: 800;
        box-sizing: border-box;
      }

      .record {
        overflow: hidden;
        max-width: 44%;
        text-align: right;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .route {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 96px minmax(0, 1fr);
        align-items: center;
        gap: 14px;
        margin-top: 24px;
      }

      .airport {
        min-width: 0;
      }

      .airport.destination {
        text-align: right;
      }

      .airport > div {
        display: flex;
        align-items: baseline;
        gap: 8px;
        min-width: 0;
      }

      .destination > div {
        justify-content: flex-end;
      }

      .airport strong {
        color: #ffffff;
        font-size: 32px;
        line-height: 1;
        font-weight: 800;
      }

      .airport span {
        color: var(--flight-card-green);
        font-size: 30px;
        line-height: 1;
        font-weight: 700;
        white-space: nowrap;
      }

      .airport small {
        display: block;
        margin-top: 8px;
        overflow: hidden;
        color: var(--flight-card-green);
        font-size: 17px;
        font-weight: 650;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .plane-line {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        align-items: center;
        gap: 8px;
        color: rgba(255, 255, 255, 0.42);
      }

      .plane-line span {
        border-top: 5px dotted rgba(255, 255, 255, 0.24);
      }

      .plane-line b {
        color: rgba(255, 255, 255, 0.44);
        font-size: 25px;
        line-height: 1;
      }

      .progress {
        position: relative;
        z-index: 1;
        margin-top: 24px;
      }

      .track {
        overflow: hidden;
        height: 5px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.16);
      }

      .track i {
        display: block;
        height: 100%;
        min-width: 10px;
        max-width: 100%;
        border-radius: inherit;
        background: var(--flight-card-green);
        box-shadow: 0 0 16px rgba(0, 245, 138, 0.62);
      }

      .countdown {
        margin-top: 13px;
        text-align: center;
      }

      .countdown strong {
        display: block;
        color: var(--flight-card-green);
        font-size: 30px;
        line-height: 1;
        font-weight: 800;
      }

      .countdown span {
        display: block;
        margin-top: 6px;
        color: rgba(255, 255, 255, 0.82);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
      }

      .footer {
        margin-top: 13px;
        color: rgba(255, 255, 255, 0.58);
        font-size: 13px;
      }

      .footer span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .empty {
        min-height: 132px;
        display: grid;
        align-content: center;
        gap: 8px;
      }

      .empty strong {
        color: #ffffff;
        font-size: 24px;
      }

      .empty span {
        color: var(--flight-card-muted);
      }

      @media (max-width: 520px) {
        .flight-card {
          min-height: 172px;
          padding: 18px 18px 16px;
          border-radius: 26px;
        }

        .route {
          grid-template-columns: minmax(0, 1fr) 48px minmax(0, 1fr);
          gap: 8px;
          margin-top: 22px;
        }

        .airport strong {
          font-size: 27px;
        }

        .airport span {
          font-size: 22px;
        }

        .airport small {
          font-size: 15px;
        }

        .plane-line span {
          border-top-width: 4px;
        }

        .plane-line b {
          font-size: 21px;
        }

        .countdown strong {
          font-size: 27px;
        }
      }
    </style>
  `;
}

function emptyCard() {
  return `
    <ha-card>
      <article class="flight-card empty">
        <strong>No flight on the board</strong>
        <span>The next roster flight will appear here once the calendar has one.</span>
      </article>
    </ha-card>
  `;
}

function isFlightState(state) {
  if (!state || EMPTY_STATES.has(String(state.state).toLowerCase())) {
    return false;
  }
  return Boolean(state.attributes && state.attributes.flight_number);
}

function parseDate(value) {
  if (!value) {
    return undefined;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

function formatTime(date) {
  if (!date) {
    return "--:--";
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  })
    .format(date)
    .replace(/\s/g, "");
}

function statusText(delay) {
  const value = Number(delay);
  if (!Number.isFinite(value) || Math.abs(value) < 3) {
    return "On Time";
  }
  return value > 0 ? `${value}m Late` : `${Math.abs(value)}m Early`;
}

function progressPercent(apiProgress, departure, arrival, now) {
  const liveProgress = Number(apiProgress);
  if (Number.isFinite(liveProgress)) {
    return clamp(liveProgress, 0, 100);
  }
  if (!departure || !arrival || arrival <= departure) {
    return 0;
  }
  return clamp(((now - departure.getTime()) / (arrival.getTime() - departure.getTime())) * 100, 0, 100);
}

function timelineText(departure, arrival, now) {
  if (departure && now < departure.getTime()) {
    return {
      phase: "departure",
      value: durationLabel(departure.getTime() - now),
      label: "Until Departure",
    };
  }
  if (arrival && now <= arrival.getTime()) {
    return {
      phase: "arrival",
      value: durationLabel(arrival.getTime() - now),
      label: "Until Arrival",
    };
  }
  return {
    phase: "arrived",
    value: "Arrived",
    label: "Flight Complete",
  };
}

function durationLabel(milliseconds) {
  const totalMinutes = Math.max(0, Math.round(milliseconds / 60000));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours && minutes) {
    return `${hours}h ${minutes}m`;
  }
  if (hours) {
    return `${hours}h`;
  }
  return `${minutes}m`;
}

function routePart(route, index) {
  if (!route) {
    return undefined;
  }
  const parts = String(route).split("->").map((part) => part.trim());
  return parts[index];
}

function flightPrefix(flightNumber) {
  const match = String(flightNumber || "").match(/^([A-Z0-9]{2,3})/i);
  return match ? match[1].toUpperCase() : "";
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

customElements.define("flight-tracker-card", FlightTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "flight-tracker-card",
  name: "Flight Tracker Card",
  preview: true,
  description: "Compact flight status card for iCal Flight Tracker.",
});

console.info(
  `%c FLIGHT-TRACKER-CARD %c ${CARD_VERSION} `,
  "color: #07100c; background: #00f58a; font-weight: 700;",
  "color: #00f58a; background: #07100c; font-weight: 700;",
);
