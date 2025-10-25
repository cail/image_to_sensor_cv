#!/bin/bash
# Quick test script to check Home Assistant logs for image_to_sensor_cv issues

echo "🔍 Checking Home Assistant logs for image_to_sensor_cv issues..."

# Check for errors related to our component
docker logs homeassistant 2>&1 | grep -i "image_to_sensor_cv" | tail -10

echo ""
echo "🔍 Checking for any recent errors or warnings..."

# Check for recent errors
docker logs homeassistant 2>&1 | grep -E "(ERROR|WARNING|Exception)" | tail -10

echo ""
echo "✅ Log check complete!"