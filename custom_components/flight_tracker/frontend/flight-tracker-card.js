const CARD_VERSION = "0.3.1";
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
    const departure =
      parseDate(attrs.actual_departure) ||
      parseDate(attrs.estimated_departure) ||
      scheduledDeparture;
    const arrival =
      parseDate(attrs.actual_arrival) ||
      parseDate(attrs.estimated_arrival) ||
      scheduledArrival;
    const progress = progressPercent(attrs.progress_percent, departure, arrival, now);
    const timeline = timelineText(departure, arrival, now);
    const departureStatus = airportStatus(
      attrs.departure_terminal,
      attrs.departure_gate,
      statusText(attrs.departure_delay_minutes),
    );
    const arrivalStatus = airportStatus(
      attrs.arrival_terminal,
      attrs.arrival_gate,
      statusText(attrs.arrival_delay_minutes),
    );
    const airline = attrs.airline_code || flightPrefix(attrs.flight_number) || "";
    const flightNumber = attrs.flight_number || state.state || "Flight";
    const departureAirport = attrs.departure_airport || routePart(attrs.route, 0) || "---";
    const arrivalAirport = attrs.arrival_airport || routePart(attrs.route, 1) || "---";
    const aircraft = attrs.aircraft_type_code || attrs.live_aircraft_type || attrs.aircraft_type || "";
    const registration = attrs.aircraft_registration || "";
    const label = attrs.is_deadhead ? "Deadhead" : aircraft || airline || "Flight";
    const liveStatus = attrs.live_status || (attrs.is_deadhead ? "Positioning" : "On roster");
    const rightLabel = [registration, liveStatus].filter(Boolean).join(" · ");
    const irregularity = irregularityText(attrs);
    const delayClass =
      isDelayed(attrs.departure_delay_minutes) || isDelayed(attrs.arrival_delay_minutes)
        ? "is-delayed"
        : "";
    const phaseClass = timeline.phase === "arrival" ? "is-active" : "";

    this.shadowRoot.innerHTML = `
      ${styles()}
      <ha-card>
        <article class="flight-card ${phaseClass} ${delayClass}" aria-label="${escapeHtml(flightNumber)}">
          <div class="glow"></div>
          <header class="meta">
            <span class="airline">
              <span class="airline-dot">${escapeHtml(flightNumber)}</span>
              <span>${escapeHtml(label)}</span>
            </span>
            <span class="record">${escapeHtml(rightLabel)}</span>
          </header>

          <section class="route">
            <div class="airport origin ${delayTone(attrs.departure_delay_minutes)}">
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

            <div class="airport destination ${delayTone(attrs.arrival_delay_minutes)}">
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

          ${
            irregularity
              ? `<section class="irregularity"><b>Delay</b><span>${escapeHtml(irregularity)}</span></section>`
              : ""
          }
        </article>
      </ha-card>
    `;
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
    if (!state || !state.attributes) {
      this.shadowRoot.innerHTML = `${timelineStyles()}${timelineEmptyCard()}`;
      return;
    }

    const attrs = state.attributes || {};
    const segments = Array.isArray(attrs.segments) ? attrs.segments : [];
    if (!segments.length) {
      this.shadowRoot.innerHTML = `${timelineStyles()}${timelineEmptyCard(attrs)}`;
      return;
    }

    this.shadowRoot.innerHTML = `
      ${timelineStyles()}
      <ha-card>
        <article class="timeline-card" aria-label="${escapeHtml(attrs.headline || state.state)}">
          <header class="timeline-header">
            <span>${escapeHtml(this._config.title)}</span>
            <strong>${escapeHtml(attrs.headline || state.state)}</strong>
            <small>${escapeHtml(attrs.detail || "")}</small>
          </header>
          <ol class="timeline-list">
            ${segments.map((segment) => timelineItem(segment)).join("")}
          </ol>
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
        --flight-card-red: #ff4d5f;
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

      .flight-card.is-delayed {
        border-color: rgba(255, 77, 95, 0.28);
        background:
          radial-gradient(circle at 82% 12%, rgba(255, 77, 95, 0.24), transparent 30%),
          radial-gradient(circle at 64% 106%, rgba(0, 245, 138, 0.22), transparent 42%),
          linear-gradient(156deg, #060506 0%, #1b1018 54%, #080707 100%);
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
      .route {
        position: relative;
        z-index: 1;
      }

      .meta {
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
        min-width: 54px;
        height: 20px;
        padding: 0 8px;
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

      .airport.delayed span,
      .airport.delayed small {
        color: var(--flight-card-red);
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

      .irregularity {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 9px;
        margin-top: 14px;
        overflow: hidden;
        color: #ffd8dd;
        font-size: 13px;
        font-weight: 700;
      }

      .irregularity b {
        flex: 0 0 auto;
        padding: 4px 8px;
        border-radius: 999px;
        color: #1d070a;
        background: var(--flight-card-red);
        font-size: 11px;
        line-height: 1;
        text-transform: uppercase;
      }

      .irregularity span {
        overflow: hidden;
        min-width: 0;
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

function timelineStyles() {
  return `
    <style>
      :host {
        display: block;
        --flight-card-green: #00f58a;
        --flight-card-red: #ff4d5f;
        --flight-card-muted: rgba(255, 255, 255, 0.64);
        --flight-card-border: rgba(255, 255, 255, 0.12);
      }

      ha-card {
        background: transparent;
        box-shadow: none;
        border: 0;
      }

      .timeline-card {
        overflow: hidden;
        padding: 22px 24px 18px;
        border: 1px solid var(--flight-card-border);
        border-radius: 28px;
        color: #f8fbff;
        background:
          radial-gradient(circle at 88% 8%, rgba(104, 82, 255, 0.30), transparent 34%),
          radial-gradient(circle at 36% 100%, rgba(0, 245, 138, 0.20), transparent 42%),
          linear-gradient(155deg, #050506 0%, #15111d 56%, #070808 100%);
        box-sizing: border-box;
        font-family: var(--primary-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
      }

      .timeline-header {
        display: grid;
        gap: 5px;
        margin-bottom: 18px;
      }

      .timeline-header span {
        color: var(--flight-card-green);
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
      }

      .timeline-header strong {
        color: #ffffff;
        font-size: 26px;
        line-height: 1.1;
        font-weight: 800;
      }

      .timeline-header small {
        color: var(--flight-card-muted);
        font-size: 14px;
      }

      .timeline-list {
        display: grid;
        gap: 0;
        margin: 0;
        padding: 0;
        list-style: none;
      }

      .timeline-item {
        display: grid;
        grid-template-columns: 72px 28px minmax(0, 1fr);
        gap: 12px;
        min-height: 58px;
        color: var(--flight-card-muted);
      }

      .timeline-item.is-current {
        color: #ffffff;
      }

      .timeline-time {
        padding-top: 2px;
        color: rgba(255, 255, 255, 0.70);
        font-size: 13px;
        font-weight: 700;
        line-height: 1.25;
        text-align: right;
      }

      .timeline-rail {
        position: relative;
        display: grid;
        justify-items: center;
      }

      .timeline-rail::before {
        content: "";
        position: absolute;
        top: 24px;
        bottom: -4px;
        width: 2px;
        background: rgba(255, 255, 255, 0.14);
      }

      .timeline-item:last-child .timeline-rail::before {
        display: none;
      }

      .timeline-dot {
        position: relative;
        z-index: 1;
        display: grid;
        place-items: center;
        width: 24px;
        height: 24px;
        border-radius: 999px;
        color: #07100c;
        background: rgba(255, 255, 255, 0.26);
        font-size: 10px;
        font-weight: 900;
      }

      .timeline-item.is-current .timeline-dot,
      .timeline-item.is-next .timeline-dot {
        background: var(--flight-card-green);
        box-shadow: 0 0 18px rgba(0, 245, 138, 0.42);
      }

      .timeline-item.kind-flight.is-current .timeline-dot {
        background: var(--flight-card-green);
      }

      .timeline-item.kind-base_return .timeline-dot {
        background: #ffffff;
      }

      .timeline-body {
        min-width: 0;
        padding-bottom: 18px;
      }

      .timeline-body strong {
        display: block;
        overflow: hidden;
        color: #ffffff;
        font-size: 16px;
        line-height: 1.2;
        font-weight: 800;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .timeline-body span {
        display: block;
        overflow: hidden;
        margin-top: 4px;
        color: var(--flight-card-muted);
        font-size: 13px;
        line-height: 1.25;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .timeline-status {
        display: inline-flex;
        margin-top: 8px;
        padding: 4px 8px;
        border-radius: 999px;
        color: #07100c;
        background: rgba(255, 255, 255, 0.72);
        font-size: 11px;
        font-weight: 800;
      }

      .timeline-item.is-current .timeline-status,
      .timeline-item.is-next .timeline-status {
        background: var(--flight-card-green);
      }

      .timeline-item.is-past {
        opacity: 0.62;
      }

      .timeline-empty {
        min-height: 132px;
        display: grid;
        align-content: center;
        gap: 8px;
      }

      .timeline-empty strong {
        color: #ffffff;
        font-size: 24px;
      }

      .timeline-empty span {
        color: var(--flight-card-muted);
      }

      @media (max-width: 520px) {
        .timeline-card {
          padding: 18px 16px 14px;
          border-radius: 24px;
        }

        .timeline-header strong {
          font-size: 22px;
        }

        .timeline-item {
          grid-template-columns: 58px 24px minmax(0, 1fr);
          gap: 9px;
        }

        .timeline-time {
          font-size: 12px;
        }
      }
    </style>
  `;
}

function timelineEmptyCard(attrs = {}) {
  return `
    <ha-card>
      <article class="timeline-card timeline-empty">
        <strong>${escapeHtml(attrs.headline || "No travel day")}</strong>
        <span>${escapeHtml(attrs.detail || "The next roster day will appear here once the calendar has one.")}</span>
      </article>
    </ha-card>
  `;
}

function timelineItem(segment) {
  const phase = timelinePhaseClass(segment.phase);
  const kind = `kind-${String(segment.kind || "event").replace(/[^a-z0-9_-]/gi, "_")}`;
  return `
    <li class="timeline-item ${phase} ${kind}">
      <div class="timeline-time">${segmentTime(segment)}</div>
      <div class="timeline-rail">
        <span class="timeline-dot">${escapeHtml(segmentIcon(segment.kind))}</span>
      </div>
      <div class="timeline-body">
        <strong>${escapeHtml(segment.title || "Roster item")}</strong>
        <span>${escapeHtml(segment.detail || segment.route || "")}</span>
        <b class="timeline-status">${escapeHtml(segment.status || segmentMeta(segment))}</b>
      </div>
    </li>
  `;
}

function timelinePhaseClass(phase) {
  if (phase === "current") {
    return "is-current";
  }
  if (phase === "past") {
    return "is-past";
  }
  return "is-next";
}

function segmentTime(segment) {
  const start = parseDate(segment.start);
  const end = parseDate(segment.end);
  return `${formatTime(start)}<br>${formatTime(end)}`;
}

function segmentIcon(kind) {
  const icons = {
    flight: "FLT",
    layover: "LAY",
    hotel: "HTL",
    transfer: "CAR",
    base_return: "AMS",
    training: "TRN",
    off: "OFF",
  };
  return icons[kind] || "DAY";
}

function segmentMeta(segment) {
  if (segment.duration_minutes) {
    return durationLabel(segment.duration_minutes * 60000);
  }
  return "";
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
  if (!Number.isFinite(value) || Math.abs(value) <= 5) {
    return "On Time";
  }
  return value > 0 ? `${value}m Late` : `${Math.abs(value)}m Early`;
}

function delayTone(delay) {
  return isDelayed(delay) ? "delayed" : "on-time";
}

function isDelayed(delay) {
  const value = Number(delay);
  return Number.isFinite(value) && value > 5;
}

function airportStatus(terminal, gate, status) {
  const parts = [];
  if (terminal) {
    parts.push(String(terminal).startsWith("T") ? terminal : `T${terminal}`);
  }
  if (gate) {
    parts.push(`Gate ${gate}`);
  }
  parts.push(status);
  return parts.join(" · ");
}

function irregularityText(attrs) {
  const code = firstValue(
    attrs.irregularity_delay_code,
    attrs.irregularity_delay_reason_code_public,
    attrs.irregularity_delay_sub_code,
  );
  const duration =
    formatDelayDuration(
      firstValue(
        attrs.irregularity_delay_duration_public,
        attrs.irregularity_delay_duration,
      ),
    ) || delayDurationFromMinutes(attrs.departure_delay_minutes, attrs.arrival_delay_minutes);
  const reason = firstValue(
    attrs.irregularity_delay_reason_public,
    attrs.irregularity_public_disruption_reason,
    attrs.irregularity_delay_reason,
  );

  if (!code && !duration && !reason) {
    return "";
  }

  const parts = [duration ? `Delayed ${duration}` : "Delayed"];
  if (reason) {
    parts.push(reason);
  }
  if (code) {
    parts.push(`Code ${code}`);
  }
  return parts.join(" · ");
}

function firstValue(...values) {
  return values.find((value) => value !== undefined && value !== null && String(value).trim());
}

function formatDelayDuration(value) {
  if (!value) {
    return "";
  }
  const text = String(value).trim();
  const isoMatch = text.match(/^PT(?:(\d+)H)?(?:(\d+)M)?$/i);
  if (isoMatch) {
    return minutesLabel(Number(isoMatch[1] || 0) * 60 + Number(isoMatch[2] || 0));
  }
  const clockMatch = text.match(/^(\d{1,2}):(\d{2})$/);
  if (clockMatch) {
    return minutesLabel(Number(clockMatch[1]) * 60 + Number(clockMatch[2]));
  }
  if (/^\d+$/.test(text)) {
    return minutesLabel(Number(text));
  }
  return text;
}

function delayDurationFromMinutes(...delays) {
  const minutes = Math.max(
    0,
    ...delays
      .map((delay) => Number(delay))
      .filter((delay) => Number.isFinite(delay) && delay > 5),
  );
  return minutes ? minutesLabel(minutes) : "";
}

function minutesLabel(totalMinutes) {
  const minutes = Math.max(0, Math.round(totalMinutes));
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (hours && remainder) {
    return `${hours}h ${remainder}m`;
  }
  if (hours) {
    return `${hours}h`;
  }
  return `${remainder}m`;
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
