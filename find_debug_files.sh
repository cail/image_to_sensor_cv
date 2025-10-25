#!/bin/bash

# Debug file finder for Image to Sensor CV
# This script helps you locate debug files for your sensors

DEBUG_DIR="/config/www/image_to_sensor_cv_debug"

echo "🔍 Image to Sensor CV Debug File Finder"
echo "========================================"

if [ ! -d "$DEBUG_DIR" ]; then
    echo "❌ Debug directory not found: $DEBUG_DIR"
    echo "   Make sure you have:"
    echo "   1. Enabled debug logging"
    echo "   2. Triggered at least one image processing cycle"
    exit 1
fi

echo "📁 Debug directory: $DEBUG_DIR"
echo ""

# Count total files
TOTAL_FILES=$(find "$DEBUG_DIR" -name "*.png" | wc -l)
echo "📊 Total debug images: $TOTAL_FILES"
echo ""

if [ $TOTAL_FILES -eq 0 ]; then
    echo "❌ No debug images found."
    echo "   To generate debug images:"
    echo "   1. Enable debug logging: image_to_sensor_cv.enable_debug_logging"
    echo "   2. Process an image: image_to_sensor_cv.process_image"
    exit 1
fi

# Group files by sensor
echo "🏷️  Debug images by sensor:"
echo ""

# Extract unique sensor names from filenames
SENSOR_NAMES=$(find "$DEBUG_DIR" -name "*.png" -exec basename {} \; | sed 's/_[^_]*_[^_]*\.png$//' | sort | uniq)

for SENSOR in $SENSOR_NAMES; do
    echo "📸 Sensor: $SENSOR"
    
    # Find files for this sensor
    FILES=$(find "$DEBUG_DIR" -name "${SENSOR}_*.png" | sort)
    
    for FILE in $FILES; do
        BASENAME=$(basename "$FILE")
        FILESIZE=$(ls -lh "$FILE" | awk '{print $5}')
        TIMESTAMP=$(ls -l "$FILE" | awk '{print $6, $7, $8}')
        
        # Determine file type from name
        if [[ $BASENAME == *"_loaded_original.png" ]]; then
            TYPE="🖼️  Original Image"
        elif [[ $BASENAME == *"_processed_cropped.png" ]]; then
            TYPE="✂️  Cropped Image"
        elif [[ $BASENAME == *"_grayscale_gauge_processed.png" ]]; then
            TYPE="⚫ Grayscale Processed"
        elif [[ $BASENAME == *"_overlay_gauge_detection.png" ]]; then
            TYPE="🎯 Detection Overlay"
        else
            TYPE="📄 Debug Image"
        fi
        
        echo "   $TYPE"
        echo "      File: $BASENAME"
        echo "      Size: $FILESIZE | Modified: $TIMESTAMP"
        echo ""
    done
    echo "   🌐 View online: http://your-ha-ip:8123/local/image_to_sensor_cv_debug/"
    echo ""
done

echo "💡 Tips:"
echo "   - Images are overwritten on each processing cycle"
echo "   - Use 'image_to_sensor_cv.disable_debug_logging' to stop generating debug images"
echo "   - Delete old images: rm $DEBUG_DIR/*.png"