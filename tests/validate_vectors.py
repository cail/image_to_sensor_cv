#!/usr/bin/env python3
"""
Quick Test Vector Validator

Validates your current test vectors and shows the math.
Also validates SimpleAnalogGaugeProcessor results against expected values.
"""

import json
import math
import os
import sys
import numpy as np
from PIL import Image
from typing import Optional
from unittest.mock import MagicMock

# Set up paths FIRST
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
grandparent_dir = os.path.dirname(parent_dir)

# Add grandparent to path so we can import the package
sys.path.insert(0, grandparent_dir)

# Mock Home Assistant packages BEFORE any imports from your package
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.typing'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()

sys.modules['voluptuous'] = MagicMock()


DEBUG = 0

# Mock Home Assistant dependencies for standalone testing
class MockLogger:
    def debug(self, msg, *args, **kwargs):
        if DEBUG and args:
            print(f"DEBUG: {msg % args}")
        elif DEBUG:
            print(f"DEBUG: {msg}")
    
    def warning(self, msg, *args, **kwargs):
        if args:
            print(f"WARNING: {msg % args}")
        else:
            print(f"WARNING: {msg}")
    
    def error(self, msg, *args, **kwargs):
        if args:
            print(f"ERROR: {msg % args}")
        else:
            print(f"ERROR: {msg}")
    
    def info(self, msg, *args, **kwargs):
        if DEBUG and args:
            print(f"INFO: {msg % args}")
        elif DEBUG:
            print(f"INFO: {msg}")
    
    def isEnabledFor(self, level):
        return DEBUG > 0

class MockHomeAssistant:
    pass

# NOW we can import from the package
try:
    from image_to_sensor_cv.image_processing_simple import SimpleAnalogGaugeProcessor
    # Replace the module-level logger with our mock
    from image_to_sensor_cv import image_processing_simple
    image_processing_simple._LOGGER = MockLogger()
    PROCESSOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Could not import SimpleAnalogGaugeProcessor: {e}")
    print("   Processor validation will be skipped.")
    import traceback
    traceback.print_exc()
    PROCESSOR_AVAILABLE = False

try:
    from image_to_sensor_cv import debug_utils
    debug_utils.set_debug_directory("./image_to_sensor_cv_debug")
except ImportError as e:
    print(f"⚠️  Warning: Could not import debug_utils: {e}")

def time_to_degrees(time_str) -> float:

    hour = float(time_str)

    # Convert hour to clock degrees (12 o'clock = 0°)
    # Each hour is 30 degrees (360° / 12 hours)
    if hour == 12:
        degrees = 0  # 12 o'clock = 0°
    else:
        degrees = (hour % 12) * 30
    
    return degrees

def load_test_image(image_path: str) -> Optional[np.ndarray]:
    """Load a test image and convert to numpy array."""
    try:
        if not os.path.exists(image_path):
            print(f"   ⚠️  Image not found: {image_path}")
            return None
        
        pil_image = Image.open(image_path)
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        return image_array
    except Exception as e:
        print(f"   ❌ Error loading image: {e}")
        return None

