import {
  timeDeltaLabel as timeDeltaLabelHelper,
  timelineRoute as timelineRouteHelper,
  timelineStatusClass as timelineStatusClassHelper,
  timelineStatusHtml as timelineStatusHtmlHelper,
} from "./flight-tracker-card-helpers.js";
import {
  durationLabel,
  escapeHtml,
  formatTime,
  parseDate,
} from "./flight-tracker-card-shared.js";

export class FlightTrackerTimelineCard extends HTMLElement {
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
        padding: 24px 26px 20px;
        border: 1px solid var(--flight-card-border);
        border-radius: 30px;
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
        margin-bottom: 22px;
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
        grid-template-columns: 76px 34px minmax(0, 1fr);
        gap: 13px;
        min-height: 66px;
        color: var(--flight-card-muted);
      }

      .timeline-item.is-current {
        color: #ffffff;
      }

      .timeline-time {
        padding-top: 3px;
        color: rgba(255, 255, 255, 0.70);
        font-size: 14px;
        font-weight: 700;
        line-height: 1.25;
        text-align: right;
      }

      .timeline-time-row {
        display: block;
        min-height: 18px;
      }

      .timeline-time-row b {
        font-weight: 800;
      }

      .timeline-time-delta {
        display: block;
        color: rgba(255, 255, 255, 0.48);
        font-size: 10px;
        font-style: normal;
        font-weight: 800;
        line-height: 1.2;
      }

      .timeline-time-delta.is-late {
        color: var(--flight-card-red);
      }

      .timeline-time-delta.is-early {
        color: var(--flight-card-green);
      }

      .timeline-rail {
        position: relative;
        display: grid;
        justify-items: center;
      }

      .timeline-rail::before {
        content: "";
        position: absolute;
        top: 30px;
        bottom: -4px;
        width: 2px;
        background: linear-gradient(
          180deg,
          rgba(255, 255, 255, 0.20),
          rgba(255, 255, 255, 0.08)
        );
      }

      .timeline-item:last-child .timeline-rail::before {
        display: none;
      }

      .timeline-dot {
        position: relative;
        z-index: 1;
        display: grid;
        place-items: center;
        width: 30px;
        height: 30px;
        border-radius: 999px;
        color: #07100c;
        background: rgba(255, 255, 255, 0.26);
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 0;
      }

      .timeline-item.is-current .timeline-dot {
        background: var(--flight-card-green);
        box-shadow: 0 0 18px rgba(0, 245, 138, 0.42);
      }

      .timeline-item.kind-flight.is-current .timeline-dot {
        background: var(--flight-card-green);
      }

      .timeline-item.kind-base_return .timeline-dot {
        background: #ffffff;
      }

      .timeline-item.kind-ground_time.is-current .timeline-dot {
        background: rgba(0, 245, 138, 0.88);
      }

      .timeline-body {
        min-width: 0;
        padding-bottom: 20px;
      }

      .timeline-heading {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
      }

      .timeline-title {
        display: inline-block;
        overflow: hidden;
        color: #ffffff;
        font-size: 18px;
        line-height: 1.2;
        font-weight: 800;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .timeline-aircraft {
        flex: 0 0 auto;
        padding: 3px 7px;
        border-radius: 999px;
        color: rgba(255, 255, 255, 0.76);
        background: rgba(255, 255, 255, 0.10);
        font-size: 11px;
        font-style: normal;
        font-weight: 900;
        line-height: 1;
      }

      .timeline-body span {
        display: block;
        overflow: hidden;
        margin-top: 4px;
        color: var(--flight-card-muted);
        font-size: 14px;
        line-height: 1.25;
        text-overflow: ellipsis;
        white-space: normal;
      }

      .timeline-status {
        display: inline-flex;
        margin-top: 10px;
        padding: 5px 10px;
        border-radius: 999px;
        color: #07100c;
        background: rgba(255, 255, 255, 0.72);
        font-size: 12px;
        font-weight: 800;
      }

      .timeline-status.is-hidden {
        display: none;
      }

      .timeline-item.is-current .timeline-status {
        background: var(--flight-card-green);
      }

      .timeline-item .timeline-status.is-delayed {
        color: #ffffff;
        background: var(--flight-card-red);
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
          grid-template-columns: 58px 28px minmax(0, 1fr);
          gap: 9px;
        }

        .timeline-time {
          font-size: 12px;
        }

        .timeline-dot {
          width: 26px;
          height: 26px;
          font-size: 9px;
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
  const status = timelineStatusClass(segment.status || segmentMeta(segment));
  return `
    <li class="timeline-item ${phase} ${kind} ${status}">
      <div class="timeline-time">${segmentTime(segment)}</div>
      <div class="timeline-rail">
        <span class="timeline-dot">${escapeHtml(segmentIcon(segment.kind))}</span>
      </div>
      <div class="timeline-body">
        ${timelineHeading(segment)}
        ${timelineDetail(segment)}
        ${timelineStatus(segment)}
      </div>
    </li>
  `;
}

function timelineHeading(segment) {
  const title = escapeHtml(segment.title || "Roster item");
  const aircraft =
    segment.kind === "flight" && segment.aircraft_type
      ? `<em class="timeline-aircraft">${escapeHtml(segment.aircraft_type)}</em>`
      : "";
  return `<div class="timeline-heading"><strong class="timeline-title">${title}</strong>${aircraft}</div>`;
}

function segmentDetail(segment) {
  if (segment.kind === "flight") {
    return timelineRoute(segment.route || segment.detail || "");
  }
  return segment.detail || segment.route || "";
}

function timelineDetail(segment) {
  const detail = segmentDetail(segment);
  return detail ? `<span>${escapeHtml(detail)}</span>` : "";
}

function timelineRoute(value) {
  return timelineRouteHelper(value);
}

function timelineStatus(segment) {
  const status = segment.status || segmentMeta(segment);
  return timelineStatusHtmlHelper(status);
}

function timelineStatusClass(status) {
  return timelineStatusClassHelper(status);
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
  return `${timeRow(start, segment.departure_time_delta_minutes)}${timeRow(
    end,
    segment.arrival_time_delta_minutes,
  )}`;
}

function timeRow(date, deltaMinutes) {
  const delta = timeDeltaLabel(deltaMinutes);
  return `<span class="timeline-time-row"><b>${formatTime(date)}</b>${delta}</span>`;
}

function timeDeltaLabel(deltaMinutes) {
  return timeDeltaLabelHelper(deltaMinutes);
}

function segmentIcon(kind) {
  const icons = {
    flight: "FLT",
    layover: "LAY",
    ground_time: "GND",
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
