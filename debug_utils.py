"""Debug utilities for Image to Sensor CV."""
from __future__ import annotations

import logging
from typing import Any, Dict
import os

import numpy as np
from PIL import Image

_LOGGER = logging.getLogger(__name__)


def save_debug_image(image_array: np.ndarray, filename: str, stage: str = "", sensor_name: str = "unknown") -> None:
    """Save debug image to help with troubleshooting."""
    try:
        # Create debug directory if it doesn't exist
        debug_dir = "/config/www/image_to_sensor_cv_debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        # Clean sensor name for filename (remove invalid characters)
        clean_sensor_name = "".join(c for c in sensor_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_sensor_name = clean_sensor_name.replace(' ', '_')
        
        # Generate filename with sensor name and stage
        if stage:
            base_name = f"{clean_sensor_name}_{stage}_{filename}"
        else:
            base_name = f"{clean_sensor_name}_{filename}"
            
        file_path = os.path.join(debug_dir, base_name)
        
        # Convert numpy array to PIL and save
        if len(image_array.shape) == 3:
            # Color image
            pil_image = Image.fromarray(image_array.astype('uint8'))
        else:
            # Grayscale image
            pil_image = Image.fromarray(image_array.astype('uint8'), mode='L')
            
        pil_image.save(file_path)
        _LOGGER.debug("Saved debug image: %s", file_path)
        
    except Exception as e:
        _LOGGER.warning("Could not save debug image %s: %s", filename, e)


def enable_debug_logging() -> None:
    """Enable debug logging for the image processing module."""
    logger = logging.getLogger("custom_components.image_to_sensor_cv")
    logger.setLevel(logging.DEBUG)
    
    # Also enable debug for image processing modules specifically
    img_logger = logging.getLogger("custom_components.image_to_sensor_cv.image_processing_simple")
    img_logger.setLevel(logging.DEBUG)
    
    _LOGGER.info("Debug logging enabled for Image to Sensor CV")


def disable_debug_logging() -> None:
    """Disable debug logging for the image processing module."""
    logger = logging.getLogger("custom_components.image_to_sensor_cv")
    logger.setLevel(logging.INFO)
    
    img_logger = logging.getLogger("custom_components.image_to_sensor_cv.image_processing_simple")
    img_logger.setLevel(logging.INFO)
    
    _LOGGER.info("Debug logging disabled for Image to Sensor CV")


def log_detection_summary(angle: float, value: float, config: Dict[str, Any]) -> None:
    """Log a summary of the detection results."""
    _LOGGER.info("=== DETECTION SUMMARY ===")
    _LOGGER.info("Detected needle angle: %.1f°", angle)
    _LOGGER.info("Calculated gauge value: %.2f %s", value, config.get("units", ""))
    _LOGGER.info("Gauge configuration:")
    _LOGGER.info("  Range: %.1f - %.1f hours (%.0f° - %.0f°)", 
                 config["min_angle_hours"], config["max_angle_hours"],
                 config["min_angle_hours"] * 30, config["max_angle_hours"] * 30)
    _LOGGER.info("  Values: %.2f - %.2f %s", 
                 config["min_value"], config["max_value"], config.get("units", ""))
    _LOGGER.info("=========================")


def create_detection_overlay(image_array: np.ndarray, center_x: int, center_y: int, 
                           needle_angle: float, radius: int) -> np.ndarray:
    """Create a debug image with detection overlay."""
    try:
        # Create a copy for overlay
        overlay = image_array.copy()
        
        # If grayscale, convert to RGB for colored overlay
        if len(overlay.shape) == 2:
            overlay = np.stack([overlay, overlay, overlay], axis=2)
        
        # Draw center point (red)
        cv_y, cv_x = max(0, center_y-2), max(0, center_x-2)
        overlay[cv_y:center_y+3, cv_x:center_x+3] = [255, 0, 0]  # Red center
        
        # Draw detected needle line (green)
        import math
        angle_rad = math.radians(needle_angle)
        # Fix: Use same coordinate system as detection (Y-axis flipped)
        end_x = int(center_x + radius * math.cos(angle_rad))
        end_y = int(center_y - radius * math.sin(angle_rad))  # Flip Y for image coordinates
        
        # Simple line drawing (basic implementation)
        # Draw points along the line
        steps = radius
        for i in range(steps):
            t = i / steps
            x = int(center_x + t * (end_x - center_x))
            y = int(center_y + t * (end_y - center_y))
            if 0 <= x < overlay.shape[1] and 0 <= y < overlay.shape[0]:
                overlay[y, x] = [0, 255, 0]  # Green line
        
        return overlay
        
    except Exception as e:
        _LOGGER.warning("Could not create detection overlay: %s", e)
        return image_array