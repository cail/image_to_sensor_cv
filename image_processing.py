"""Image processing utilities for Image to Sensor CV."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import asyncio
import os
from pathlib import Path

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    _LOGGER = logging.getLogger(__name__)
    _LOGGER.warning("OpenCV not available. Image processing features will be limited.")

import numpy as np
from PIL import Image
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


class ImageProcessor:
    """Base class for image processing."""

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

            # Load image using PIL first, then convert to OpenCV format
            pil_image = Image.open(image_path)
            # Convert PIL image to RGB (from potential RGBA or other formats)
            pil_image = pil_image.convert('RGB')
            # Convert to numpy array and then to BGR for OpenCV
            image_array = np.array(pil_image)
            # Convert RGB to BGR for OpenCV
            bgr_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            return bgr_image
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
                    # Convert bytes to numpy array
                    nparr = np.frombuffer(image_data, np.uint8)
                    # Decode image
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    return image
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


class AnalogGaugeProcessor:
    """Processor for reading analog gauge values from images."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the analog gauge processor."""
        self.config = config

    def process_image(self, image: np.ndarray) -> Optional[float]:
        """Process image and extract gauge value."""
        if not HAS_OPENCV:
            _LOGGER.error("OpenCV is required for analog gauge processing but not available")
            return None
            
        try:
            return self._read_analog_gauge(image)
        except Exception as e:
            _LOGGER.error("Error processing analog gauge: %s", e)
            return None

    def _read_analog_gauge(self, img: np.ndarray) -> Optional[float]:
        """
        Read analog gauge value from image.
        Adapted from the original Test_Video.py implementation.
        """
        try:
            # Apply Gaussian blur and convert to grayscale
            img_blur = cv2.GaussianBlur(img, (5, 5), 3)
            gray = cv2.cvtColor(img_blur, cv2.COLOR_BGR2GRAY)
            height, width = img.shape[:2]

            # Find circles using HoughCircles
            circles = cv2.HoughCircles(
                gray, 
                cv2.HOUGH_GRADIENT, 
                1, 
                20, 
                np.array([]), 
                100, 
                50, 
                int(height * 0.35), 
                int(height * 0.48)
            )

            if circles is None:
                _LOGGER.warning("No circles detected in gauge image")
                return None

            # Average found circles for better accuracy
            a, b, c = circles.shape
            x, y, r = self._avg_circles(circles, b)

            # Find the needle line
            needle_line = self._find_needle_line(img, x, y, r)
            if needle_line is None:
                _LOGGER.warning("No needle line detected")
                return None

            x1, y1, x2, y2 = needle_line

            # Calculate angle from needle line
            angle = self._calculate_needle_angle(x, y, x1, y1, x2, y2)
            
            # Convert angle to gauge value
            value = self._angle_to_value(angle)
            
            return value

        except Exception as e:
            _LOGGER.error("Error in analog gauge reading: %s", e)
            return None

    def _avg_circles(self, circles: np.ndarray, b: int) -> tuple[int, int, int]:
        """Average multiple circles for better accuracy."""
        avg_x = avg_y = avg_r = 0
        for i in range(b):
            avg_x += circles[0][i][0]
            avg_y += circles[0][i][1]
            avg_r += circles[0][i][2]
        
        avg_x = int(avg_x / b)
        avg_y = int(avg_y / b)
        avg_r = int(avg_r / b)
        
        return avg_x, avg_y, avg_r

    def _dist_2_pts(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate distance between two points."""
        return np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def _find_needle_line(self, img: np.ndarray, x: int, y: int, r: int) -> Optional[tuple[int, int, int, int]]:
        """Find the needle line in the gauge."""
        try:
            gray2 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply thresholding
            thresh = 175
            maxValue = 255
            th, dst2 = cv2.threshold(gray2, thresh, maxValue, cv2.THRESH_BINARY_INV)

            # Find lines using HoughLinesP
            minLineLength = 10
            maxLineGap = 0
            lines = cv2.HoughLinesP(
                image=dst2, 
                rho=3, 
                theta=np.pi / 180, 
                threshold=100,
                minLineLength=minLineLength, 
                maxLineGap=maxLineGap
            )

            if lines is None:
                return None

            # Filter lines based on distance from center
            final_line_list = []
            diff1LowerBound = 0.15
            diff1UpperBound = 0.25
            diff2LowerBound = 0.5
            diff2UpperBound = 1.0

            for line in lines:
                x1, y1, x2, y2 = line[0]
                diff1 = self._dist_2_pts(x, y, x1, y1)
                diff2 = self._dist_2_pts(x, y, x2, y2)
                
                # Set diff1 to be the smaller (closest to center)
                if diff1 > diff2:
                    diff1, diff2 = diff2, diff1
                
                # Check if line is within acceptable range
                if (diff1 < diff1UpperBound * r and diff1 > diff1LowerBound * r and 
                    diff2 < diff2UpperBound * r and diff2 > diff2LowerBound * r):
                    final_line_list.append([x1, y1, x2, y2])

            if not final_line_list:
                return None

            # Return the first (best) line
            return tuple(final_line_list[0])

        except Exception as e:
            _LOGGER.error("Error finding needle line: %s", e)
            return None

    def _calculate_needle_angle(self, cx: int, cy: int, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate the angle of the needle."""
        # Find the farthest point from center
        dist_pt_0 = self._dist_2_pts(cx, cy, x1, y1)
        dist_pt_1 = self._dist_2_pts(cx, cy, x2, y2)
        
        if dist_pt_0 > dist_pt_1:
            x_angle = x1 - cx
            y_angle = cy - y1
        else:
            x_angle = x2 - cx
            y_angle = cy - y2

        # Calculate angle using arctan
        res = np.arctan(np.divide(float(y_angle), float(x_angle)))
        res = np.rad2deg(res)

        # Determine final angle based on quadrant
        if x_angle > 0 and y_angle > 0:  # Quadrant I
            final_angle = 270 - res
        elif x_angle < 0 and y_angle > 0:  # Quadrant II
            final_angle = 90 - res
        elif x_angle < 0 and y_angle < 0:  # Quadrant III
            final_angle = 90 - res
        elif x_angle > 0 and y_angle < 0:  # Quadrant IV
            final_angle = 270 - res
        else:
            final_angle = 0

        return final_angle

    def _angle_to_value(self, angle: float) -> float:
        """Convert angle to gauge value using configuration."""
        # Convert clock hours to degrees
        min_angle_deg = self.config["min_angle_hours"] * 30  # 30 degrees per hour
        max_angle_deg = self.config["max_angle_hours"] * 30
        
        min_value = self.config["min_value"]
        max_value = self.config["max_value"]

        # Map angle to value
        old_range = max_angle_deg - min_angle_deg
        new_range = max_value - min_value
        
        if old_range == 0:
            return min_value
            
        new_value = (((angle - min_angle_deg) * new_range) / old_range) + min_value
        
        # Clamp to valid range
        return max(min_value, min(max_value, new_value))


def create_processor(processor_type: str, config: Dict[str, Any]):
    """Create a processor based on type."""
    if processor_type == PROCESSOR_ANALOG_GAUGE:
        return AnalogGaugeProcessor(config)
    else:
        raise ValueError(f"Unknown processor type: {processor_type}")