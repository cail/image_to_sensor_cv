"""Config flow for Image to Sensor CV integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_IMAGE_SOURCE,
    CONF_IMAGE_PATH,
    CONF_CAMERA_ENTITY,
    CONF_CROP_CONFIG,
    CONF_CROP_X,
    CONF_CROP_Y,
    CONF_CROP_WIDTH,
    CONF_CROP_HEIGHT,
    CONF_PROCESSORS,
    CONF_MIN_ANGLE_HOURS,
    CONF_MAX_ANGLE_HOURS,
    CONF_MIN_VALUE,
    CONF_MAX_VALUE,
    CONF_UNITS,
    SOURCE_FILE,
    SOURCE_CAMERA,
    PROCESSOR_ANALOG_GAUGE,
    DEFAULT_CROP_X,
    DEFAULT_CROP_Y,
    DEFAULT_CROP_WIDTH,
    DEFAULT_CROP_HEIGHT,
    DEFAULT_MIN_ANGLE_HOURS,
    DEFAULT_MAX_ANGLE_HOURS,
    DEFAULT_MIN_VALUE,
    DEFAULT_MAX_VALUE,
    DEFAULT_UNITS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Required(CONF_IMAGE_SOURCE): selector.SelectSelector(
            selector.SelectSelectorConfig(options=[
                {"value": SOURCE_FILE, "label": "Local Image File"},
                {"value": SOURCE_CAMERA, "label": "Home Assistant Camera"},
            ])
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # TODO: Add validation for image path or camera entity
    return {"title": data["name"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Image to Sensor CV."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.data.update(user_input)
            return await self.async_step_image_config()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_image_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure image source."""
        if user_input is None:
            if self.data[CONF_IMAGE_SOURCE] == SOURCE_FILE:
                schema = vol.Schema({
                    vol.Required(CONF_IMAGE_PATH): str,
                })
            else:
                schema = vol.Schema({
                    vol.Required(CONF_CAMERA_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="camera")
                    ),
                })
            
            return self.async_show_form(step_id="image_config", data_schema=schema)

        self.data.update(user_input)
        return await self.async_step_crop_config()

    async def async_step_crop_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure image cropping."""
        if user_input is None:
            schema = vol.Schema({
                vol.Optional(CONF_CROP_X, default=DEFAULT_CROP_X): int,
                vol.Optional(CONF_CROP_Y, default=DEFAULT_CROP_Y): int,
                vol.Optional(CONF_CROP_WIDTH, default=DEFAULT_CROP_WIDTH): int,
                vol.Optional(CONF_CROP_HEIGHT, default=DEFAULT_CROP_HEIGHT): int,
            })
            
            return self.async_show_form(step_id="crop_config", data_schema=schema)

        self.data[CONF_CROP_CONFIG] = user_input
        return await self.async_step_processor_config()

    async def async_step_processor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure processors."""
        if user_input is None:
            schema = vol.Schema({
                vol.Optional(CONF_MIN_ANGLE_HOURS, default=DEFAULT_MIN_ANGLE_HOURS): vol.All(vol.Coerce(float), vol.Range(min=0, max=12)),
                vol.Optional(CONF_MAX_ANGLE_HOURS, default=DEFAULT_MAX_ANGLE_HOURS): vol.All(vol.Coerce(float), vol.Range(min=0, max=12)),
                vol.Optional(CONF_MIN_VALUE, default=DEFAULT_MIN_VALUE): vol.Coerce(float),
                vol.Optional(CONF_MAX_VALUE, default=DEFAULT_MAX_VALUE): vol.Coerce(float),
                vol.Optional(CONF_UNITS, default=DEFAULT_UNITS): str,
            })
            
            return self.async_show_form(step_id="processor_config", data_schema=schema)

        # Create processor configuration
        processor_config = {
            "type": PROCESSOR_ANALOG_GAUGE,
            "config": user_input
        }
        
        self.data[CONF_PROCESSORS] = [processor_config]

        return self.async_create_entry(title=self.data["name"], data=self.data)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""