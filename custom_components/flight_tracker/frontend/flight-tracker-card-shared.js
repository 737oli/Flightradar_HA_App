export const EMPTY_STATES = new Set(["unknown", "unavailable", "none", "not_flying"]);

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

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
