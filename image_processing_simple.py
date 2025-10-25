"""Simplified image processing without OpenCV dependency."""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, Optional
import os

import numpy as np
from PIL import Image, ImageFilter, ImageOps
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    SOURCE_FILE,
    SOURCE_CAMERA,
    PROCESSOR_ANALOG_GAUGE,
    CONF_IMAGE_SOURCE,
    CONF_IMAGE_PATH,
    CONF_CAMERA_ENTITY,
    CONF_CROP_CONFIG,
    CONF_CROP_X,
    CONF_CROP_Y,
    CONF_CROP_WIDTH,
    CONF_CROP_HEIGHT,
)

_LOGGER = logging.getLogger(__name__)


class SimpleImageProcessor:
    """Simplified image processor using only PIL/Pillow."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the image processor."""
        self.hass = hass
        self.config = config

    async def get_image(self) -> Optional[np.ndarray]:
        """Get image from configured source."""
        if self.config[CONF_IMAGE_SOURCE] == SOURCE_FILE:
            return await self._get_image_from_file()
        elif self.config[CONF_IMAGE_SOURCE] == SOURCE_CAMERA:
            return await self._get_image_from_camera()
        return None

    async def _get_image_from_file(self) -> Optional[np.ndarray]:
        """Load image from file path."""
        try:
            image_path = self.config[CONF_IMAGE_PATH]
            if not os.path.exists(image_path):
                _LOGGER.error("Image file not found: %s", image_path)
                return None

            # Load image using PIL
            pil_image = Image.open(image_path)
            # Convert to RGB
            pil_image = pil_image.convert('RGB')
            # Convert to numpy array
            image_array = np.array(pil_image)
            
            return image_array
        except Exception as e:
            _LOGGER.error("Error loading image from file: %s", e)
            return None

    async def _get_image_from_camera(self) -> Optional[np.ndarray]:
        """Get image from Home Assistant camera entity."""
        try:
            camera_entity = self.config[CONF_CAMERA_ENTITY]
            
            # Get camera image URL
            camera_image_url = f"/api/camera_proxy/{camera_entity}"
            
            session = async_get_clientsession(self.hass)
            
            async with session.get(
                f"http://localhost:8123{camera_image_url}",
                headers={"Authorization": f"Bearer {self.hass.auth.async_create_access_token()}"}
            ) as response:
                if response.status == 200:
                    image_data = await response.read()
                    # Use PIL to decode image
                    from io import BytesIO
                    pil_image = Image.open(BytesIO(image_data))
                    pil_image = pil_image.convert('RGB')
                    image_array = np.array(pil_image)
                    return image_array
                else:
                    _LOGGER.error("Failed to get camera image, status: %s", response.status)
                    return None
                    
        except Exception as e:
            _LOGGER.error("Error getting image from camera: %s", e)
            return None

    def crop_image(self, image: np.ndarray) -> np.ndarray:
        """Crop image based on configuration."""
        if CONF_CROP_CONFIG not in self.config:
            return image
            
        crop_config = self.config[CONF_CROP_CONFIG]
        x = crop_config.get(CONF_CROP_X, 0)
        y = crop_config.get(CONF_CROP_Y, 0)
        width = crop_config.get(CONF_CROP_WIDTH, image.shape[1])
        height = crop_config.get(CONF_CROP_HEIGHT, image.shape[0])
        
        # Ensure crop coordinates are within image bounds
        x = max(0, min(x, image.shape[1]))
        y = max(0, min(y, image.shape[0]))
        width = min(width, image.shape[1] - x)
        height = min(height, image.shape[0] - y)
        
        return image[y:y+height, x:x+width]


