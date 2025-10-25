# Debug Guide for Image to Sensor CV

This guide helps you troubleshoot detection issues with the Image to Sensor CV component.

## Enable Debug Logging

### Method 1: Via Home Assistant Service
1. Go to **Developer Tools** → **Services**
2. Call service: `image_to_sensor_cv.enable_debug_logging`
3. No parameters needed

### Method 2: Via Configuration.yaml
Add to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.image_to_sensor_cv: debug
    custom_components.image_to_sensor_cv.image_processing_simple: debug
```

## Debug Information Provided

When debug logging is enabled, you'll get:

### 1. **Detailed Processing Logs**
```
[DEBUG] === Starting gauge image processing ===
[DEBUG] Processor config: {'min_angle_hours': 7, 'max_angle_hours': 5, ...}
[DEBUG] Starting analog gauge reading process
[DEBUG] Input image shape: (480, 640, 3)
[DEBUG] Converted to PIL image, mode: RGB, size: (640, 480)
[DEBUG] Applied edge enhancement filter
[DEBUG] Gray array shape: (480, 640), dtype: uint8
[DEBUG] Gray array stats - min: 12, max: 255, mean: 127.45
```

### 2. **Image Acquisition Debug**
```
[DEBUG] Getting image from source: file
[DEBUG] Loading image from file: /config/www/pressure-gauge.jpg
[DEBUG] Original image mode: RGB, size: (800, 600)
[DEBUG] Successfully acquired image with shape: (600, 800, 3)
```

### 3. **Cropping Information**
```
[DEBUG] Checking crop configuration
[DEBUG] Original image shape: (600, 800, 3)
[DEBUG] Requested crop: x=100, y=50, width=400, height=400
[DEBUG] Cropped image shape: (400, 400, 3)
```

### 4. **Needle Detection Analysis**
```
[DEBUG] Starting needle detection - center: (200, 200), radius: 66
[DEBUG] Top 10 needle angle candidates:
[DEBUG]   1. Angle: 142°, Score:  89.23, Points: 22
[DEBUG]   2. Angle: 141°, Score:  91.45, Points: 22
[DEBUG]   3. Angle: 143°, Score:  93.12, Points: 22
[DEBUG] Refined needle angle from 142° to 142.5°
[DEBUG] Final needle angle: 142.5°, best score: 89.23
```

### 5. **Value Conversion Details**
```
[DEBUG] Angle conversion config:
[DEBUG]   Min angle: 7.0 hours = 210.0 degrees
[DEBUG]   Max angle: 5.0 hours = 150.0 degrees
[DEBUG]   Value range: 0.00 to 100.00 psi
[DEBUG]   Input needle angle: 142.5 degrees
[DEBUG] Handling angle wrapping (gauge spans across 0°)
[DEBUG]   Normalized angle: 292.5°, Total range: 300.0°
[DEBUG]   Calculated raw value: 97.500
[DEBUG]   Final gauge value: 97.50 psi
```

### 6. **Detection Summary**
```
[INFO] === DETECTION SUMMARY ===
[INFO] Detected needle angle: 142.5°
[INFO] Calculated gauge value: 97.50 psi
[INFO] Gauge configuration:
[INFO]   Range: 7.0 - 5.0 hours (210° - 150°)
[INFO]   Values: 0.00 - 100.00 psi
[INFO] =========================
```

## Debug Images

When debug logging is enabled, the component saves debug images to:
`/config/www/image_to_sensor_cv_debug/`

### Available Debug Images:
Each sensor creates its own set of debug images with the sensor name prefix:

- **`{sensor_name}_loaded_original.png`**: The original loaded image before processing
- **`{sensor_name}_processed_cropped.png`**: The cropped image ready for processing
- **`{sensor_name}_grayscale_gauge_processed.png`**: The processed grayscale image used for detection
- **`{sensor_name}_overlay_gauge_detection.png`**: Image with detection overlay showing center point and detected needle

Example for a sensor named "Pressure Gauge Monitor":
- `Pressure_Gauge_Monitor_processor_0_loaded_original.png`
- `Pressure_Gauge_Monitor_processor_0_processed_cropped.png`
- `Pressure_Gauge_Monitor_processor_0_grayscale_gauge_processed.png`
- `Pressure_Gauge_Monitor_processor_0_overlay_gauge_detection.png`

You can view these images by navigating to:
`http://your-ha-ip:8123/local/image_to_sensor_cv_debug/`

