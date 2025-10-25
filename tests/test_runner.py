#!/usr/bin/env python3
"""
Standalone Test Runner for Image to Sensor CV Component

This script validates the image processing logic using reference test vectors.
It can run independently of Home Assistant for development and debugging.
"""

import os
import sys
import json
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from dataclasses import dataclass

# Add parent directory to path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import our modules
from image_processing_simple import SimpleAnalogGaugeProcessor
from const import PROCESSOR_ANALOG_GAUGE

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_results.log')
    ]
)
_LOGGER = logging.getLogger(__name__)

@dataclass
class TestCase:
    """Represents a single test case."""
    file: str
    start_angle: str  # e.g., "7am"
    end_angle: str    # e.g., "5am" 
    min_value: float
    max_value: float
    detected_angle: str  # e.g., "10am"
    expected_value: float
    
    def __post_init__(self):
        """Convert clock time strings to degrees."""
        self.start_angle_deg = self._time_to_degrees(self.start_angle)
        self.end_angle_deg = self._time_to_degrees(self.end_angle)
        self.detected_angle_deg = self._time_to_degrees(self.detected_angle)
    
    def _time_to_degrees(self, time_str: str) -> float:
        """Convert time string like '7am' to degrees (clock convention)."""
        # Remove 'am'/'pm' and get hour
        hour_str = time_str.replace('am', '').replace('pm', '').strip()
        hour = float(hour_str)
        
        # Convert hour to degrees (12 o'clock = 0°, 3 o'clock = 90°, etc.)
        # Each hour is 30 degrees (360° / 12 hours)
        degrees = (hour % 12) * 30
        
        # Adjust for clock convention (12 o'clock = 0°)
        if hour == 12:
            degrees = 0
        elif hour == 6:
            degrees = 180
        elif hour == 3 or hour == 15:
            degrees = 90
        elif hour == 9 or hour == 21:
            degrees = 270
        else:
            # General formula: degrees from 12 o'clock position
            degrees = (hour % 12) * 30
        
        return degrees

@dataclass 
class TestResult:
    """Results from a test run."""
    test_case: TestCase
    success: bool
    detected_value: Optional[float]
    angle_error: Optional[float]  # Difference in degrees
    value_error: Optional[float]  # Difference in gauge value
    error_message: Optional[str]
    processing_time: float

