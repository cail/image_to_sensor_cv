#!/usr/bin/env python3
"""
Enhanced Test Case Generator and Validator

This script helps create and validate test cases for the Image to Sensor CV component.
It includes utilities for angle conversion and test case validation.
"""

import json
import math
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class GaugeTestCase:
    """Enhanced test case with validation and conversion utilities."""
    file: str
    start_angle: str  # e.g., "7am", "210deg", "7:00"
    end_angle: str    # e.g., "5am", "150deg", "5:00"
    min_value: float
    max_value: float
    detected_angle: str  # Expected needle position
    expected_value: float
    description: str = ""
    tolerance: float = 0.2  # Acceptable error in final value
    
    def to_degrees(self, angle_str: str) -> float:
        """Convert various angle formats to degrees (clock convention)."""
        angle_str = angle_str.lower().strip()
        
        # Handle degree format: "210deg", "210°"
        if 'deg' in angle_str or '°' in angle_str:
            return float(angle_str.replace('deg', '').replace('°', ''))
        
        # Handle time format: "7am", "7:00", "7"
        if 'am' in angle_str or 'pm' in angle_str:
            hour = float(angle_str.replace('am', '').replace('pm', ''))
        elif ':' in angle_str:
            parts = angle_str.split(':')
            hour = float(parts[0]) + float(parts[1]) / 60
        else:
            hour = float(angle_str)
        
        # Convert hour to clock degrees
        # 12 o'clock = 0°, 3 o'clock = 90°, 6 o'clock = 180°, 9 o'clock = 270°
        degrees = (hour % 12) * 30
        return degrees
    
    def validate(self) -> List[str]:
        """Validate the test case and return any errors."""
        errors = []
        
        try:
            start_deg = self.to_degrees(self.start_angle)
            end_deg = self.to_degrees(self.end_angle)
            detected_deg = self.to_degrees(self.detected_angle)
            
            # Check value ranges
            if self.min_value >= self.max_value:
                errors.append("min_value must be less than max_value")
            
            # Check expected value is in range
            if not (self.min_value <= self.expected_value <= self.max_value):
                errors.append(f"expected_value {self.expected_value} not in range [{self.min_value}, {self.max_value}]")
            
            # Validate needle position makes sense
            if start_deg != end_deg:  # Not a full circle gauge
                # For wrapped ranges (e.g., 210° to 150°), check if detected angle is reasonable
                if start_deg > end_deg:  # Wrapped range
                    if not (detected_deg >= start_deg or detected_deg <= end_deg):
                        errors.append(f"detected_angle {detected_deg}° not in wrapped range [{start_deg}°, {end_deg}°]")
                else:  # Normal range
                    if not (start_deg <= detected_deg <= end_deg):
                        errors.append(f"detected_angle {detected_deg}° not in range [{start_deg}°, {end_deg}°]")
                        
        except ValueError as e:
            errors.append(f"Invalid angle format: {e}")
            
        return errors
    
    def calculate_expected_value(self) -> float:
        """Calculate what the expected value should be based on needle position."""
        start_deg = self.to_degrees(self.start_angle)
        end_deg = self.to_degrees(self.end_angle)
        detected_deg = self.to_degrees(self.detected_angle)
        
        # Handle wrapped ranges
        if start_deg > end_deg:
            if detected_deg >= start_deg:
                angle_normalized = detected_deg - start_deg
            else:
                angle_normalized = (360 - start_deg) + detected_deg
            total_range = (360 - start_deg) + end_deg
        else:
            angle_normalized = detected_deg - start_deg
            total_range = end_deg - start_deg
        
        if total_range == 0:
            return self.min_value
            
        value_range = self.max_value - self.min_value
        return (angle_normalized / total_range) * value_range + self.min_value

