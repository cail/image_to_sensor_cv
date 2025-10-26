"""Sensor platform for Image to Sensor CV integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_PROCESSORS, DEFAULT_SCAN_INTERVAL

# Always use the simple image processor since we're using minimal dependencies
from .image_processing_simple import create_simple_processor as create_processor
from .image_processing_ha import SimpleImageProcessor as ImageProcessor

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Image to Sensor CV sensor platform."""
    _LOGGER.debug("Starting sensor platform setup for entry: %s", config_entry.entry_id)
    
    try:
        config = hass.data[DOMAIN][config_entry.entry_id]

        # Create coordinator for updating sensor data
        coordinator = ImageSensorCoordinator(hass, config, config_entry)
        
        _LOGGER.debug("Created coordinator, performing first refresh")
        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()
        
        _LOGGER.debug("First refresh complete")

        # Create sensor entities for each processor
        entities = []
        processors = config.get(CONF_PROCESSORS, [])
        
        _LOGGER.debug("Creating %d sensor entities", len(processors))
        for i, processor_config in enumerate(processors):
            entities.append(
                ImageSensorEntity(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    processor_index=i,
                    processor_config=processor_config,
                )
            )

        async_add_entities(entities)
        _LOGGER.debug("Sensor platform setup complete")
        
    except Exception as err:
        _LOGGER.error(
            "Error during sensor platform setup: %s",
            err,
            exc_info=True
        )
        raise


class ImageSensorCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from image processing."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any], config_entry: ConfigEntry) -> None:
        """Initialize."""
        self.config = config
        self.config_entry = config_entry
        # Use config entry title as base sensor name for image processor
        base_sensor_name = config_entry.title
        self.image_processor = ImageProcessor(hass, config, base_sensor_name)
        self.processors = []
        
        # Create processors based on configuration
        self._create_processors()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    def _create_processors(self) -> None:
        """Create processors based on current configuration."""
        self.processors = []
        for i, processor_config in enumerate(self.config.get(CONF_PROCESSORS, [])):
            # Create a sensor name for this processor
            sensor_name = f"{self.config_entry.title}_processor_{i}"
            processor = create_processor(
                processor_config["type"], 
                processor_config["config"],
                sensor_name
            )
            self.processors.append(processor)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update configuration and recreate processors."""
        self.config = new_config
        # Recreate image processor with new config
        base_sensor_name = self.config_entry.title
        self.image_processor = ImageProcessor(self.hass, new_config, base_sensor_name)
        # Recreate processors
        self._create_processors()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            # Get image from configured source
            image = await self.image_processor.get_image()
            if image is None:
                raise UpdateFailed("Failed to get image from source")

            # Apply cropping if configured
            cropped_image = self.image_processor.crop_image(image)

            # Process image with each processor
            results = {}
            for i, processor in enumerate(self.processors):
                try:
                    result = processor.process_image(cropped_image)
                    results[f"processor_{i}"] = {
                        "value": result,
                        "timestamp": dt_util.utcnow(),
                    }
                except Exception as e:
                    _LOGGER.error("Error processing with processor %d: %s", i, e)
                    results[f"processor_{i}"] = {
                        "value": None,
                        "timestamp": dt_util.utcnow(),
                        "error": str(e),
                    }

            return results

        except Exception as err:
            raise UpdateFailed(f"Error communicating with image source: {err}")


class ImageSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of an Image Sensor CV sensor."""

    def __init__(
        self,
        coordinator: ImageSensorCoordinator,
        config_entry: ConfigEntry,
        processor_index: int,
        processor_config: Dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self.config_entry = config_entry
        self.processor_index = processor_index
        self.processor_config = processor_config
        
        # Generate unique ID
        self._attr_unique_id = f"{config_entry.entry_id}_processor_{processor_index}"
        
        # Set name based on processor type and index
        processor_type = processor_config["type"]
        self._attr_name = f"{config_entry.title} {processor_type.replace('_', ' ').title()} {processor_index + 1}"
        
        # Set unit of measurement from processor config
        if processor_type == "analog_gauge_reader":
            units = processor_config["config"].get("units", "")
            if units:
                self._attr_native_unit_of_measurement = units
                
        # Set device class if applicable
        self._attr_device_class = None
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float]:
        """Return the native value of the sensor."""
        data_key = f"processor_{self.processor_index}"
        if self.coordinator.data and data_key in self.coordinator.data:
            return self.coordinator.data[data_key]["value"]
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        data_key = f"processor_{self.processor_index}"
        return (
            self.coordinator.last_update_success 
            and self.coordinator.data 
            and data_key in self.coordinator.data
            and self.coordinator.data[data_key]["value"] is not None
        )

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        data_key = f"processor_{self.processor_index}"
        attributes = {
            "processor_type": self.processor_config["type"],
            "processor_config": self.processor_config["config"],
        }
        
        if self.coordinator.data and data_key in self.coordinator.data:
            data = self.coordinator.data[data_key]
            if "timestamp" in data:
                attributes["last_reading_time"] = data["timestamp"].isoformat()
            if "error" in data:
                attributes["last_error"] = data["error"]
                
        return attributes

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": self.config_entry.title,
            "manufacturer": "Image to Sensor CV",
            "model": "Image Processor",
            "sw_version": "1.0.0",
        }