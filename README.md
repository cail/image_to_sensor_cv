# Image to Sensor CV - Home Assistant Custom Component

A Home Assistant custom component that uses computer vision to analyze images and extract sensor data. Currently supports analog gauge reading with extensible processor architecture.

## Features

- **Multiple Image Sources**: Support for local image files and Home Assistant camera entities
- **Image Cropping**: Configurable cropping to focus on specific areas of the image
- **Extensible Processors**: Modular architecture for different types of image analysis
- **Analog Gauge Reader**: Built-in processor for reading analog gauge values using OpenCV

## Installation

1. Copy the `image_to_sensor_cv` folder to your `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "Add Integration" and search for "Image to Sensor CV"

## Configuration

### Image Source
Choose between:
- **Local Image File**: Path to an image file on the Home Assistant server
- **Home Assistant Camera**: Any camera entity in your Home Assistant instance

### Image Cropping (Optional)
Configure cropping parameters to focus on a specific area:
- **X Position**: Horizontal offset in pixels
- **Y Position**: Vertical offset in pixels
- **Width**: Crop width in pixels
- **Height**: Crop height in pixels

### Analog Gauge Reader Processor
Configure the analog gauge reader with these parameters:

- **Min Angle (Hours)**: The minimum angle of the gauge dial in clock hours (0-12)
  - Example: 7 o'clock position = 7
- **Max Angle (Hours)**: The maximum angle of the gauge dial in clock hours (0-12)
  - Example: 5 o'clock position = 5
- **Min Value**: Minimum reading value of the gauge
- **Max Value**: Maximum reading value of the gauge
- **Units**: Optional unit of measurement (e.g., "psi", "°C", "rpm")

## How the Analog Gauge Reader Works

The analog gauge reader is based on computer vision techniques:

1. **Circle Detection**: Uses Hough Circle Transform to detect the circular gauge
2. **Needle Detection**: Applies thresholding and line detection to find the needle
3. **Angle Calculation**: Calculates the needle angle relative to the gauge center
4. **Value Mapping**: Maps the angle to the configured value range

### Gauge Requirements

For best results, your analog gauge should:
- Be clearly visible and well-lit
- Have good contrast between needle and background
- Be roughly circular in shape
- Have the needle clearly distinguishable

## Troubleshooting

### Common Issues

1. **No circles detected**: 
   - Ensure the gauge is circular and well-lit
   - Try adjusting image cropping to focus on the gauge
   - Check if the image quality is sufficient

2. **No needle detected**:
   - Verify the needle has good contrast against the background
   - Ensure the needle is not too thin or blurry
   - Check that the gauge face is not too cluttered

3. **Incorrect readings**:
   - Verify the min/max angle configuration matches your gauge
   - Check that the min/max value configuration is correct
   - Ensure the needle is the only prominent line in the gauge area

### Debug Information

The sensor provides additional attributes:
- `processor_type`: Type of processor used
- `processor_config`: Current processor configuration
- `last_reading_time`: Timestamp of last successful reading
- `last_error`: Error message if processing failed

## Technical Details

### Dependencies
- OpenCV Python (`opencv-python>=4.5.0`)
- NumPy (`numpy>=1.20.0`)
- Pillow (`pillow>=9.0.0`)

### Architecture
The component uses a modular architecture:
- **ImageProcessor**: Handles image acquisition and cropping
- **Processor Classes**: Implement specific analysis algorithms
- **Sensor Entity**: Provides Home Assistant integration
- **Data Coordinator**: Manages periodic updates

## Future Enhancements

Planned processor types:
- Digital display OCR reader
- Object detection and counting
- Color analysis
- Motion detection
- Custom template matching

## Contributing

This component is designed to be extensible. To add new processors:

1. Create a new processor class in `image_processing.py`
2. Implement the `process_image()` method
3. Add configuration options to the config flow
4. Register the processor in the `create_processor()` function

## License

This project is licensed under the MIT License.

## Credits

The analog gauge reading algorithm is adapted from various computer vision examples and optimized for Home Assistant integration.