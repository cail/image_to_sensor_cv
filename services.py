"""Services for Image to Sensor CV integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_PROCESS_IMAGE = "process_image"
SERVICE_ENABLE_DEBUG = "enable_debug_logging"
SERVICE_DISABLE_DEBUG = "disable_debug_logging"
SERVICE_GENERATE_PREVIEW = "generate_preview"

SERVICE_PROCESS_IMAGE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
})

SERVICE_DEBUG_SCHEMA = vol.Schema({})

SERVICE_GENERATE_PREVIEW_SCHEMA = vol.Schema({
    vol.Required("config_entry_id"): str,
    vol.Optional("crop_x", default=0): int,
    vol.Optional("crop_y", default=0): int,
    vol.Optional("crop_width", default=100): int,
    vol.Optional("crop_height", default=100): int,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the Image to Sensor CV integration."""
    
    async def handle_process_image(call: ServiceCall) -> None:
        """Handle the process_image service call."""
        entity_id = call.data["entity_id"]
        
        # Get the entity
        entity = hass.states.get(entity_id)
        if entity is None:
            _LOGGER.error("Entity %s not found", entity_id)
            return
            
        # Trigger update for the specific entity
        # This would need to be implemented based on the specific entity structure
        _LOGGER.info("Processing image for entity %s", entity_id)

    async def handle_enable_debug(call: ServiceCall) -> None:
        """Handle the enable_debug_logging service call."""
        try:
            from .debug_utils import enable_debug_logging
            enable_debug_logging()
            _LOGGER.info("Debug logging enabled via service call")
        except Exception as e:
            _LOGGER.error("Failed to enable debug logging: %s", e)

    async def handle_disable_debug(call: ServiceCall) -> None:
        """Handle the disable_debug_logging service call."""
        try:
            from .debug_utils import disable_debug_logging
            disable_debug_logging()
            _LOGGER.info("Debug logging disabled via service call")
        except Exception as e:
            _LOGGER.error("Failed to disable debug logging: %s", e)

    async def handle_generate_preview(call: ServiceCall) -> None:
        """Handle the generate_preview service call."""
        try:
            import io
            import base64
            import os
            from PIL import Image, ImageDraw
            from .image_processing_simple import SimpleImageProcessor
            from .const import (
                CONF_CROP_CONFIG, CONF_CROP_X, CONF_CROP_Y, 
                CONF_CROP_WIDTH, CONF_CROP_HEIGHT
            )
            
            config_entry_id = call.data["config_entry_id"]
            
            # Get config entry data
            if config_entry_id not in hass.data[DOMAIN]:
                _LOGGER.error("Config entry %s not found", config_entry_id)
                return
                
            config_data = hass.data[DOMAIN][config_entry_id].copy()
            
            # Override crop settings with service call parameters
            crop_config = {
                CONF_CROP_X: call.data.get("crop_x", 0),
                CONF_CROP_Y: call.data.get("crop_y", 0),
                CONF_CROP_WIDTH: call.data.get("crop_width", 100),
                CONF_CROP_HEIGHT: call.data.get("crop_height", 100),
            }
            config_data[CONF_CROP_CONFIG] = crop_config
            
            # Create image processor
            processor = SimpleImageProcessor(hass, config_data, "preview_service")
            
            # Get the image
            image = await processor.get_image()
            if image is None:
                _LOGGER.error("Failed to get image from source")
                return
            
            # Convert PIL image if needed
            if hasattr(image, 'size'):
                pil_image = image
            else:
                # Convert numpy array to PIL
                from PIL import Image as PILImage
                pil_image = PILImage.fromarray(image)
            
            # Create preview with crop overlay
            preview_image = pil_image.copy()
            draw = ImageDraw.Draw(preview_image)
            
            # Draw crop rectangle
            crop_x = crop_config[CONF_CROP_X]
            crop_y = crop_config[CONF_CROP_Y]
            crop_width = crop_config[CONF_CROP_WIDTH]
            crop_height = crop_config[CONF_CROP_HEIGHT]
            
            img_width, img_height = preview_image.size
            actual_crop_x = min(crop_x, img_width - 1)
            actual_crop_y = min(crop_y, img_height - 1)
            actual_crop_width = min(crop_width, img_width - actual_crop_x)
            actual_crop_height = min(crop_height, img_height - actual_crop_y)
            
            # Draw red rectangle for crop area
            draw.rectangle([
                actual_crop_x, 
                actual_crop_y, 
                actual_crop_x + actual_crop_width, 
                actual_crop_y + actual_crop_height
            ], outline="red", width=3)
            
            # Save preview to www folder
            www_path = hass.config.path("www")
            os.makedirs(www_path, exist_ok=True)
            
            preview_path = os.path.join(www_path, f"image_to_sensor_cv_preview_{config_entry_id}.png")
            preview_image.save(preview_path)
            
            # Create URL for the preview
            preview_url = f"/local/image_to_sensor_cv_preview_{config_entry_id}.png"
            
            _LOGGER.info("Preview generated and saved to %s", preview_url)
            
            # Fire an event with the preview URL
            hass.bus.async_fire(
                f"{DOMAIN}_preview_generated",
                {
                    "config_entry_id": config_entry_id,
                    "preview_url": preview_url,
                    "crop_settings": crop_config,
                }
            )
            
        except Exception as e:
            _LOGGER.error("Failed to generate preview: %s", e)

    hass.services.async_register(
        DOMAIN,
        SERVICE_PROCESS_IMAGE,
        handle_process_image,
        schema=SERVICE_PROCESS_IMAGE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_DEBUG,
        handle_enable_debug,
        schema=SERVICE_DEBUG_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_DEBUG,
        handle_disable_debug,
        schema=SERVICE_DEBUG_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_PREVIEW,
        handle_generate_preview,
        schema=SERVICE_GENERATE_PREVIEW_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for the Image to Sensor CV integration."""
    hass.services.async_remove(DOMAIN, SERVICE_PROCESS_IMAGE)
    hass.services.async_remove(DOMAIN, SERVICE_ENABLE_DEBUG)
    hass.services.async_remove(DOMAIN, SERVICE_DISABLE_DEBUG)
    hass.services.async_remove(DOMAIN, SERVICE_GENERATE_PREVIEW)