def process_with_gauge_processor(test_case: dict, image_path: str) -> Optional[dict]:
    """Process image with SimpleAnalogGaugeProcessor and return results."""
    if not PROCESSOR_AVAILABLE:
        return None
    
    try:
        # Load the image
        image_array = load_test_image(image_path)
        if image_array is None:
            return None
        
        # Create processor config from test case
        config = {}
        # merge values from test_case into config
        config.update(test_case)

        config.update({
            'min_angle_hours': test_case['start_angle'],
            'max_angle_hours': test_case['end_angle'],
            'min_value': test_case['min_value'],
            'max_value': test_case['max_value'],
            'units': test_case.get('units', '')
        })
        
        # Create and run processor
        processor = SimpleAnalogGaugeProcessor(config, sensor_name=test_case['file'])
        detected_value = processor.process_image(image_array)
        
        if detected_value is None:
            return {
                'success': False,
                'error': 'Processor returned None'
            }
        
        # Calculate error vs expected value
        expected_value = test_case['expected_value']
        error = abs(detected_value - expected_value)
        value_range = test_case['max_value'] - test_case['min_value']
        error_percent = (error / value_range) * 100 if value_range != 0 else 0
        
        return {
            'success': True,
            'detected_value': detected_value,
            'expected_value': expected_value,
            'error': error,
            'error_percent': error_percent,
            'config': config
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


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
            'message': 'OK' if error_percent < 5 else f'High error: {error:.3f}'
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
    
    if PROCESSOR_AVAILABLE:
        print("✅ SimpleAnalogGaugeProcessor available - will test actual image processing")
    else:
        print("⚠️  SimpleAnalogGaugeProcessor not available - only validating math")
    
    # Load current test file
    testcases = 'tests/tests.json'
    if os.path.exists(testcases):
        with open(testcases, 'r') as f:
            test_data = json.load(f)
    else:
        print("❌ tests.json not found!")
        return
    
    processor_results = []
    
    for i, test_case in enumerate(test_data, 1):
        print(f"\n📋 Test {i}: {test_case['file']}")
        print("-" * 40)
        
        result = validate_test_vector(test_case)
        
        if not result['valid']:
            print(f"❌ Invalid: {result['error_message']}")
            continue
        
        # Display angle analysis
        print(f"📐 Angle Analysis:")
        print(f"  Start: {test_case['start_angle']} = {result['start_deg']}°")
        print(f"  End: {test_case['end_angle']} = {result['end_deg']}°")
        print(f"  Detected: {test_case['detected_angle']} = {result['detected_deg']}°")
        print(f"  Normalized angle: {result['angle_normalized']:.1f}°")
        print(f"  Total range: {result['total_range']:.1f}°")
        
        print(f"\n📊 Value Analysis (Math Validation):")
        print(f"  Range: {test_case['min_value']} to {test_case['max_value']}")
        print(f"  Expected: {result['expected_value']}")
        print(f"  Calculated: {result['calculated_value']:.3f}")
        print(f"  Error: {result['error']:.3f} ({result['error_percent']:.1f}%)")
        
        if result['error_percent'] < 3:
            print(f"  ✅ {result['message']}")
        elif result['error_percent'] < 5:
            print(f"  ⚠️  {result['message']}")
        else:
            print(f"  ❌ {result['message']}")
        
        # Test with actual processor if available
        if PROCESSOR_AVAILABLE:
            image_path = test_case['file']
            if not os.path.isabs(image_path):
                image_path = os.path.join(os.path.dirname(__file__), image_path)
            
            print(f"\n🔬 Processor Test (Actual Image Processing):")
            processor_result = process_with_gauge_processor(test_case, image_path)
            
            if processor_result and processor_result['success']:
                print(f"  Detected Value: {processor_result['detected_value']:.3f}")
                print(f"  Expected Value: {processor_result['expected_value']}")
                print(f"  Error: {processor_result['error']:.3f} ({processor_result['error_percent']:.1f}%)")
                
                if processor_result['error_percent'] < 5:
                    print(f"  ✅ Processor detection accurate!")
                    processor_results.append({'test': i, 'status': 'pass', 'error': processor_result['error']})
                elif processor_result['error_percent'] < 10:
                    print(f"  ⚠️  Processor detection acceptable but could be improved")
                    processor_results.append({'test': i, 'status': 'warning', 'error': processor_result['error']})
                else:
                    print(f"  ❌ Processor detection error too high!")
                    processor_results.append({'test': i, 'status': 'fail', 'error': processor_result['error']})
            else:
                error_msg = processor_result.get('error', 'Unknown error') if processor_result else 'No result'
                print(f"  ❌ Processor failed: {error_msg}")
                processor_results.append({'test': i, 'status': 'error', 'error': error_msg})
    
    # Summary
    print(f"\n{'=' * 50}")
    print(f"🎯 Summary:")
    print(f"Validated {len(test_data)} test cases")
    
    if PROCESSOR_AVAILABLE and processor_results:
        print(f"\n🔬 Processor Results:")
        passed = sum(1 for r in processor_results if r['status'] == 'pass')
        warned = sum(1 for r in processor_results if r['status'] == 'warning')
        failed = sum(1 for r in processor_results if r['status'] == 'fail')
        errors = sum(1 for r in processor_results if r['status'] == 'error')
        
        print(f"  ✅ Passed: {passed}/{len(processor_results)}")
        if warned > 0:
            print(f"  ⚠️  Warnings: {warned}/{len(processor_results)}")
        if failed > 0:
            print(f"  ❌ Failed: {failed}/{len(processor_results)}")
        if errors > 0:
            print(f"  ❌ Errors: {errors}/{len(processor_results)}")
        
        # Calculate average error for successful detections
        successful_errors = [r['error'] for r in processor_results if r['status'] in ['pass', 'warning'] and isinstance(r['error'], (int, float))]
        if successful_errors:
            avg_error = sum(successful_errors) / len(successful_errors)
            print(f"\n  Average error (successful detections): {avg_error:.3f}")


if __name__ == "__main__":
    main()