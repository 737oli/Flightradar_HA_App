import {
  flightTimeDeltaLabel,
  irregularityText,
  irregularityTitle,
  progressPercent,
} from "./flight-tracker-card-helpers.js";
import {
  airportDetail,
  delayTone,
  flightPrefix,
  formatTime,
  escapeHtml,
  isDelayed,
  isFlightState,
  parseDate,
  routePart,
  timelineText,
} from "./flight-tracker-card-formatters.js";

export function renderFlightCard(state, now = Date.now()) {
  if (!isFlightState(state)) {
    return `${styles()}${emptyCard()}`;
  }

  const attrs = state.attributes || {};
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
  const departureDetail = airportDetail(
    attrs.departure_parking_position,
    attrs.departure_gate,
  );
  const arrivalDetail = airportDetail(
    attrs.arrival_parking_position,
    attrs.arrival_gate,
  );
  const departureTime = scheduledDeparture || departure;
  const arrivalTime = scheduledArrival || arrival;
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
  const irregularityFullText = irregularityTitle(attrs);
  const delayClass =
    isDelayed(attrs.departure_delay_minutes) || isDelayed(attrs.arrival_delay_minutes)
      ? "is-delayed"
      : "";
  const phaseClass = timeline.phase === "arrival" ? "is-active" : "";

  return `
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
              <span class="time">
                ${escapeHtml(formatTime(departureTime))}
                ${flightTimeDeltaLabel(attrs.departure_delay_minutes)}
              </span>
            </div>
            <small>${escapeHtml(departureDetail)}</small>
          </div>

          <div class="plane-line" aria-hidden="true">
            <span></span>
            <b>&#9992;</b>
            <span></span>
          </div>

          <div class="airport destination ${delayTone(attrs.arrival_delay_minutes)}">
            <div>
              <span class="time">
                ${escapeHtml(formatTime(arrivalTime))}
                ${flightTimeDeltaLabel(attrs.arrival_delay_minutes)}
              </span>
              <strong>${escapeHtml(arrivalAirport)}</strong>
            </div>
            <small>${escapeHtml(arrivalDetail)}</small>
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
            ? `<section class="irregularity" title="${escapeHtml(irregularityFullText || irregularity)}"><b>Delay</b><span>${escapeHtml(irregularity)}</span></section>`
            : ""
        }
      </article>
    </ha-card>
  `;
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

      .airport .time {
        display: inline-flex;
        align-items: flex-start;
        gap: 3px;
        color: var(--flight-card-green);
        font-size: 30px;
        line-height: 1;
        font-weight: 700;
        white-space: nowrap;
      }

      .flight-time-delta {
        color: var(--flight-card-green);
        font-size: 12px;
        line-height: 1;
        font-weight: 800;
        transform: translateY(-0.42em);
      }

      .flight-time-delta.is-late {
        color: var(--flight-card-red);
      }

      .flight-time-delta.is-early {
        color: var(--flight-card-green);
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

      .airport.delayed .time,
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

        .airport .time {
          font-size: 22px;
        }

        .flight-time-delta {
          font-size: 10px;
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
