#!/bin/bash

# Manual installation script for OpenCV in Home Assistant Docker

echo "Installing OpenCV in Home Assistant Docker container..."

# Access the Home Assistant container
docker exec -it homeassistant bash -c "
    echo 'Installing OpenCV and dependencies...'
    pip install --no-cache-dir opencv-python-headless==4.8.1.78
    pip install --no-cache-dir numpy==1.24.3
    echo 'Installation complete!'
    echo 'Testing installation...'
    python -c 'import cv2; print(f\"OpenCV version: {cv2.__version__}\")'
"

echo "Restarting Home Assistant..."
docker restart homeassistant

echo "Done! You can now try adding the Image to Sensor CV integration."