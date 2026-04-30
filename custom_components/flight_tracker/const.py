"""Constants for iCal Flight Tracker."""

from __future__ import annotations

DOMAIN = "flight_tracker"

DEFAULT_NAME = "iCal Flight Tracker"
DEFAULT_LOOKAHEAD_DAYS = 45
DEFAULT_UPDATE_INTERVAL_MINUTES = 15

CONF_LOOKAHEAD_DAYS = "lookahead_days"
CONF_UPDATE_INTERVAL = "update_interval_minutes"

ATTR_FLIGHTS = "flights"
ATTR_LAST_REFRESH = "last_refresh"

