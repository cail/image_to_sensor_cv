"""
Angle Conversion Test for Image to Sensor CV

This script helps validate that angle calculations are working correctly.
It shows the relationship between different coordinate systems used.
"""

import math

def test_angle_conversions():
    """Test angle conversions between coordinate systems."""
    
    print("🧮 Angle Conversion Test")
    print("=" * 50)
    
    print("\n📐 Coordinate System Conventions:")
    print("Mathematical (used in detection):")
    print("  0° = Right (3 o'clock)")
    print("  90° = Up (12 o'clock)")  
    print("  180° = Left (9 o'clock)")
    print("  270° = Down (6 o'clock)")
    
    print("\nClock (used for gauge configuration):")
    print("  0° = Up (12 o'clock)")
    print("  90° = Right (3 o'clock)")
    print("  180° = Down (6 o'clock)")
    print("  270° = Left (9 o'clock)")
    
    print("\n🔄 Conversion Formula:")
    print("  clock_angle = (90 - math_angle) % 360")
    
    print("\n📊 Test Cases:")
    print("Math°  | Clock° | Clock Position")
    print("-------|--------|---------------")
    
    test_angles = [0, 30, 45, 90, 135, 180, 225, 270, 315]
    
    for math_angle in test_angles:
        clock_angle = (90 - math_angle) % 360
        
        # Convert to clock position
        hour = clock_angle / 30
        if hour == 0:
            position = "12:00"
        elif hour == int(hour):
            position = f"{int(hour)}:00"
        else:
            minutes = int((hour - int(hour)) * 60)
            position = f"{int(hour)}:{minutes:02d}"
            
        print(f"{math_angle:4d}°  | {clock_angle:5.0f}° | {position}")
    
    print("\n🎯 Common Gauge Configurations:")
    
    configs = [
        {"name": "Pressure Gauge", "min_hours": 7, "max_hours": 5, "min_val": 0, "max_val": 100},
        {"name": "Temperature", "min_hours": 8, "max_hours": 4, "min_val": -20, "max_val": 50},
        {"name": "Fuel Level", "min_hours": 9, "max_hours": 3, "min_val": 0, "max_val": 1},
    ]
    
    for config in configs:
        print(f"\n{config['name']}:")
        print(f"  Range: {config['min_hours']}:00 to {config['max_hours']}:00")
        print(f"  Angles: {config['min_hours']*30}° to {config['max_hours']*30}° (clock)")
        print(f"  Values: {config['min_val']} to {config['max_val']}")
        
        # Test a few needle positions
        test_positions = [
            (config['min_hours'] * 30, config['min_val']),
            (config['max_hours'] * 30, config['max_val']),
            ((config['min_hours'] + config['max_hours']) * 15, (config['min_val'] + config['max_val']) / 2)
        ]
        
        for clock_deg, expected_val in test_positions:
            # Convert clock to math angle for detection
            math_deg = (90 - clock_deg) % 360
            print(f"    {clock_deg}° clock = {math_deg}° math → should read ~{expected_val}")

def test_coordinate_system():
    """Test image coordinate system vs math coordinate system."""
    
    print("\n🖼️  Image Coordinate System Test")
    print("=" * 40)
    
    # Simulate image center
    cx, cy = 100, 100
    radius = 50
    
    print(f"Image center: ({cx}, {cy})")
    print(f"Test radius: {radius}")
    print("\nAngle | Math Coords | Image Coords | Clock Position")
    print("------|-------------|--------------|---------------")
    
    for angle_deg in [0, 90, 180, 270]:
        angle_rad = math.radians(angle_deg)
        
        # Mathematical coordinates (standard)
        math_x = cx + radius * math.cos(angle_rad)
        math_y = cy + radius * math.sin(angle_rad)
        
        # Image coordinates (Y-axis flipped)
        img_x = cx + radius * math.cos(angle_rad)
        img_y = cy - radius * math.sin(angle_rad)  # Flip Y
        
        # Clock position
        clock_angle = (90 - angle_deg) % 360
        hour = clock_angle / 30
        if hour == 0:
            hour = 12
        
        print(f"{angle_deg:4d}° | ({math_x:5.0f},{math_y:5.0f}) | ({img_x:5.0f},{img_y:5.0f})  | {hour:2.0f}:00")

if __name__ == "__main__":
    test_angle_conversions()
    test_coordinate_system()
    
    print("\n✅ Test complete!")
    print("\n💡 Key Points:")
    print("1. Detection uses mathematical angles (0°=right)")
    print("2. Gauge config uses clock angles (0°=up)")
    print("3. Image Y-axis is flipped (0,0 at top-left)")
    print("4. Conversion: clock = (90 - math) % 360")
    print("5. Image Y: y = center_y - radius * sin(angle)")