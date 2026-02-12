"""Test script for calendar generation."""

import asyncio
from calendar_utils import calendar_generator
from notifications import notifier


def test_time_parsing():
    """Test time parsing functionality."""
    print("Testing time parsing...")

    test_cases = [
        ("2026-02-17", "10am"),
        ("2026-02-19", "7pm"),
        ("2026-03-01", "7:30pm"),
        ("2026-03-15", "12pm"),
        ("2026-03-20", "12am"),
    ]

    for date, time in test_cases:
        try:
            dt = calendar_generator.parse_time_to_datetime(date, time)
            print(f"✓ {date} {time} -> {dt}")
        except Exception as e:
            print(f"✗ {date} {time} -> ERROR: {e}")


def test_ics_generation():
    """Test .ics file generation."""
    print("\nTesting .ics file generation...")

    try:
        ics_file = calendar_generator.generate_ics(
            booking_date="2026-02-17",
            booking_time="10am",
            court_name="Court 1"
        )

        # Check that file was generated
        ics_file.seek(0)
        content = ics_file.read().decode('utf-8')

        print(f"✓ Generated .ics file ({len(content)} bytes)")

        # Check for required components
        required = [
            'BEGIN:VCALENDAR',
            'BEGIN:VEVENT',
            'DTSTART',
            'DTEND',
            'SUMMARY:Padel Court Booking - Court 1',
            'LOCATION:Estelle Manor Padel Courts',
            'STATUS:CONFIRMED',
            'BEGIN:VALARM',
        ]

        for component in required:
            if component in content:
                print(f"  ✓ Contains: {component}")
            else:
                print(f"  ✗ Missing: {component}")

        # Save to file for manual inspection
        test_file = "/tmp/test_booking.ics"
        with open(test_file, 'wb') as f:
            ics_file.seek(0)
            f.write(ics_file.read())
        print(f"\n✓ Saved test file to: {test_file}")
        print("  You can open this file in a calendar app to verify it works")

    except Exception as e:
        print(f"✗ Failed to generate .ics file: {e}")
        import traceback
        traceback.print_exc()


def test_filename_generation():
    """Test filename generation."""
    print("\nTesting filename generation...")

    test_cases = [
        ("2026-02-17", "10am", "padel_booking_2026-02-17_10am.ics"),
        ("2026-02-19", "7pm", "padel_booking_2026-02-19_7pm.ics"),
        ("2026-03-01", "7:30pm", "padel_booking_2026-03-01_730pm.ics"),
    ]

    for date, time, expected in test_cases:
        result = calendar_generator.generate_filename(date, time)
        if result == expected:
            print(f"✓ {date} {time} -> {result}")
        else:
            print(f"✗ {date} {time} -> {result} (expected: {expected})")


async def test_discord_integration():
    """Test Discord notification with calendar attachment."""
    print("\nTesting Discord integration...")
    print("This will send a test notification to your Discord webhook.")

    response = input("Send test notification? (y/n): ")
    if response.lower() != 'y':
        print("Skipped Discord test")
        return

    try:
        await notifier.booking_success(
            booking_date="2026-02-17",
            booked_time="10am",
            court_name="Court 1 (Test)"
        )
        print("✓ Discord notification sent")
        print("  Check your Discord channel for the message with calendar attachment")

    except Exception as e:
        print(f"✗ Failed to send Discord notification: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Calendar Invite Generation - Test Suite")
    print("=" * 60)

    test_time_parsing()
    test_filename_generation()
    test_ics_generation()

    await test_discord_integration()

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
