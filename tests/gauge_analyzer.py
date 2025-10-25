#!/usr/bin/env python3
"""
Gauge Analysis Tool

Helps visualize and understand gauge configurations.
"""

import math

def draw_gauge_diagram(start_angle: str, end_angle: str, detected_angle: str, min_val: float, max_val: float):
    """Draw ASCII art gauge diagram."""
    
    def time_to_degrees(time_str: str) -> float:
        hour = float(time_str.replace('am', '').replace('pm', ''))
        if hour == 12:
            return 0
        return (hour % 12) * 30
    
    start_deg = time_to_degrees(start_angle)
    end_deg = time_to_degrees(end_angle)
    detected_deg = time_to_degrees(detected_angle)
    
    print(f"🎯 Gauge Configuration Analysis")
    print(f"=" * 50)
    print(f"Range: {start_angle} ({start_deg}°) to {end_angle} ({end_deg}°)")
    print(f"Values: {min_val} to {max_val}")
    print(f"Needle at: {detected_angle} ({detected_deg}°)")
    print()
    
    # ASCII gauge representation
    print("     12 (0°)")
    print("      |")
    print("  9 --+-- 3")
    print("   (270°) (90°)")
    print("      |")
    print("     6 (180°)")
    print()
    
    # Show positions
    positions = {
        0: "12", 30: "1", 60: "2", 90: "3", 120: "4", 150: "5",
        180: "6", 210: "7", 240: "8", 270: "9", 300: "10", 330: "11"
    }
    
    print("Gauge positions:")
    print(f"  Start: {start_deg}° = {positions.get(start_deg, '?')} o'clock")
    print(f"  End: {end_deg}° = {positions.get(end_deg, '?')} o'clock") 
    print(f"  Needle: {detected_deg}° = {positions.get(detected_deg, '?')} o'clock")
    print()
    
    # Calculate expected value manually
    if start_deg > end_deg:  # Wrapped gauge (e.g., 7am to 5am)
        print("🔄 Wrapped gauge (crosses 12 o'clock)")
        
        # For 7am to 5am: 210° to 150°
        # Total sweep = (360 - 210) + 150 = 150 + 150 = 300°
        total_sweep = (360 - start_deg) + end_deg
        
        # Where is needle relative to start?
        if detected_deg >= start_deg:
            needle_offset = detected_deg - start_deg
        else:
            needle_offset = (360 - start_deg) + detected_deg
            
        print(f"  Total sweep: {total_sweep}°")
        print(f"  Needle offset from start: {needle_offset}°")
        
        # Calculate value
        progress = needle_offset / total_sweep
        value = min_val + progress * (max_val - min_val)
        
        print(f"  Progress: {progress:.3f} ({progress*100:.1f}%)")
        print(f"  Calculated value: {value:.3f}")
        
    else:  # Normal gauge
        print("📏 Normal gauge")
        total_sweep = end_deg - start_deg
        needle_offset = detected_deg - start_deg
        
        print(f"  Total sweep: {total_sweep}°")
        print(f"  Needle offset: {needle_offset}°")
        
        progress = needle_offset / total_sweep if total_sweep > 0 else 0
        value = min_val + progress * (max_val - min_val)
        
        print(f"  Progress: {progress:.3f} ({progress*100:.1f}%)")
        print(f"  Calculated value: {value:.3f}")

if __name__ == "__main__":
    # Analyze your test case
    print("Analyzing your test case:")
    draw_gauge_diagram("7am", "5am", "10am", 0, 6)
    
    print("\n" + "="*50)
    print("🤔 Let's double-check this calculation:")
    print()
    print("For a gauge from 7 o'clock to 5 o'clock:")
    print("- 7 o'clock = 210°")
    print("- 5 o'clock = 150°") 
    print("- 10 o'clock = 300°")
    print()
    print("This gauge sweeps:")
    print("- From 210° clockwise to 360° (150° sweep)")
    print("- Then from 0° to 150° (150° sweep)")
    print("- Total: 300° sweep")
    print()
    print("Needle at 300° (10 o'clock):")
    print("- From start (210°): 300° - 210° = 90°")
    print("- Progress: 90° / 300° = 0.3 = 30%")
    print("- Value: 0 + 0.3 × (6 - 0) = 1.8")
    print()
    print("🎯 So if needle is at 10 o'clock, value should be 1.8, not 2.1")
    print("   Either the needle is not at 10 o'clock, or expected value is wrong.")