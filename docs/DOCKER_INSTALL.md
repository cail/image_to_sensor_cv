# Installation Guide for Docker Environment

This component requires OpenCV which can be challenging to install in Home Assistant's Docker environment. Here are several approaches to get it working:

## Option 1: Use opencv-python-headless (Recommended)

The component has been updated to use `opencv-python-headless` which should work better in Docker environments. Try restarting Home Assistant after the update.

## Option 2: Manual Docker Installation

If the automatic installation still fails, you can manually install OpenCV in your Home Assistant Docker container:

### For Home Assistant Container

1. **Access the container:**
   ```bash
   docker exec -it homeassistant /bin/bash
   ```

2. **Install OpenCV manually:**
   ```bash
   pip install opencv-python-headless==4.8.1.78 numpy==1.24.3
   ```

3. **Exit and restart container:**
   ```bash
   exit
   docker restart homeassistant
   ```

### For Home Assistant OS/Supervised

If you're using Home Assistant OS or Supervised, you'll need to create a custom Docker image:

1. **Create a custom Dockerfile:**
   ```dockerfile
   FROM homeassistant/home-assistant:stable
   
   RUN pip install opencv-python-headless==4.8.1.78 numpy==1.24.3
   ```

2. **Build and use the custom image**

## Option 3: Alternative Implementation

If OpenCV continues to cause issues, we can create a fallback version using only PIL (Pillow) for basic image processing. This would be less accurate but more compatible.

## Option 4: External Processing Service

Another approach is to run the image processing in a separate container and communicate via MQTT or HTTP API.

## Troubleshooting

### Check if OpenCV is available:
```python
# In Home Assistant Python console or via custom service
try:
    import cv2
    print(f"OpenCV version: {cv2.__version__}")
except ImportError:
    print("OpenCV not available")
```

### Common Issues:

1. **libGL.so.1 error**: This indicates missing system libraries. Use `opencv-python-headless` instead.

2. **Memory issues**: OpenCV can be memory-intensive. Ensure sufficient RAM.

3. **Architecture mismatch**: Make sure the OpenCV version matches your system architecture (ARM vs x86).

## Docker Compose Example

If you're using docker-compose, you can create a custom image:

```yaml
version: '3'
services:
  homeassistant:
    build:
      context: .
      dockerfile: Dockerfile.custom
    # ... rest of your configuration
```

**Dockerfile.custom:**
```dockerfile
FROM homeassistant/home-assistant:stable

# Install system dependencies for OpenCV
USER root
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

USER homeassistant

# Install Python packages
RUN pip install --no-cache-dir \
    opencv-python-headless==4.8.1.78 \
    numpy==1.24.3
```

## Testing the Installation

After installation, restart Home Assistant and try adding the integration. Check the logs for any remaining errors:

```bash
docker logs homeassistant | grep -i opencv
docker logs homeassistant | grep image_to_sensor_cv
```