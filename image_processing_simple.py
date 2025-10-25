"""Simplified image processing without OpenCV dependency."""
from __future__ import annotations

import asyncio
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

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any], sensor_name: str = "unknown"):
        """Initialize the image processor."""
        self.hass = hass
        self.config = config
        self.sensor_name = sensor_name

    async def get_image(self) -> Optional[np.ndarray]:
        """Get image from configured source."""
        _LOGGER.debug("Getting image from source: %s", self.config[CONF_IMAGE_SOURCE])
        
        if self.config[CONF_IMAGE_SOURCE] == SOURCE_FILE:
            result = await self._get_image_from_file()
        elif self.config[CONF_IMAGE_SOURCE] == SOURCE_CAMERA:
            result = await self._get_image_from_camera()
        else:
            _LOGGER.error("Unknown image source: %s", self.config[CONF_IMAGE_SOURCE])
            return None
            
        if result is not None:
            _LOGGER.debug("Successfully acquired image with shape: %s", result.shape)
        else:
            _LOGGER.warning("Failed to acquire image from source")
            
        return result

    async def _get_image_from_file(self) -> Optional[np.ndarray]:
        """Load image from file path."""
        try:
            image_path = self.config[CONF_IMAGE_PATH]
            _LOGGER.debug("Loading image from file: %s", image_path)
            
            if not os.path.exists(image_path):
                _LOGGER.error("Image file not found: %s", image_path)
                # List files in the directory for debugging
                try:
                    dir_path = os.path.dirname(image_path)
                    if os.path.exists(dir_path):
                        files = os.listdir(dir_path)
                        _LOGGER.debug("Files in directory %s: %s", dir_path, files[:10])  # Limit to first 10
                except Exception as dir_e:
                    _LOGGER.debug("Could not list directory contents: %s", dir_e)
                return None

            # Use executor to avoid blocking I/O
            loop = asyncio.get_event_loop()
            
            def _load_image():
                _LOGGER.debug("Opening image file with PIL")
                # Load image using PIL
                pil_image = Image.open(image_path)
                _LOGGER.debug("Original image mode: %s, size: %s", pil_image.mode, pil_image.size)
                # Convert to RGB
                pil_image = pil_image.convert('RGB')
                _LOGGER.debug("Converted to RGB, size: %s", pil_image.size)
                # Convert to numpy array
                image_array = np.array(pil_image)
                _LOGGER.debug("Converted to numpy array, shape: %s, dtype: %s", 
                             image_array.shape, image_array.dtype)
                return image_array
            
            result = await loop.run_in_executor(None, _load_image)
            _LOGGER.debug("Image loaded successfully from file")
            
            # Save debug image of original loaded image
            try:
                from .debug_utils import save_debug_image
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    save_debug_image(result, "original.png", "loaded", self.sensor_name)
            except Exception as debug_e:
                _LOGGER.warning("Could not save original debug image: %s", debug_e)
            
            return result
            
        except Exception as e:
            _LOGGER.error("Error loading image from file: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
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
        _LOGGER.debug("Checking crop configuration")
        
        if CONF_CROP_CONFIG not in self.config:
            _LOGGER.debug("No crop configuration found, using full image")
            return image
            
        crop_config = self.config[CONF_CROP_CONFIG]
        x = crop_config.get(CONF_CROP_X, 0)
        y = crop_config.get(CONF_CROP_Y, 0)
        width = crop_config.get(CONF_CROP_WIDTH, image.shape[1])
        height = crop_config.get(CONF_CROP_HEIGHT, image.shape[0])
        
        _LOGGER.debug("Original image shape: %s", image.shape)
        _LOGGER.debug("Requested crop: x=%d, y=%d, width=%d, height=%d", x, y, width, height)
        
        # Ensure crop coordinates are within image bounds
        orig_x, orig_y, orig_width, orig_height = x, y, width, height
        x = max(0, min(x, image.shape[1]))
        y = max(0, min(y, image.shape[0]))
        width = min(width, image.shape[1] - x)
        height = min(height, image.shape[0] - y)
        
        if (x, y, width, height) != (orig_x, orig_y, orig_width, orig_height):
            _LOGGER.debug("Adjusted crop to fit image bounds: x=%d, y=%d, width=%d, height=%d", 
                         x, y, width, height)
        
        cropped = image[y:y+height, x:x+width]
        _LOGGER.debug("Cropped image shape: %s", cropped.shape)
        
        # Save debug image of cropped image
        try:
            from .debug_utils import save_debug_image
            if _LOGGER.isEnabledFor(logging.DEBUG):
                save_debug_image(cropped, "cropped.png", "processed", self.sensor_name)
        except Exception as debug_e:
            _LOGGER.warning("Could not save cropped debug image: %s", debug_e)
        
        return cropped


class SimpleAnalogGaugeProcessor:
    """Simplified analog gauge processor using PIL instead of OpenCV."""

    def __init__(self, config: Dict[str, Any], sensor_name: str = "unknown"):
        """Initialize the analog gauge processor."""
        self.config = config
        self.sensor_name = sensor_name

    def process_image(self, image: np.ndarray) -> Optional[float]:
        """Process image and extract gauge value using simplified method."""
        try:
            _LOGGER.debug("=== Starting gauge image processing ===")
            _LOGGER.debug("Processor config: %s", self.config)
            result = self._read_analog_gauge_simple(image)
            _LOGGER.debug("=== Gauge processing complete, result: %s ===", result)
            return result
        except Exception as e:
            _LOGGER.error("Error processing analog gauge: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return None

    def _read_analog_gauge_simple(self, image_array: np.ndarray) -> Optional[float]:
        """
        Simplified analog gauge reading using PIL and basic image processing.
        This is less accurate than OpenCV but works without additional dependencies.
        """
        try:
            _LOGGER.debug("Starting analog gauge reading process")
            _LOGGER.debug("Input image shape: %s", image_array.shape)
            
            # Convert numpy array back to PIL Image for processing
            pil_image = Image.fromarray(image_array)
            _LOGGER.debug("Converted to PIL image, mode: %s, size: %s", pil_image.mode, pil_image.size)
            
            # Convert to grayscale
            gray_image = pil_image.convert('L')
            _LOGGER.debug("Converted to grayscale")
            
            # Apply some basic filtering to enhance edges
            enhanced = gray_image.filter(ImageFilter.EDGE_ENHANCE_MORE)
            _LOGGER.debug("Applied edge enhancement filter")
            
            # Convert back to numpy for analysis
            gray_array = np.array(enhanced)
            _LOGGER.debug("Gray array shape: %s, dtype: %s", gray_array.shape, gray_array.dtype)
            _LOGGER.debug("Gray array stats - min: %d, max: %d, mean: %.2f", 
                         gray_array.min(), gray_array.max(), gray_array.mean())
            
            # Find the center of the gauge (simplified approach)
            height, width = gray_array.shape
            center_x, center_y = width // 2, height // 2
            _LOGGER.debug("Gauge center calculated at: (%d, %d)", center_x, center_y)
            
            # Use a simplified approach to find the needle
            # This assumes the darkest line from center is the needle
            needle_angle = self._find_needle_angle_simple(gray_array, center_x, center_y)
            
            if needle_angle is None:
                _LOGGER.warning("Could not detect needle angle")
                return None
            
            _LOGGER.debug("Detected needle angle: %.2f degrees", needle_angle)
            
            # Convert angle to gauge value
            value = self._angle_to_value(needle_angle)
            _LOGGER.debug("Converted angle to gauge value: %.2f", value)
            
            # Log detection summary at info level for easier monitoring
            try:
                from .debug_utils import log_detection_summary
                log_detection_summary(needle_angle, value, self.config)
            except Exception as summary_e:
                _LOGGER.warning("Could not log detection summary: %s", summary_e)
            
            return value

        except Exception as e:
            _LOGGER.error("Error in simplified gauge reading: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return None

    def _find_needle_angle_simple(self, gray_array: np.ndarray, cx: int, cy: int) -> Optional[float]:
        """
        Simplified needle detection using radial scanning.
        Scans in radial directions from center to find the darkest path (needle).
        """
        try:
            height, width = gray_array.shape
            radius = min(width, height) // 3  # Search within reasonable radius
            _LOGGER.debug("Starting needle detection - center: (%d, %d), radius: %d", cx, cy, radius)
            
            best_angle = None
            best_score = float('inf')
            angle_scores = []  # Store scores for analysis
            
            # Scan in 5-degree increments first for performance, then refine
            coarse_step = 5
            for angle_deg in range(0, 360, coarse_step):
                angle_rad = math.radians(angle_deg)
                
                # Sample points along this angle
                score = 0.0  # Use float to prevent overflow
                valid_points = 0
                
                for r in range(10, radius, 3):  # Skip very center, sample every 3 pixels
                    # Fix: Image coordinates have Y-axis flipped (0,0 is top-left)
                    # Standard math: angle 0° = right (3 o'clock), 90° = up (12 o'clock)
                    # For gauge: angle 0° = up (12 o'clock), 90° = right (3 o'clock)
                    # Convert: gauge_angle = 90 - math_angle, then flip Y
                    
                    x = int(cx + r * math.cos(angle_rad))
                    y = int(cy - r * math.sin(angle_rad))  # Flip Y axis for image coordinates
                    
                    if 0 <= x < width and 0 <= y < height:
                        # Lower pixel values = darker = more likely to be needle
                        score += float(gray_array[y, x])  # Convert to float to prevent overflow
                        valid_points += 1
                
                if valid_points > 0:
                    avg_score = score / valid_points
                    angle_scores.append((angle_deg, avg_score, valid_points))
                    if avg_score < best_score:
                        best_score = avg_score
                        best_angle = angle_deg
            
            # Sort by score and log top candidates
            angle_scores.sort(key=lambda x: x[1])  # Sort by score (lower = darker)
            _LOGGER.debug("Top 10 needle angle candidates:")
            for i, (angle, score, points) in enumerate(angle_scores[:10]):
                _LOGGER.debug("  %d. Angle: %3d°, Score: %6.2f, Points: %d", 
                             i+1, angle, score, points)
            
            if best_angle is not None:
                # Refine the best angle by scanning ±2 degrees in 1-degree increments
                refined_angle = self._refine_needle_angle(gray_array, cx, cy, best_angle, radius)
                if refined_angle is not None:
                    _LOGGER.debug("Refined needle angle from %d° to %.1f°", best_angle, refined_angle)
                    best_angle = refined_angle
                
                _LOGGER.debug("Final needle angle: %.1f° (math convention), best score: %.2f", best_angle, best_score)
                
                # Convert to clock convention for display
                clock_angle_display = (90 - best_angle) % 360
                _LOGGER.debug("Needle angle in clock convention: %.1f°", clock_angle_display)
                
                # Save debug images if logging is at debug level
                try:
                    from .debug_utils import save_debug_image, create_detection_overlay
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        # Save the processed grayscale image
                        save_debug_image(gray_array, "gauge_processed.png", "grayscale", self.sensor_name)
                        
                        # Create and save detection overlay (using math convention angle)
                        overlay = create_detection_overlay(gray_array, cx, cy, best_angle, radius)
                        save_debug_image(overlay, "gauge_detection.png", "overlay", self.sensor_name)
                except Exception as debug_e:
                    _LOGGER.warning("Could not save debug images: %s", debug_e)
                
                # Additional validation
                if best_score > 200:  # Threshold for "too bright" (needle should be dark)
                    _LOGGER.warning("Needle appears too bright (score: %.2f), detection may be unreliable", best_score)
                
            else:
                _LOGGER.warning("No needle angle detected - all scores were invalid")
                _LOGGER.debug("Image brightness analysis - center region:")
                # Analyze center region brightness
                center_region = gray_array[max(0, cy-20):cy+20, max(0, cx-20):cx+20]
                if center_region.size > 0:
                    _LOGGER.debug("  Center region shape: %s", center_region.shape)
                    _LOGGER.debug("  Center region stats - min: %d, max: %d, mean: %.2f", 
                                 center_region.min(), center_region.max(), center_region.mean())
            
            return best_angle if best_angle is not None else None

        except Exception as e:
            _LOGGER.error("Error finding needle angle: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return None

    def _refine_needle_angle(self, gray_array: np.ndarray, cx: int, cy: int, 
                           coarse_angle: int, radius: int) -> Optional[float]:
        """Refine the needle angle by scanning around the coarse angle."""
        try:
            height, width = gray_array.shape
            best_angle = coarse_angle
            best_score = float('inf')
            
            # Scan ±4 degrees around the coarse angle in 0.5-degree increments
            for angle_offset in range(-8, 9):  # -4 to +4 degrees in 0.5 increments
                angle_deg = coarse_angle + (angle_offset * 0.5)
                angle_rad = math.radians(angle_deg)
                
                score = 0.0  # Use float to prevent overflow
                valid_points = 0
                
                for r in range(8, radius, 2):  # More precise sampling
                    # Apply same coordinate system fix as main detection
                    x = int(cx + r * math.cos(angle_rad))
                    y = int(cy - r * math.sin(angle_rad))  # Flip Y axis for image coordinates
                    
                    if 0 <= x < width and 0 <= y < height:
                        score += float(gray_array[y, x])  # Convert to float to prevent overflow
                        valid_points += 1
                
                if valid_points > 0:
                    avg_score = score / valid_points
                    if avg_score < best_score:
                        best_score = avg_score
                        best_angle = angle_deg
            
            return best_angle
            
        except Exception as e:
            _LOGGER.error("Error refining needle angle: %s", e)
            return None

    def _angle_to_value(self, angle: float) -> float:
        """Convert angle to gauge value using configuration."""
        # Convert clock hours to degrees (clock convention: 12=0°, 3=90°, 6=180°, 9=270°)
        min_angle_deg = self.config["min_angle_hours"] * 30  # 30 degrees per hour
        max_angle_deg = self.config["max_angle_hours"] * 30
        
        min_value = self.config["min_value"]
        max_value = self.config["max_value"]

        _LOGGER.debug("Angle conversion config:")
        _LOGGER.debug("  Min angle: %.1f hours = %.1f degrees (clock)", self.config["min_angle_hours"], min_angle_deg)
        _LOGGER.debug("  Max angle: %.1f hours = %.1f degrees (clock)", self.config["max_angle_hours"], max_angle_deg)
        _LOGGER.debug("  Value range: %.2f to %.2f %s", min_value, max_value, self.config.get("units", ""))
        _LOGGER.debug("  Raw detected angle: %.1f degrees (math convention)", angle)
        
        # Convert from mathematical angle convention to clock convention
        # Math: 0°=right, 90°=up, 180°=left, 270°=down
        # Clock: 0°=up(12), 90°=right(3), 180°=down(6), 270°=left(9)
        # Conversion: clock_angle = (90 - math_angle) % 360
        clock_angle = (90 - angle) % 360
        _LOGGER.debug("  Converted to clock angle: %.1f degrees", clock_angle)

        # Handle angle wrapping (e.g., from 7 o'clock to 5 o'clock)
        if min_angle_deg > max_angle_deg:
            # Gauge spans across 0 degrees (e.g., 210° to 150°)
            _LOGGER.debug("Handling angle wrapping (gauge spans across 0°)")
            if clock_angle >= min_angle_deg:
                angle_normalized = clock_angle - min_angle_deg
            else:
                angle_normalized = (360 - min_angle_deg) + clock_angle
            total_range = (360 - min_angle_deg) + max_angle_deg
            _LOGGER.debug("  Normalized angle: %.1f°, Total range: %.1f°", angle_normalized, total_range)
        else:
            # Normal case
            _LOGGER.debug("Normal angle range (no wrapping)")
            angle_normalized = clock_angle - min_angle_deg
            total_range = max_angle_deg - min_angle_deg
            _LOGGER.debug("  Normalized angle: %.1f°, Total range: %.1f°", angle_normalized, total_range)

        if total_range == 0:
            _LOGGER.warning("Total angle range is 0, returning min value")
            return min_value
            
        # Map angle to value
        value_range = max_value - min_value
        new_value = (angle_normalized / total_range) * value_range + min_value
        
        _LOGGER.debug("  Calculated raw value: %.3f", new_value)
        
        # Clamp to valid range
        clamped_value = max(min_value, min(max_value, new_value))
        if clamped_value != new_value:
            _LOGGER.debug("  Value clamped from %.3f to %.3f", new_value, clamped_value)
        
        _LOGGER.debug("  Final gauge value: %.2f %s", clamped_value, self.config.get("units", ""))
        
        return clamped_value


def create_simple_processor(processor_type: str, config: Dict[str, Any], sensor_name: str = "unknown"):
    """Create a simplified processor based on type."""
    if processor_type == PROCESSOR_ANALOG_GAUGE:
        return SimpleAnalogGaugeProcessor(config, sensor_name)
    else:
        raise ValueError(f"Unknown processor type: {processor_type}")