#!/usr/bin/env python3
"""
Keep trying to make a booking until successful.
Waits 10 minutes between login attempts to avoid being flagged.
"""
import asyncio
import logging
from datetime import datetime
from booking_engine_local import BookingEngine
from database import db
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Booking parameters
BOOKING_DATE = "2026-02-25"
TIME_PRIMARY = "12pm"
TIME_FALLBACK = None
WAIT_MINUTES_BETWEEN_ATTEMPTS = 10


async def attempt_booking(attempt_number: int):
    """Attempt a single booking."""
    logger.info("=" * 80)
    logger.info(f"ATTEMPT #{attempt_number}")
    logger.info(f"Booking: {BOOKING_DATE} at {TIME_PRIMARY}")
    logger.info("=" * 80)

    engine = BookingEngine()

    try:
        # Create booking record
        booking_id = db.create_booking(
            booking_date=BOOKING_DATE,
            time_primary=TIME_PRIMARY,
            time_fallback=TIME_FALLBACK,
            execute_at=datetime.now().isoformat()
        )

        logger.info(f"Created booking ID: {booking_id}")

        # Execute booking
        await engine.execute_booking(
            booking_id=booking_id,
            booking_date=BOOKING_DATE,
            time_primary=TIME_PRIMARY,
            time_fallback=TIME_FALLBACK
        )

        # Check result
        booking = db.get_booking(booking_id)
        status = booking['status']

        logger.info(f"\nResult: {status}")

        if status == 'booked':
            logger.info("✅ SUCCESS! Booking completed!")
            logger.info(f"Court: {booking.get('court_name')}")
            logger.info(f"Time: {booking.get('booked_time')}")
            return True
        else:
            logger.info(f"❌ Failed: {booking.get('error_message', 'Unknown error')}")
            return False

    except Exception as e:
        logger.error(f"❌ Exception during booking: {e}", exc_info=True)
        return False
    finally:
        await engine.cleanup()


async def keep_trying():
    """Keep trying until successful."""
    attempt = 1

    while True:
        success = await attempt_booking(attempt)

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 BOOKING SUCCESSFUL! Stopping.")
            logger.info("=" * 80)
            break

        # Wait before next attempt (unless this is the last attempt we want)
        wait_seconds = WAIT_MINUTES_BETWEEN_ATTEMPTS * 60
        logger.info(f"\nWaiting {WAIT_MINUTES_BETWEEN_ATTEMPTS} minutes before next attempt...")
        logger.info(f"(to avoid being flagged by the site)")

        # Countdown
        for remaining in range(wait_seconds, 0, -60):
            mins = remaining // 60
            logger.info(f"  {mins} minute(s) remaining...")
            await asyncio.sleep(60)

        attempt += 1
        logger.info("\n")


if __name__ == "__main__":
    try:
        asyncio.run(keep_trying())
    except KeyboardInterrupt:
        logger.info("\n\n❌ Stopped by user (Ctrl+C)")
