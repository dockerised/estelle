#!/usr/bin/env python3
"""
Keep trying to make a booking until successful.
Smart approach: Login ONCE, then reuse browser with new tabs for each attempt.
This avoids triggering security flags from repeated logins.
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


async def attempt_booking_with_new_tab(engine, context, attempt_number: int):
    """Attempt a single booking using a new tab in the existing browser."""
    logger.info("=" * 80)
    logger.info(f"ATTEMPT #{attempt_number}")
    logger.info(f"Booking: {BOOKING_DATE} at {TIME_PRIMARY}")
    logger.info("=" * 80)

    # Create a new page/tab
    page = await context.new_page()

    try:
        # Create booking record
        booking_id = db.create_booking(
            booking_date=BOOKING_DATE,
            time_primary=TIME_PRIMARY,
            time_fallback=TIME_FALLBACK,
            execute_at=datetime.now().isoformat()
        )

        logger.info(f"Created booking ID: {booking_id}")
        logger.info("Using new tab in existing browser session...")

        # Navigate directly to booking page (already logged in)
        logger.info(f"Navigating to booking page: {settings.booking_url}")
        await page.goto(settings.booking_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)

        logger.info(f"Current URL: {page.url}")

        # Prepare the booking page
        success = await engine.prepare_booking_page(page, BOOKING_DATE)
        if not success:
            logger.error("Failed to prepare booking page")
            db.update_booking_status(booking_id, "failed", error_message="Failed to prepare page")
            return False

        db.log_execution(booking_id, "prepare_page", "success")

        # Click "Show Availability"
        logger.info("Clicking 'Show Availability'")
        show_link = page.locator('a:has-text("Show Availability")')
        await show_link.click()
        await asyncio.sleep(3)

        db.log_execution(booking_id, "show_availability", "clicked")

        # Try to find and click time slot
        logger.info(f"Looking for time slot: {TIME_PRIMARY}")
        success, court_name = await engine.find_and_click_time_slot(
            page, BOOKING_DATE, TIME_PRIMARY
        )

        booked_time = TIME_PRIMARY

        # If primary failed, try fallback
        if not success and TIME_FALLBACK:
            logger.info(f"Trying fallback time: {TIME_FALLBACK}")
            success, court_name = await engine.find_and_click_time_slot(
                page, BOOKING_DATE, TIME_FALLBACK
            )
            booked_time = TIME_FALLBACK

        if not success:
            logger.warning("No availability for requested times")
            db.update_booking_status(booking_id, "failed", error_message="No availability")
            db.log_execution(booking_id, "booking", "failed", "No slots available")
            return False

        # Verify confirmation
        logger.info("Verifying booking confirmation...")
        confirmed = await engine.verify_confirmation(page)

        if confirmed or settings.dry_run:
            logger.info("✅ BOOKING CONFIRMED!")
            db.update_booking_status(
                booking_id,
                "booked",
                court_name=court_name,
                booked_time=booked_time
            )
            db.log_execution(booking_id, "booking", "success", f"Booked {booked_time}")

            # Take screenshot
            screenshot = await engine.take_screenshot(page, f"success_{booking_id}")
            if screenshot:
                db.update_booking_status(booking_id, "booked", screenshot_path=screenshot)

            logger.info(f"Court: {court_name}")
            logger.info(f"Time: {booked_time}")
            return True
        else:
            logger.error("Could not verify confirmation")
            db.update_booking_status(booking_id, "failed", error_message="No confirmation")
            return False

    except Exception as e:
        logger.error(f"Exception during booking: {e}", exc_info=True)
        return False
    finally:
        # Close the tab
        await page.close()
        logger.info("Tab closed")


async def keep_trying_smart():
    """Login once, then keep trying with new tabs."""

    logger.info("=" * 80)
    logger.info("INITIALIZING BROWSER AND LOGGING IN (ONE TIME ONLY)")
    logger.info("=" * 80)

    engine = BookingEngine()

    try:
        # Initialize browser ONCE
        await engine.init_browser()
        context = await engine.get_context()

        # Login ONCE
        login_page = await context.new_page()
        try:
            logger.info("Performing initial login...")
            login_success = await engine.login(login_page)
            if not login_success:
                logger.error("Initial login failed!")
                return
            logger.info("✅ Login successful - browser will stay open for all attempts")
        finally:
            await login_page.close()

        # Now loop with new tabs
        attempt = 1
        while True:
            success = await attempt_booking_with_new_tab(engine, context, attempt)

            if success:
                logger.info("\n" + "=" * 80)
                logger.info("🎉 BOOKING SUCCESSFUL! Stopping.")
                logger.info("=" * 80)
                break

            # Wait before next attempt
            wait_seconds = WAIT_MINUTES_BETWEEN_ATTEMPTS * 60
            logger.info(f"\nWaiting {WAIT_MINUTES_BETWEEN_ATTEMPTS} minutes before next attempt...")

            # Countdown
            for remaining in range(wait_seconds, 0, -60):
                mins = remaining // 60
                logger.info(f"  {mins} minute(s) remaining...")
                await asyncio.sleep(60)

            attempt += 1
            logger.info("\n")

    finally:
        await engine.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(keep_trying_smart())
    except KeyboardInterrupt:
        logger.info("\n\n❌ Stopped by user (Ctrl+C)")