**Note:** Each sensor creates its own set of debug images with unique names, so multiple sensors won't overwrite each other's debug files. The sensor name and processor index are included in the filename to ensure uniqueness.

## Common Issues and Solutions

### 1. **No Needle Detected**
**Symptoms:**
```
[WARNING] Could not detect needle angle
[WARNING] No needle angle detected - all scores were invalid
```

**Debug Analysis:**
- Check if needle is dark enough compared to background
- Verify gauge center detection is correct
- Look at debug images to see what the processor is analyzing

**Solutions:**
- Adjust image cropping to focus on gauge only
- Improve image lighting/contrast
- Try different min/max angle configurations

### 2. **Needle Too Bright Warning**
**Symptoms:**
```
[WARNING] Needle appears too bright (score: 245.67), detection may be unreliable
```

**Analysis:**
- The needle is lighter than the background
- Detection algorithm looks for dark lines

**Solutions:**
- Improve image contrast
- Check if image is inverted
- Adjust lighting conditions

### 3. **Incorrect Value Mapping**
**Symptoms:**
- Needle detected correctly but wrong value calculated

**Debug Analysis:**
Look at the angle conversion logs:
```
[DEBUG] Input needle angle: 142.5 degrees
[DEBUG] Final gauge value: 97.50 psi
```

**Solutions:**
- Verify min/max angle hours match your gauge
- Check min/max values are correct
- Confirm gauge orientation (clockwise vs counter-clockwise)

### 4. **File Not Found**
**Symptoms:**
```
[ERROR] Image file not found: /config/www/gauge.jpg
[DEBUG] Files in directory /config/www: ['other.jpg', 'test.png']
```

**Solutions:**
- Check file path is correct
- Verify file exists and has proper permissions
- Use absolute paths starting with `/config/`

## Testing and Validation

### Step 1: Enable Debug Logging
```yaml
# In Developer Tools → Services
service: image_to_sensor_cv.enable_debug_logging
```

### Step 2: Trigger Processing
```yaml
# In Developer Tools → Services
service: image_to_sensor_cv.process_image
data:
  entity_id: sensor.your_gauge_sensor
```

### Step 3: Check Logs
Go to **Settings** → **System** → **Logs** and look for `image_to_sensor_cv` entries.

### Step 4: Review Debug Images
Navigate to: `http://your-ha-ip:8123/local/image_to_sensor_cv_debug/`

### Step 5: Disable Debug (Optional)
```yaml
service: image_to_sensor_cv.disable_debug_logging
```

## Performance Notes

- Debug logging increases CPU usage and storage
- Debug images are overwritten on each processing cycle
- Disable debug logging in production for better performance
- Debug directory `/config/www/image_to_sensor_cv_debug/` can be safely deleted

## Advanced Debugging

### Manual Testing
You can test the detection with a Python script:
```python
from custom_components.image_to_sensor_cv.image_processing_simple import SimpleAnalogGaugeProcessor
import numpy as np
from PIL import Image

# Load your gauge image
image = Image.open('/config/www/your_gauge.jpg')
image_array = np.array(image)

# Create processor with your config
config = {
    'min_angle_hours': 7,
    'max_angle_hours': 5,
    'min_value': 0,
    'max_value': 100,
    'units': 'psi'
}

processor = SimpleAnalogGaugeProcessor(config)
result = processor.process_image(image_array)
print(f"Detection result: {result}")
```

This guide should help you diagnose and fix most detection issues!