class SimpleAnalogGaugeProcessor:
    """Simplified analog gauge processor using PIL instead of OpenCV."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the analog gauge processor."""
        self.config = config

    def process_image(self, image: np.ndarray) -> Optional[float]:
        """Process image and extract gauge value using simplified method."""
        try:
            return self._read_analog_gauge_simple(image)
        except Exception as e:
            _LOGGER.error("Error processing analog gauge: %s", e)
            return None

    def _read_analog_gauge_simple(self, image_array: np.ndarray) -> Optional[float]:
        """
        Simplified analog gauge reading using PIL and basic image processing.
        This is less accurate than OpenCV but works without additional dependencies.
        """
        try:
            # Convert numpy array back to PIL Image for processing
            pil_image = Image.fromarray(image_array)
            
            # Convert to grayscale
            gray_image = pil_image.convert('L')
            
            # Apply some basic filtering to enhance edges
            enhanced = gray_image.filter(ImageFilter.EDGE_ENHANCE_MORE)
            
            # Convert back to numpy for analysis
            gray_array = np.array(enhanced)
            
            # Find the center of the gauge (simplified approach)
            height, width = gray_array.shape
            center_x, center_y = width // 2, height // 2
            
            # Use a simplified approach to find the needle
            # This assumes the darkest line from center is the needle
            needle_angle = self._find_needle_angle_simple(gray_array, center_x, center_y)
            
            if needle_angle is None:
                _LOGGER.warning("Could not detect needle angle")
                return None
            
            # Convert angle to gauge value
            value = self._angle_to_value(needle_angle)
            
            return value

        except Exception as e:
            _LOGGER.error("Error in simplified gauge reading: %s", e)
            return None

    def _find_needle_angle_simple(self, gray_array: np.ndarray, cx: int, cy: int) -> Optional[float]:
        """
        Simplified needle detection using radial scanning.
        Scans in radial directions from center to find the darkest path (needle).
        """
        try:
            height, width = gray_array.shape
            radius = min(width, height) // 3  # Search within reasonable radius
            
            best_angle = None
            best_score = float('inf')
            
            # Scan in 1-degree increments
            for angle_deg in range(0, 360, 1):
                angle_rad = math.radians(angle_deg)
                
                # Sample points along this angle
                score = 0
                valid_points = 0
                
                for r in range(10, radius, 2):  # Skip very center, sample every 2 pixels
                    x = int(cx + r * math.cos(angle_rad))
                    y = int(cy + r * math.sin(angle_rad))
                    
                    if 0 <= x < width and 0 <= y < height:
                        # Lower pixel values = darker = more likely to be needle
                        score += gray_array[y, x]
                        valid_points += 1
                
                if valid_points > 0:
                    avg_score = score / valid_points
                    if avg_score < best_score:
                        best_score = avg_score
                        best_angle = angle_deg
            
            return best_angle if best_angle is not None else None

        except Exception as e:
            _LOGGER.error("Error finding needle angle: %s", e)
            return None

    def _angle_to_value(self, angle: float) -> float:
        """Convert angle to gauge value using configuration."""
        # Convert clock hours to degrees
        min_angle_deg = self.config["min_angle_hours"] * 30  # 30 degrees per hour
        max_angle_deg = self.config["max_angle_hours"] * 30
        
        min_value = self.config["min_value"]
        max_value = self.config["max_value"]

        # Handle angle wrapping (e.g., from 7 o'clock to 5 o'clock)
        if min_angle_deg > max_angle_deg:
            # Gauge spans across 0 degrees (e.g., 210° to 150°)
            if angle >= min_angle_deg:
                angle_normalized = angle - min_angle_deg
            else:
                angle_normalized = (360 - min_angle_deg) + angle
            total_range = (360 - min_angle_deg) + max_angle_deg
        else:
            # Normal case
            angle_normalized = angle - min_angle_deg
            total_range = max_angle_deg - min_angle_deg

        if total_range == 0:
            return min_value
            
        # Map angle to value
        value_range = max_value - min_value
        new_value = (angle_normalized / total_range) * value_range + min_value
        
        # Clamp to valid range
        return max(min_value, min(max_value, new_value))


def create_simple_processor(processor_type: str, config: Dict[str, Any]):
    """Create a simplified processor based on type."""
    if processor_type == PROCESSOR_ANALOG_GAUGE:
        return SimpleAnalogGaugeProcessor(config)
    else:
        raise ValueError(f"Unknown processor type: {processor_type}")