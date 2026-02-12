#!/usr/bin/env python3
"""
Local test script for booking engine with VISIBLE browser.
Use this for local development and debugging.

Usage:
    python test_local_booking.py

This will:
1. Open a visible Chrome browser window
2. Perform login to Estelle Manor
3. Navigate to the booking page
4. Show you what's happening in real-time
"""
import asyncio
import logging
from datetime import datetime

# Import the LOCAL version of the booking engine
from booking_engine_local import BookingEngine
from database import db
from config import settings

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_local_booking():
    """Test booking with visible browser for local debugging."""

    logger.info("=" * 80)
    logger.info("STARTING LOCAL BOOKING TEST (VISIBLE BROWSER MODE)")
    logger.info("=" * 80)
    logger.info("")
    logger.info("You should see a browser window open shortly...")
    logger.info("")

    # Create booking engine instance
    engine = BookingEngine()

    try:
        # Test parameters - modify these as needed
        booking_date = "2026-02-25"  # Format: YYYY-MM-DD
        time_primary = "12pm"
        time_fallback = None

        logger.info(f"Test booking for: {booking_date} at {time_primary}")
        logger.info("")

        # Create a test booking in the database
        booking_id = db.create_booking(
            booking_date=booking_date,
            time_primary=time_primary,
            time_fallback=time_fallback,
            execute_at=datetime.utcnow().isoformat()
        )

        logger.info(f"Created booking ID: {booking_id}")
        logger.info("")
        logger.info("Watch the browser window to see what happens...")
        logger.info("")

        # Execute the booking (you'll see the browser in action)
        await engine.execute_booking(
            booking_id=booking_id,
            booking_date=booking_date,
            time_primary=time_primary,
            time_fallback=time_fallback
        )

        # Get the result
        booking = db.get_booking(booking_id)

        logger.info("")
        logger.info("=" * 80)
        logger.info("BOOKING RESULT:")
        logger.info("=" * 80)
        logger.info(f"Status: {booking['status']}")
        logger.info(f"Court Name: {booking.get('court_name', 'N/A')}")
        logger.info(f"Booked Time: {booking.get('booked_time', 'N/A')}")
        logger.info(f"Error Message: {booking.get('error_message', 'None')}")
        logger.info(f"Screenshot: {booking.get('screenshot_path', 'N/A')}")
        logger.info("")

        # Show logs
        logs = db.get_booking_logs(booking_id)
        logger.info("Execution Logs:")
        for log in logs:
            logger.info(f"  [{log['action']}] {log['result']}: {log.get('details', '')}")

    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n\nTest failed with error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("\n\nCleaning up...")
        await engine.cleanup()
        logger.info("Done!")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_local_booking())