class TestCaseBuilder:
    """Helper class to build test cases."""
    
    @staticmethod
    def create_pressure_gauge(file: str, needle_hour: float, pressure_value: float) -> GaugeTestCase:
        """Create a standard pressure gauge test case (7am to 5am, 0-6 bar)."""
        return GaugeTestCase(
            file=file,
            start_angle="7am",
            end_angle="5am", 
            min_value=0.0,
            max_value=6.0,
            detected_angle=f"{needle_hour}am",
            expected_value=pressure_value,
            description=f"Pressure gauge reading {pressure_value} bar at {needle_hour} o'clock"
        )
    
    @staticmethod
    def create_temperature_gauge(file: str, needle_hour: float, temp_value: float) -> GaugeTestCase:
        """Create a standard temperature gauge test case (8am to 4pm, -20 to 50°C)."""
        return GaugeTestCase(
            file=file,
            start_angle="8am",
            end_angle="4pm",
            min_value=-20.0,
            max_value=50.0,
            detected_angle=f"{needle_hour}am" if needle_hour <= 12 else f"{needle_hour-12}pm",
            expected_value=temp_value,
            description=f"Temperature gauge reading {temp_value}°C"
        )
    
    @staticmethod
    def create_fuel_gauge(file: str, needle_hour: float, fuel_percent: float) -> GaugeTestCase:
        """Create a fuel level gauge test case (9am to 3pm, 0-100%)."""
        return GaugeTestCase(
            file=file,
            start_angle="9am",
            end_angle="3pm",
            min_value=0.0,
            max_value=100.0,
            detected_angle=f"{needle_hour}am" if needle_hour <= 12 else f"{needle_hour-12}pm",
            expected_value=fuel_percent,
            description=f"Fuel gauge reading {fuel_percent}%"
        )

def create_sample_test_suite() -> List[GaugeTestCase]:
    """Create a comprehensive test suite with various gauge types."""
    test_cases = []
    
    # Pressure gauges
    test_cases.extend([
        TestCaseBuilder.create_pressure_gauge("pressure-heat-last.jpg", 10, 2.1),
        TestCaseBuilder.create_pressure_gauge("pressure-heat-51.jpg", 9, 1.5),
        TestCaseBuilder.create_pressure_gauge("pressure-water-last.jpg", 11, 3.2),
    ])
    
    # Temperature/other gauges  
    test_cases.extend([
        GaugeTestCase(
            file="kotel-01.jpg",
            start_angle="8am",
            end_angle="4pm", 
            min_value=0,
            max_value=100,
            detected_angle="12pm",
            expected_value=50,
            description="Boiler temperature gauge"
        ),
        GaugeTestCase(
            file="kotel-last.jpg",
            start_angle="8am", 
            end_angle="4pm",
            min_value=0,
            max_value=100,
            detected_angle="2pm",
            expected_value=75,
            description="Boiler temperature gauge - high reading"
        )
    ])
    
    return test_cases

def validate_test_suite(test_cases: List[GaugeTestCase]) -> None:
    """Validate all test cases and report issues."""
    print("🔍 Validating Test Suite")
    print("=" * 50)
    
    all_valid = True
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case.file}")
        errors = test_case.validate()
        
        if errors:
            print(f"  ❌ Validation failed:")
            for error in errors:
                print(f"    - {error}")
            all_valid = False
        else:
            # Calculate and compare expected value
            calculated = test_case.calculate_expected_value()
            diff = abs(calculated - test_case.expected_value)
            
            if diff > test_case.tolerance:
                print(f"  ⚠️  Expected value mismatch:")
                print(f"    - Configured: {test_case.expected_value}")
                print(f"    - Calculated: {calculated:.3f}")
                print(f"    - Difference: {diff:.3f} (tolerance: {test_case.tolerance})")
            else:
                print(f"  ✅ Valid (calculated: {calculated:.3f})")
    
    if all_valid:
        print(f"\n🎉 All {len(test_cases)} test cases are valid!")
    else:
        print(f"\n⚠️  Some test cases have validation issues.")

def export_to_json(test_cases: List[GaugeTestCase], filename: str) -> None:
    """Export test cases to JSON format."""
    # Convert to simple dict format for JSON
    json_data = []
    for tc in test_cases:
        json_data.append({
            "file": tc.file,
            "start_angle": tc.start_angle,
            "end_angle": tc.end_angle,
            "min_value": tc.min_value,
            "max_value": tc.max_value,
            "detected_angle": tc.detected_angle,
            "expected_value": tc.expected_value,
            "description": tc.description,
            "tolerance": tc.tolerance
        })
    
    with open(filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"📄 Test cases exported to {filename}")

if __name__ == "__main__":
    # Create sample test suite
    test_cases = create_sample_test_suite()
    
    # Validate test cases
    validate_test_suite(test_cases)
    
    # Export to JSON
    export_to_json(test_cases, "enhanced_tests.json")
    
    print("\n🎯 Usage:")
    print("1. Review the generated enhanced_tests.json")
    print("2. Modify test cases as needed")
    print("3. Run: python test_runner.py")