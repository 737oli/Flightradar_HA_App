"""Config flow for iCal Flight Tracker."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_URL
from homeassistant.core import callback

from .const import (
    CONF_CONSUMER_HOST,
    CONF_LOOKAHEAD_DAYS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_CONSUMER_HOST,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
)


class FlightTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an iCal Flight Tracker config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = str(user_input[CONF_URL]).strip()
            api_key = str(user_input.get(CONF_API_KEY, "")).strip()
            if not _valid_url(url):
                errors[CONF_URL] = "invalid_url"
            if not api_key:
                errors[CONF_API_KEY] = "api_key_required"

            if not errors:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()

                data = _entry_data(user_input)
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ):
        """Create the options flow."""
        return FlightTrackerOptionsFlow(config_entry)


class FlightTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle iCal Flight Tracker options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not _valid_url(str(user_input[CONF_URL]).strip()):
                errors[CONF_URL] = "invalid_url"
            if not str(user_input.get(CONF_API_KEY, "")).strip():
                errors[CONF_API_KEY] = "api_key_required"

            if not errors:
                return self.async_create_entry(title="", data=_entry_data(user_input))

        data = {**self._config_entry.data, **self._config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or data),
            errors=errors,
        )


def _schema(defaults: dict[str, object] | None) -> vol.Schema:
    """Build config flow schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_URL,
                default=defaults.get(CONF_URL, ""),
            ): str,
            vol.Optional(
                CONF_NAME,
                default=defaults.get(CONF_NAME, DEFAULT_NAME),
            ): str,
            vol.Required(
                CONF_API_KEY,
                default=defaults.get(CONF_API_KEY, ""),
            ): str,
            vol.Optional(
                CONF_LOOKAHEAD_DAYS,
                default=defaults.get(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Optional(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(
                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=240)),
        }
    )


def _valid_url(url: str) -> bool:
    """Return whether the URL looks usable."""
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _entry_data(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return normalized config entry data."""
    return {
        CONF_NAME: str(user_input.get(CONF_NAME, DEFAULT_NAME)).strip()
        or DEFAULT_NAME,
        CONF_URL: str(user_input[CONF_URL]).strip(),
        CONF_API_KEY: str(user_input[CONF_API_KEY]).strip(),
        CONF_CONSUMER_HOST: DEFAULT_CONSUMER_HOST,
        CONF_LOOKAHEAD_DAYS: user_input.get(
            CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS
        ),
        CONF_UPDATE_INTERVAL: user_input.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
        ),
    }
