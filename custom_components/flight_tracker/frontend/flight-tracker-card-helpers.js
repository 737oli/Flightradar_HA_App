export function timelineRoute(value) {
  return String(value || "")
    .replace(/\s*(?:->|→)\s*/g, " - ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function timeDeltaLabel(deltaMinutes) {
  if (!Number.isFinite(Number(deltaMinutes)) || Number(deltaMinutes) === 0) {
    return "";
  }
  const minutes = Number(deltaMinutes);
  const tone = minutes > 0 ? "is-late" : "is-early";
  const sign = minutes > 0 ? "+" : "";
  return `<em class="timeline-time-delta ${tone}">${sign}${minutes}m</em>`;
}

export function irregularityText(attrs = {}) {
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

export function progressPercent(apiProgress, departure, arrival, now) {
  const liveProgress = Number(apiProgress);
  if (Number.isFinite(liveProgress)) {
    return clamp(liveProgress, 0, 100);
  }
  if (!departure || !arrival || arrival <= departure) {
    return 0;
  }
  return clamp(((now - departure.getTime()) / (arrival.getTime() - departure.getTime())) * 100, 0, 100);
}

export function timelineStatusClass(status) {
  return String(status || "")
    .toLowerCase()
    .includes("delayed")
    ? " is-delayed"
    : "";
}

export function timelineStatusHtml(status) {
  if (!status || ["upcoming", "done"].includes(String(status).toLowerCase())) {
    return "";
  }
  const delayed = timelineStatusClass(status);
  return `<b class="timeline-status${delayed}">${escapeHtml(status)}</b>`;
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
