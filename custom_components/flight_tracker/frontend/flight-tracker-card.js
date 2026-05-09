import { FlightTrackerCard } from "./flight-tracker-flight-card.js";
import { FlightTrackerTimelineCard } from "./flight-tracker-timeline-card.js";

const CARD_VERSION = "0.3.4";

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
