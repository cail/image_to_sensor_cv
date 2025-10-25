#!/usr/bin/env python3
"""
Test Case Correction Tool

Helps determine the correct needle position or expected value.
"""

def find_needle_position_for_value(start_deg: float, end_deg: float, min_val: float, max_val: float, target_value: float) -> float:
    """Find what needle position would give the target value."""
    
    # Calculate total sweep
    if start_deg > end_deg:  # Wrapped gauge
        total_sweep = (360 - start_deg) + end_deg
    else:
        total_sweep = end_deg - start_deg
    
    # Calculate required progress
    progress = (target_value - min_val) / (max_val - min_val)
    
    # Calculate required angle offset
    angle_offset = progress * total_sweep
    
    # Calculate actual needle position
    if start_deg > end_deg:  # Wrapped gauge
        if angle_offset <= (360 - start_deg):
            needle_deg = start_deg + angle_offset
        else:
            needle_deg = angle_offset - (360 - start_deg)
    else:
        needle_deg = start_deg + angle_offset
    
    return needle_deg

def degrees_to_clock_time(deg: float) -> str:
    """Convert degrees to clock time string."""
    hour = deg / 30
    if hour == 0:
        return "12am"
    elif hour <= 12:
        return f"{int(hour)}am"
    else:
        return f"{int(hour-12)}pm"

def main():
    print("🔧 Test Case Correction Tool")
    print("=" * 40)
    
    # Your current test case
    start_deg = 210  # 7am
    end_deg = 150    # 5am  
    min_val = 0
    max_val = 6
    target_value = 2.1
    
    print(f"Gauge: {start_deg}° to {end_deg}° (7am to 5am)")
    print(f"Range: {min_val} to {max_val}")
    print(f"Target value: {target_value}")
    print()
    
    # Find correct needle position for target value
    correct_needle_deg = find_needle_position_for_value(start_deg, end_deg, min_val, max_val, target_value)
    correct_time = degrees_to_clock_time(correct_needle_deg)
    
    print(f"🎯 For value {target_value}:")
    print(f"  Needle should be at: {correct_needle_deg:.1f}° ({correct_time})")
    
    # Also show what 10am (300°) should give
    detected_deg = 300  # 10am
    
    # Calculate value for 10am position
    if start_deg > end_deg:  # Wrapped
        if detected_deg >= start_deg:
            needle_offset = detected_deg - start_deg
        else:
            needle_offset = (360 - start_deg) + detected_deg
        total_sweep = (360 - start_deg) + end_deg
    else:
        needle_offset = detected_deg - start_deg
        total_sweep = end_deg - start_deg
    
    progress = needle_offset / total_sweep
    calculated_value = min_val + progress * (max_val - min_val)
    
    print(f"\n📐 For needle at 10am (300°):")
    print(f"  Calculated value: {calculated_value:.3f}")
    
    print(f"\n🔍 Recommendations:")
    print(f"  Option 1: Change detected_angle to '{correct_time}' (keep expected_value = 2.1)")
    print(f"  Option 2: Change expected_value to {calculated_value:.1f} (keep detected_angle = '10am')")

if __name__ == "__main__":
    main()