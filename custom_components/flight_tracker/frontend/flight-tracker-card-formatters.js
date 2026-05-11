const EMPTY_STATES = new Set(["unknown", "unavailable", "none", "not_flying"]);

export function isFlightState(state) {
  if (!state || EMPTY_STATES.has(String(state.state).toLowerCase())) {
    return false;
  }
  return Boolean(state.attributes && state.attributes.flight_number);
}

export function parseDate(value) {
  if (!value) {
    return undefined;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export function formatTime(date) {
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

export function statusText(delay) {
  const value = Number(delay);
  if (!Number.isFinite(value) || Math.abs(value) <= 5) {
    return "On Time";
  }
  return value > 0 ? `${value}m Late` : `${Math.abs(value)}m Early`;
}

export function delayTone(delay) {
  return isDelayed(delay) ? "delayed" : "on-time";
}

export function isDelayed(delay) {
  const value = Number(delay);
  return Number.isFinite(value) && value > 5;
}

export function airportStatus(terminal, gate, status) {
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

export function timelineText(departure, arrival, now) {
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

export function durationLabel(milliseconds) {
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

export function routePart(route, index) {
  if (!route) {
    return undefined;
  }
  const parts = String(route).split("->").map((part) => part.trim());
  return parts[index];
}

export function flightPrefix(flightNumber) {
  const match = String(flightNumber || "").match(/^([A-Z0-9]{2,3})/i);
  return match ? match[1].toUpperCase() : "";
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
