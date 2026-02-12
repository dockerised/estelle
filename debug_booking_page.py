#!/usr/bin/env python3
"""
Debug script to inspect the booking page and find the correct selectors.
"""
import asyncio
import logging
from booking_engine_local import BookingEngine
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def debug_booking_page():
    """Debug the booking page to find correct selectors."""

    engine = BookingEngine()

    try:
        # Initialize browser
        await engine.init_browser()
        context = await engine.get_context()
        page = await context.new_page()

        # Login
        logger.info("Logging in...")
        await engine.login(page)

        # Navigate to booking page
        logger.info(f"Navigating to booking page: {settings.booking_url}")
        await page.goto(settings.booking_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)

        logger.info(f"Current URL: {page.url}")
        logger.info(f"Page Title: {await page.title()}")

        # Check for iframes
        logger.info("\n=== CHECKING FOR IFRAMES ===")
        iframes = page.frames
        logger.info(f"Found {len(iframes)} frames on the page")
        for i, frame in enumerate(iframes):
            logger.info(f"  Frame {i}: {frame.url}")

        # Look for all input fields
        logger.info("\n=== ALL INPUT FIELDS ===")
        inputs = await page.query_selector_all('input')
        logger.info(f"Found {len(inputs)} input elements")

        for i, inp in enumerate(inputs):
            input_id = await inp.get_attribute('id')
            input_name = await inp.get_attribute('name')
            input_type = await inp.get_attribute('type')
            input_class = await inp.get_attribute('class')
            input_placeholder = await inp.get_attribute('placeholder')

            logger.info(f"\nInput {i}:")
            logger.info(f"  id: {input_id}")
            logger.info(f"  name: {input_name}")
            logger.info(f"  type: {input_type}")
            logger.info(f"  class: {input_class}")
            logger.info(f"  placeholder: {input_placeholder}")

        # Try to find from_date specifically
        logger.info("\n=== LOOKING FOR from_date ===")
        from_date = await page.query_selector('#from_date')
        if from_date:
            logger.info("✅ Found #from_date element!")
            is_visible = await from_date.is_visible()
            is_enabled = await from_date.is_enabled()
            logger.info(f"  Visible: {is_visible}")
            logger.info(f"  Enabled: {is_enabled}")
        else:
            logger.info("❌ #from_date NOT FOUND")

            # Try variations
            logger.info("\nTrying variations:")
            variations = [
                'input[name="from_date"]',
                'input[id*="from"]',
                'input[id*="date"]',
                '.datepicker',
                'input.js-datepicker'
            ]
            for selector in variations:
                elements = await page.query_selector_all(selector)
                if elements:
                    logger.info(f"  ✅ Found {len(elements)} element(s) with: {selector}")
                else:
                    logger.info(f"  ❌ Not found: {selector}")

        # Check if it's in an iframe
        logger.info("\n=== CHECKING IFRAMES FOR from_date ===")
        for i, frame in enumerate(iframes):
            if i == 0:  # Skip main frame
                continue
            try:
                from_date_in_frame = await frame.query_selector('#from_date')
                if from_date_in_frame:
                    logger.info(f"✅ Found #from_date in iframe {i}: {frame.url}")
                    break
            except:
                pass

        # Wait so you can inspect in the browser
        logger.info("\n=== Browser window will stay open for 30 seconds ===")
        logger.info("You can manually inspect the page in the browser window")
        logger.info("Press Ctrl+C to close early")
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await engine.cleanup()
        logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(debug_booking_page())
