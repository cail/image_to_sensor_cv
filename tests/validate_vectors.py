#!/usr/bin/env python3
"""
Quick Test Vector Validator

Validates your current test vectors and shows the math.
"""

import json
import math
import os

def time_to_degrees(time_str: str) -> float:
    """Convert time string like '7am' to degrees (clock convention)."""
    time_str = time_str.lower().strip()
    
    # Handle degree format
    if 'deg' in time_str or '°' in time_str:
        return float(time_str.replace('deg', '').replace('°', ''))
    
    # Handle time format
    if 'am' in time_str or 'pm' in time_str:
        hour = float(time_str.replace('am', '').replace('pm', ''))
    else:
        hour = float(time_str)
    
    # Convert hour to clock degrees (12 o'clock = 0°)
    # Each hour is 30 degrees (360° / 12 hours)
    if hour == 12:
        degrees = 0  # 12 o'clock = 0°
    else:
        degrees = (hour % 12) * 30
    
    return degrees

def validate_test_vector(test_case: dict) -> dict:
    """Validate a single test case and return analysis."""
    try:
        # Convert angles
        start_deg = time_to_degrees(test_case['start_angle'])
        end_deg = time_to_degrees(test_case['end_angle'])
        detected_deg = time_to_degrees(test_case['detected_angle'])
        
        min_val = test_case['min_value']
        max_val = test_case['max_value']
        expected_val = test_case['expected_value']
        
        # Calculate what the value should be
        # Handle wrapped ranges (like 7am to 5am = 210° to 150°)
        if start_deg > end_deg:  # Wrapped range
            if detected_deg >= start_deg:
                angle_normalized = detected_deg - start_deg
            else:
                angle_normalized = (360 - start_deg) + detected_deg
            total_range = (360 - start_deg) + end_deg
        else:  # Normal range
            angle_normalized = detected_deg - start_deg
            total_range = end_deg - start_deg
        
        if total_range == 0:
            calculated_value = min_val
        else:
            value_range = max_val - min_val
            calculated_value = (angle_normalized / total_range) * value_range + min_val
        
        # Calculate error
        error = abs(calculated_value - expected_val)
        error_percent = (error / (max_val - min_val)) * 100 if max_val != min_val else 0
        
        return {
            'valid': True,
            'start_deg': start_deg,
            'end_deg': end_deg,
            'detected_deg': detected_deg,
            'angle_normalized': angle_normalized,
            'total_range': total_range,
            'calculated_value': calculated_value,
            'expected_value': expected_val,
            'error': error,
            'error_percent': error_percent,
            'message': 'OK' if error < 0.2 else f'High error: {error:.3f}'
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error_message': str(e)
        }

def main():
    """Main validation function."""
    print("🔍 Test Vector Validator")
    print("=" * 50)
    
    # Load current test file
    if os.path.exists('tests.json'):
        with open('tests.json', 'r') as f:
            test_data = json.load(f)
    else:
        print("❌ tests.json not found!")
        return
    
    for i, test_case in enumerate(test_data, 1):
        print(f"\n📋 Test {i}: {test_case['file']}")
        print("-" * 40)
        
        result = validate_test_vector(test_case)
        
        if not result['valid']:
            print(f"❌ Invalid: {result['error_message']}")
            continue
        
        # Display analysis
        print(f"📐 Angle Analysis:")
        print(f"  Start: {test_case['start_angle']} = {result['start_deg']}°")
        print(f"  End: {test_case['end_angle']} = {result['end_deg']}°")
        print(f"  Detected: {test_case['detected_angle']} = {result['detected_deg']}°")
        print(f"  Normalized angle: {result['angle_normalized']:.1f}°")
        print(f"  Total range: {result['total_range']:.1f}°")
        
        print(f"\n📊 Value Analysis:")
        print(f"  Range: {test_case['min_value']} to {test_case['max_value']}")
        print(f"  Expected: {result['expected_value']}")
        print(f"  Calculated: {result['calculated_value']:.3f}")
        print(f"  Error: {result['error']:.3f} ({result['error_percent']:.1f}%)")
        
        if result['error'] < 0.1:
            print(f"  ✅ {result['message']}")
        elif result['error'] < 0.2:
            print(f"  ⚠️  {result['message']}")
        else:
            print(f"  ❌ {result['message']}")
    
    print(f"\n🎯 Summary:")
    print(f"Validated {len(test_data)} test cases")

if __name__ == "__main__":
    main()