class TestRunner:
    """Main test runner class."""
    
    def __init__(self, tests_dir: str):
        self.tests_dir = tests_dir
        self.test_cases: List[TestCase] = []
        self.results: List[TestResult] = []
        
    def load_test_cases(self, json_file: str = "tests.json") -> None:
        """Load test cases from JSON file."""
        json_path = os.path.join(self.tests_dir, json_file)
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Test file not found: {json_path}")
            
        with open(json_path, 'r') as f:
            test_data = json.load(f)
            
        for test_dict in test_data:
            test_case = TestCase(**test_dict)
            self.test_cases.append(test_case)
            
        _LOGGER.info(f"Loaded {len(self.test_cases)} test cases")
        
    def create_processor_config(self, test_case: TestCase) -> Dict[str, Any]:
        """Create processor configuration for a test case."""
        return {
            'image_source': 'file',
            'image_path': os.path.join(self.tests_dir, test_case.file),
            'processor_type': PROCESSOR_ANALOG_GAUGE,
            'crop_x1': 0,
            'crop_y1': 0, 
            'crop_x2': -1,  # Full image
            'crop_y2': -1,  # Full image
            'min_angle': test_case.start_angle_deg,
            'max_angle': test_case.end_angle_deg,
            'min_value': test_case.min_value,
            'max_value': test_case.max_value,
            'units': 'bar'
        }
    
    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case."""
        import time
        start_time = time.time()
        
        _LOGGER.info(f"Running test: {test_case.file}")
        _LOGGER.info(f"  Expected angle: {test_case.detected_angle} ({test_case.detected_angle_deg}°)")
        _LOGGER.info(f"  Expected value: {test_case.expected_value}")
        
        try:
            # Create processor
            config = self.create_processor_config(test_case)
            processor = SimpleAnalogGaugeProcessor(config, f"test_{test_case.file}")
            
            # Process the image
            result = await processor.process_image()
            
            processing_time = time.time() - start_time
            
            if result is None:
                return TestResult(
                    test_case=test_case,
                    success=False,
                    detected_value=None,
                    angle_error=None,
                    value_error=None,
                    error_message="Processing returned None",
                    processing_time=processing_time
                )
                
            # Calculate errors
            value_error = abs(result - test_case.expected_value)
            
            # For angle error, we need to extract the detected angle from logs
            # This is a simplified approach - in a real test we might return more info
            angle_error = None  # We'll calculate this if needed
            
            # Determine success (tolerance-based)
            value_tolerance = 0.2  # Allow 0.2 units difference
            success = value_error <= value_tolerance
            
            return TestResult(
                test_case=test_case,
                success=success,
                detected_value=result,
                angle_error=angle_error,
                value_error=value_error,
                error_message=None if success else f"Value error {value_error:.3f} > tolerance {value_tolerance}",
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return TestResult(
                test_case=test_case,
                success=False,
                detected_value=None,
                angle_error=None,
                value_error=None,
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def run_all_tests(self) -> None:
        """Run all test cases."""
        _LOGGER.info("=" * 60)
        _LOGGER.info("🧪 STARTING IMAGE PROCESSING TESTS")
        _LOGGER.info("=" * 60)
        
        for i, test_case in enumerate(self.test_cases, 1):
            _LOGGER.info(f"\n📋 Test {i}/{len(self.test_cases)}: {test_case.file}")
            result = await self.run_single_test(test_case)
            self.results.append(result)
            
            # Log result
            if result.success:
                _LOGGER.info(f"✅ PASS - Value: {result.detected_value:.3f} (expected: {test_case.expected_value})")
            else:
                _LOGGER.error(f"❌ FAIL - {result.error_message}")
                if result.detected_value is not None:
                    _LOGGER.error(f"   Detected: {result.detected_value:.3f}, Expected: {test_case.expected_value}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        if not self.results:
            return "No test results available."
            
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        
        report = []
        report.append("=" * 80)
        report.append("🧪 IMAGE PROCESSING TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total Tests: {len(self.results)}")
        report.append(f"Passed: {passed} ✅")
        report.append(f"Failed: {failed} ❌")
        report.append(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        report.append("")
        
        # Detailed results
        report.append("📊 DETAILED RESULTS:")
        report.append("-" * 80)
        
        for i, result in enumerate(self.results, 1):
            tc = result.test_case
            status = "✅ PASS" if result.success else "❌ FAIL"
            
            report.append(f"Test {i}: {tc.file} - {status}")
            report.append(f"  Image: {tc.file}")
            report.append(f"  Range: {tc.start_angle} to {tc.end_angle} ({tc.start_angle_deg}° to {tc.end_angle_deg}°)")
            report.append(f"  Values: {tc.min_value} to {tc.max_value}")
            report.append(f"  Expected: {tc.detected_angle} → {tc.expected_value}")
            
            if result.detected_value is not None:
                report.append(f"  Detected: {result.detected_value:.3f}")
                report.append(f"  Error: {result.value_error:.3f}")
            else:
                report.append(f"  Error: {result.error_message}")
                
            report.append(f"  Time: {result.processing_time:.2f}s")
            report.append("")
        
        # Summary statistics
        if self.results:
            successful_results = [r for r in self.results if r.success and r.detected_value is not None]
            if successful_results:
                avg_error = sum(r.value_error for r in successful_results) / len(successful_results)
                max_error = max(r.value_error for r in successful_results)
                avg_time = sum(r.processing_time for r in self.results) / len(self.results)
                
                report.append("📈 STATISTICS:")
                report.append(f"  Average Value Error: {avg_error:.3f}")
                report.append(f"  Maximum Value Error: {max_error:.3f}")
                report.append(f"  Average Processing Time: {avg_time:.2f}s")
        
        return "\n".join(report)
    
    def save_report(self, filename: str = "test_report.txt") -> None:
        """Save the test report to a file."""
        report = self.generate_report()
        report_path = os.path.join(self.tests_dir, filename)
        
        with open(report_path, 'w') as f:
            f.write(report)
            
        _LOGGER.info(f"Test report saved to: {report_path}")

async def main():
    """Main function to run the tests."""
    # Get the tests directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Create test runner
        runner = TestRunner(current_dir)
        
        # Load test cases
        runner.load_test_cases()
        
        # Run all tests
        await runner.run_all_tests()
        
        # Generate and display report
        report = runner.generate_report()
        print("\n" + report)
        
        # Save report
        runner.save_report()
        
        # Summary
        passed = sum(1 for r in runner.results if r.success)
        total = len(runner.results)
        
        if passed == total:
            print(f"\n🎉 All {total} tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} out of {total} tests failed.")
            return 1
            
    except Exception as e:
        _LOGGER.error(f"Test execution failed: {e}")
        import traceback
        _LOGGER.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)