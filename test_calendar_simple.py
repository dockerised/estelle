#!/usr/bin/env python3
"""Simple test script for calendar generation without external dependencies."""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    try:
        from calendar_utils import calendar_generator
        print("✓ calendar_utils imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_time_parsing():
    """Test time parsing functionality."""
    print("\nTesting time parsing...")
    from calendar_utils import calendar_generator

    test_cases = [
        ("2026-02-17", "10am", "2026-02-17 10:00:00"),
        ("2026-02-19", "7pm", "2026-02-19 19:00:00"),
        ("2026-03-01", "7:30pm", "2026-03-01 19:30:00"),
        ("2026-03-15", "12pm", "2026-03-15 12:00:00"),
        ("2026-03-20", "12am", "2026-03-20 00:00:00"),
    ]

    all_passed = True
    for date, time, expected_prefix in test_cases:
        try:
            dt = calendar_generator.parse_time_to_datetime(date, time)
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            if dt_str.startswith(expected_prefix):
                print(f"✓ {date} {time:8s} -> {dt_str}")
            else:
                print(f"✗ {date} {time:8s} -> {dt_str} (expected: {expected_prefix})")
                all_passed = False
        except Exception as e:
            print(f"✗ {date} {time:8s} -> ERROR: {e}")
            all_passed = False

    return all_passed


def test_filename_generation():
    """Test filename generation."""
    print("\nTesting filename generation...")
    from calendar_utils import calendar_generator

    test_cases = [
        ("2026-02-17", "10am", "padel_booking_2026-02-17_10am.ics"),
        ("2026-02-19", "7pm", "padel_booking_2026-02-19_7pm.ics"),
        ("2026-03-01", "7:30pm", "padel_booking_2026-03-01_730pm.ics"),
    ]

    all_passed = True
    for date, time, expected in test_cases:
        result = calendar_generator.generate_filename(date, time)
        if result == expected:
            print(f"✓ {date} {time:8s} -> {result}")
        else:
            print(f"✗ {date} {time:8s} -> {result} (expected: {expected})")
            all_passed = False

    return all_passed


def test_ics_generation():
    """Test .ics file generation."""
    print("\nTesting .ics file generation...")
    from calendar_utils import calendar_generator

    try:
        # Generate test calendar file
        ics_file = calendar_generator.generate_ics(
            booking_date="2026-02-17",
            booking_time="10am",
            court_name="Court 1"
        )

        # Read content
        ics_file.seek(0)
        content = ics_file.read().decode('utf-8')

        print(f"✓ Generated .ics file ({len(content)} bytes)")

        # Check for required components
        required = [
            ('BEGIN:VCALENDAR', 'Calendar container'),
            ('BEGIN:VEVENT', 'Event container'),
            ('DTSTART', 'Start time'),
            ('DTEND', 'End time'),
            ('SUMMARY:Padel Court Booking - Court 1', 'Event title'),
            ('LOCATION:Estelle Manor Padel Courts', 'Location'),
            ('STATUS:CONFIRMED', 'Confirmed status'),
            ('BEGIN:VALARM', 'Reminder alarm'),
        ]

        all_present = True
        for component, description in required:
            if component in content:
                print(f"  ✓ {description:30s} ({component})")
            else:
                print(f"  ✗ {description:30s} (MISSING: {component})")
                all_present = False

        # Save to file for manual inspection
        test_file = "/tmp/test_booking.ics"
        try:
            with open(test_file, 'wb') as f:
                ics_file.seek(0)
                f.write(ics_file.read())
            print(f"\n✓ Saved test file to: {test_file}")
            print("  You can open this file in a calendar app to verify")
        except Exception as e:
            print(f"\n⚠ Could not save test file: {e}")

        return all_present

    except Exception as e:
        print(f"✗ Failed to generate .ics file: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Calendar Invite Generation - Test Suite")
    print("=" * 70)

    results = []

    # Test imports
    if not test_imports():
        print("\n✗ Import test failed. Cannot continue.")
        return 1

    # Run tests
    results.append(("Time Parsing", test_time_parsing()))
    results.append(("Filename Generation", test_filename_generation()))
    results.append(("ICS Generation", test_ics_generation()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} {name}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
