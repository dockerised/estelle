"""Async Playwright booking automation for Estelle Manor Padel courts."""
import asyncio
import logging
import re
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import settings
from database import db
from notifications import notifier

logger = logging.getLogger(__name__)


class BookingEngine:
    """Async Playwright automation for Padel court bookings."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.screenshots_dir = Path("./data/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def init_browser(self) -> Browser:
        """Initialize Playwright browser in headed mode with Xvfb virtual display."""
        logger.info("Initializing Playwright browser (headed mode with Xvfb virtual display)")
        self._playwright = await async_playwright().start()

        # Run in headed mode (not headless) since we have Xvfb providing a virtual display
        # This bypasses all headless detection since the browser is actually "headed"
        self._browser = await self._playwright.chromium.launch(
            headless=False,  # Headed mode with Xvfb virtual display
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-timer-throttling",
                "--disable-infobars",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ],
            chromium_sandbox=False,
            slow_mo=50  # Add 50ms delay between actions to appear more human
        )
        return self._browser

    async def get_context(self, fresh: bool = False) -> BrowserContext:
        """Get or create browser context with optional session persistence."""
        if self._context and not fresh:
            return self._context

        if not self._browser:
            await self.init_browser()

        # Complete user agent string to avoid detection
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Try to load saved session state
        if settings.browser_state_path.exists() and not fresh:
            logger.info("Loading saved browser session")
            self._context = await self._browser.new_context(
                storage_state=str(settings.browser_state_path),
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                locale="en-GB",
                timezone_id="Europe/London",
                geolocation={"latitude": 51.9244, "longitude": -0.9161},  # Near Estelle Manor
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Linux"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
        else:
            logger.info("Creating fresh browser context")
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                locale="en-GB",
                timezone_id="Europe/London",
                geolocation={"latitude": 51.9244, "longitude": -0.9161},  # Near Estelle Manor
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Linux"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            )

        # Add comprehensive JavaScript to mask headless detection
        await self._context.add_init_script("""
            // Override the navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Add Chrome properties that are missing in headless
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Mock plugins with realistic values
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en-US', 'en']
            });

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Mock connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                })
            });

            // Mock hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // Mock device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            // Mock platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Linux x86_64'
            });

            // Mock vendor
            Object.defineProperty(navigator, 'vendor', {
                get: () => 'Google Inc.'
            });

            // Remove Playwright-specific properties
            delete window.__playwright;
            delete window.__pw_manual;
            delete window.__PW_inspect;

            // Mask headless-specific WebGL vendor
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };

            // Add realistic screen properties
            Object.defineProperty(screen, 'availWidth', {
                get: () => 1920
            });
            Object.defineProperty(screen, 'availHeight', {
                get: () => 1080
            });
        """)

        return self._context

    async def save_session(self):
        """Save browser session state for reuse."""
        if self._context:
            settings.browser_state_path.parent.mkdir(parents=True, exist_ok=True)
            await self._context.storage_state(path=str(settings.browser_state_path))
            logger.info(f"Browser session saved to {settings.browser_state_path}")

    async def login(self, page: Page) -> bool:
        """Perform login to Estelle Manor."""
        try:
            logger.info("Navigating to login page")
            await page.goto(settings.login_url, wait_until="load", timeout=60000)
            await asyncio.sleep(2)

            # Fill login form
            logger.info("Filling login credentials")
            await page.fill('input[name="email"]', settings.estelle_username)
            await page.fill('input[name="password"]', settings.estelle_password)

            # Submit form
            logger.info("Submitting login form")
            await page.click('input[type="submit"]')

            # Wait for navigation after login
            await asyncio.sleep(5)

            # Check if login was successful (look for common logged-in indicators)
            # This might need adjustment based on actual site behavior
            current_url = page.url
            logger.info(f"After login, current URL: {current_url}")

            if "login" not in current_url.lower():
                logger.info("Login successful")

                # Navigate to homepage first to establish session properly
                logger.info("Navigating to homepage to establish session")
                await page.goto("https://home.estellemanor.com/", wait_until="load", timeout=30000)
                await asyncio.sleep(3)
                logger.info(f"Homepage loaded, URL: {page.url}")

                await self.save_session()
                return True
            else:
                logger.error("Login appears to have failed")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def human_like_mouse_movement(self, page: Page):
        """Add random mouse movements to appear more human."""
        try:
            import random
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 1800)
                y = random.randint(100, 900)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logger.debug(f"Mouse movement simulation failed: {e}")

    async def prepare_booking_page(self, page: Page, booking_date: str) -> bool:
        """Navigate to booking page and prepare for midnight submission."""
        try:
            logger.info(f"Navigating to booking page for date {booking_date}")
            logger.info(f"Target URL: {settings.booking_url}")

            # Add random delay before navigation (1-3 seconds)
            await asyncio.sleep(__import__('random').uniform(1, 3))

            # Human-like mouse movement before navigation
            await self.human_like_mouse_movement(page)

            await page.goto(settings.booking_url, wait_until="networkidle", timeout=60000)

            # Log where we actually ended up
            actual_url = page.url
            logger.info(f"After navigation, current URL: {actual_url}")

            # Check if we were redirected
            if actual_url != settings.booking_url:
                logger.warning(f"REDIRECT DETECTED: Expected {settings.booking_url} but got {actual_url}")

            logger.info("Page loaded, waiting for JavaScript...")
            await asyncio.sleep(5)

            # Take screenshot for debugging
            await page.screenshot(path="data/screenshots/booking_page_loaded.png", full_page=True)
            logger.info("Screenshot taken: booking_page_loaded.png")

            # Log page title for debugging
            page_title = await page.title()
            logger.info(f"Page title: {page_title}")

            # Try multiple methods to dismiss overlays/modals (AGGRESSIVE - site changed since Feb 5th)
            logger.info("Attempting to dismiss any popups/modals...")
            try:
                # Wait a bit for any popups to appear
                await asyncio.sleep(3)

                # Method 1: Press Escape multiple times first
                for i in range(5):
                    await page.keyboard.press('Escape')
                    await asyncio.sleep(0.3)

                # Method 2: Look for and click ANY buttons containing "close", "accept", "ok", "dismiss"
                button_texts = ['close', 'accept', 'ok', 'dismiss', 'continue', 'got it', 'agree']
                for text in button_texts:
                    try:
                        buttons = page.locator(f'button:has-text("{text}"), a:has-text("{text}")')
                        count = await buttons.count()
                        if count > 0:
                            for i in range(min(count, 3)):  # Click up to 3 matches
                                try:
                                    await buttons.nth(i).click(timeout=2000)
                                    logger.info(f"Clicked button with text: {text}")
                                    await asyncio.sleep(0.5)
                                except:
                                    pass
                    except:
                        pass

                # Method 3: Click specific selectors
                close_selectors = [
                    'button.close', '.modal-close', '[aria-label="Close"]',
                    '.popup-close', '#close-button', '[data-dismiss="modal"]',
                    '.cookie-accept', '#accept-cookies', '.triptease-close',
                    '.tt-messaging__container button', '.modal-backdrop'
                ]
                for selector in close_selectors:
                    try:
                        close_btn = page.locator(selector)
                        if await close_btn.count() > 0:
                            await close_btn.first.click(timeout=2000)
                            logger.info(f"Clicked: {selector}")
                            await asyncio.sleep(0.5)
                    except:
                        pass

                # Method 4: Click anywhere on page to dismiss
                try:
                    await page.click('body', position={'x': 10, 'y': 10}, timeout=2000)
                    await asyncio.sleep(1)
                except:
                    pass

                logger.info("Modal dismissal complete")

            except Exception as e:
                logger.debug(f"Modal dismissal attempts completed: {e}")

            # The date input should exist (don't wait for visible - jQuery datepicker might hide it)
            logger.info("Looking for date input in DOM...")

            # Give JavaScript more time to render the date picker (it takes a few seconds)
            logger.info("Waiting for page JavaScript to fully load...")
            await asyncio.sleep(5)

            # Wait for element to exist in DOM (increased timeout - JS takes time to render)
            await page.wait_for_selector('input#from_date', timeout=60000)
            logger.info("Date input found in DOM!")

            # Scroll it into view to make sure it's interactable
            await page.evaluate('document.querySelector("#from_date").scrollIntoView()')
            await asyncio.sleep(1)

            # Try to make it visible if it's hidden
            await page.evaluate('document.querySelector("#from_date").style.display = "block"')
            await page.evaluate('document.querySelector("#from_date").style.visibility = "visible"')
            await asyncio.sleep(0.5)

            # Fill the date (format: DD/MM/YYYY based on URL example)
            # Convert from YYYY-MM-DD to DD/MM/YYYY
            dt = datetime.strptime(booking_date, "%Y-%m-%d")
            formatted_date = dt.strftime("%d/%m/%Y")

            logger.info(f"Filling date: {formatted_date}")

            # Use JavaScript to set the value directly (jQuery datepicker friendly)
            await page.evaluate(f'document.querySelector("#from_date").value = "{formatted_date}"')

            # Trigger change event so datepicker knows the value changed
            await page.evaluate('document.querySelector("#from_date").dispatchEvent(new Event("change", { bubbles: true }))')

            # Close the datepicker popup by pressing Escape
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)

            logger.info("Booking page prepared and ready")
            return True

        except Exception as e:
            logger.error(f"Failed to prepare booking page: {e}")
            return False

    def parse_time_to_24hr(self, time_str: str) -> str:
        """Convert '7pm', '11am' etc to '19:00:00' format."""
        time_str = time_str.strip().lower()

        # Extract number and am/pm
        match = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str)
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")

        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)

        # Convert to 24-hour format
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}:00"

    async def find_and_click_time_slot(
        self,
        page: Page,
        booking_date: str,
        time_slot: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Find and click a specific time slot.
        Returns (success, court_name).
        """
        try:
            # Convert time to 24-hour format with date
            target_time_24hr = self.parse_time_to_24hr(time_slot)
            dt = datetime.strptime(booking_date, "%Y-%m-%d")
            formatted_date = dt.strftime("%d/%m/%Y")
            full_target = f"{formatted_date} {target_time_24hr}"

            logger.info(f"Looking for time slot: {full_target}")

            # Wait for availability results to load
            await asyncio.sleep(3)

            # Find all time slot containers
            slot_containers = page.locator('div.cardBtn-bd.vr.vr_centered')
            count = await slot_containers.count()

            logger.info(f"Found {count} time slot containers")

            # Search for matching time slot
            for i in range(count):
                container = slot_containers.nth(i)

                # Get the slot_start span
                slot_start = container.locator('span.slot_start')
                slot_text = await slot_start.text_content()

                if slot_text and slot_text.strip() == full_target:
                    # Found the matching slot!
                    logger.info(f"Found matching time slot: {slot_text}")

                    # Get court name
                    court_name_span = container.locator('span.slot-subject-spa')
                    court_name = await court_name_span.text_content()

                    # Check availability
                    total_booked_span = container.locator('span.totalBooked')
                    total_slots_span = container.locator('span.totalSlots')

                    total_booked = int(await total_booked_span.text_content())
                    total_slots = int(await total_slots_span.text_content())

                    if total_booked >= total_slots:
                        logger.warning(f"Time slot {slot_text} is fully booked")
                        return (False, None)

                    # Click the slot - need to click the parent card, not the hidden span
                    # The parent div with class 'cardBtn' is the clickable element
                    parent_card = container.locator('..')

                    if settings.dry_run:
                        logger.info(f"[DRY RUN] Would click time slot {slot_text}")
                        return (True, court_name.strip() if court_name else None)
                    else:
                        logger.info(f"Clicking time slot {slot_text} via parent card")
                        await parent_card.click()
                        await asyncio.sleep(3)
                        return (True, court_name.strip() if court_name else None)

            logger.warning(f"Time slot {full_target} not found")
            return (False, None)

        except Exception as e:
            logger.error(f"Error finding/clicking time slot: {e}")
            return (False, None)

    async def verify_confirmation(self, page: Page) -> bool:
        """Verify that booking confirmation page appeared."""
        try:
            # Wait a bit for page to load
            await asyncio.sleep(3)

            # Look for confirmation indicators
            # This needs to be customized based on actual confirmation page
            page_content = await page.content()

            # Common confirmation text patterns
            confirmation_patterns = [
                "confirmed",
                "booking confirmed",
                "reservation confirmed",
                "thank you",
                "confirmation",
                "successfully booked"
            ]

            page_lower = page_content.lower()
            for pattern in confirmation_patterns:
                if pattern in page_lower:
                    logger.info(f"Found confirmation indicator: '{pattern}'")
                    return True

            # Check URL change
            current_url = page.url
            if "confirmation" in current_url.lower() or "success" in current_url.lower():
                logger.info("Confirmation detected via URL")
                return True

            logger.warning("Could not verify booking confirmation")
            return False

        except Exception as e:
            logger.error(f"Error verifying confirmation: {e}")
            return False

    async def take_screenshot(self, page: Page, name: str) -> Optional[str]:
        """Take a screenshot for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshots_dir / filename

            await page.screenshot(path=str(filepath), full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    async def execute_booking(
        self,
        booking_id: int,
        booking_date: str,
        time_primary: str,
        time_fallback: Optional[str]
    ):
        """
        Execute a booking at the scheduled time.
        This should be called at 11:50pm to prepare, then submit at midnight.
        """
        logger.info(f"Starting booking execution for ID {booking_id}")
        db.log_execution(booking_id, "start", "initiated")

        page = None
        try:
            # Get browser context
            context = await self.get_context()
            page = await context.new_page()

            # Login (this happens at 11:50pm)
            logger.info("Performing login")
            login_success = await self.login(page)
            if not login_success:
                raise Exception("Login failed")

            db.log_execution(booking_id, "login", "success")

            # Prepare booking page
            logger.info("Preparing booking page")
            prep_success = await self.prepare_booking_page(page, booking_date)
            if not prep_success:
                raise Exception("Failed to prepare booking page")

            db.log_execution(booking_id, "prepare_page", "success")

            # Wait until exactly midnight to submit
            # We're at 11:50pm, so midnight is ~10 minutes away
            now = datetime.now()

            # If we're before midnight today, wait until midnight
            # If we're after midnight, we've already passed it
            if now.hour >= 12:  # PM times
                # Calculate midnight of the next day
                tomorrow = now.date() + timedelta(days=1)
                midnight = datetime.combine(tomorrow, dt_time(0, 0, 0))
            else:
                # We're in the AM, midnight has already passed
                midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

            if now < midnight:
                wait_seconds = (midnight - now).total_seconds()
                logger.info(f"Waiting {wait_seconds:.1f} seconds until midnight ({midnight.strftime('%Y-%m-%d %H:%M:%S')})")
                await asyncio.sleep(wait_seconds)
            else:
                logger.warning("Midnight has already passed, executing immediately")

            # At midnight: click "Show Availability"
            logger.info("Clicking 'Show Availability' link")
            if not settings.dry_run:
                # Find and click the show availability link
                show_link = page.locator('a:has-text("Show Availability")')
                await show_link.click()
                await asyncio.sleep(2)
            else:
                # In dry run, still click to see results
                show_link = page.locator('a:has-text("Show Availability")')
                await show_link.click()
                await asyncio.sleep(3)

            db.log_execution(booking_id, "show_availability", "clicked")

            # Try primary time slot first
            logger.info(f"Attempting to book primary time: {time_primary}")
            success, court_name = await self.find_and_click_time_slot(
                page, booking_date, time_primary
            )

            booked_time = time_primary

            # If primary failed and we have a fallback, try it
            if not success and time_fallback:
                logger.info(f"Primary time unavailable, trying fallback: {time_fallback}")
                success, court_name = await self.find_and_click_time_slot(
                    page, booking_date, time_fallback
                )
                booked_time = time_fallback

            if not success:
                # Both times unavailable
                logger.warning("Both time slots unavailable")
                db.update_booking_status(booking_id, "failed", error_message="No availability")
                db.log_execution(booking_id, "booking", "failed", "Both times unavailable")

                await notifier.booking_unavailable(booking_date, time_primary, time_fallback)
                screenshot = await self.take_screenshot(page, f"unavailable_{booking_id}")
                if screenshot:
                    db.update_booking_status(booking_id, "failed", screenshot_path=screenshot)
                return

            # Verify confirmation page
            logger.info("Verifying booking confirmation")
            confirmed = await self.verify_confirmation(page)

            if confirmed or settings.dry_run:
                logger.info("Booking confirmed!")
                db.update_booking_status(
                    booking_id,
                    "booked",
                    court_name=court_name,
                    booked_time=booked_time
                )
                db.log_execution(booking_id, "booking", "success", f"Booked {booked_time}")

                await notifier.booking_success(booking_date, booked_time, court_name)

                # Take confirmation screenshot
                screenshot = await self.take_screenshot(page, f"success_{booking_id}")
                if screenshot:
                    db.update_booking_status(booking_id, "booked", screenshot_path=screenshot)
            else:
                logger.error("Could not verify booking confirmation")
                db.update_booking_status(
                    booking_id,
                    "failed",
                    error_message="Could not verify confirmation"
                )
                db.log_execution(booking_id, "verify", "failed", "No confirmation found")

                await notifier.booking_failed(
                    booking_date,
                    time_primary,
                    time_fallback,
                    "Could not verify booking confirmation"
                )

                screenshot = await self.take_screenshot(page, f"unverified_{booking_id}")
                if screenshot:
                    db.update_booking_status(booking_id, "failed", screenshot_path=screenshot)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Booking execution failed: {error_msg}")

            db.update_booking_status(booking_id, "failed", error_message=error_msg)
            db.log_execution(booking_id, "booking", "error", error_msg)

            await notifier.booking_failed(booking_date, time_primary, time_fallback, error_msg)

            if page:
                screenshot = await self.take_screenshot(page, f"error_{booking_id}")
                if screenshot:
                    db.update_booking_status(booking_id, "failed", screenshot_path=screenshot)

        finally:
            if page:
                await page.close()

    async def cleanup(self):
        """Clean up browser resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser cleanup complete")


# Global booking engine instance
engine = BookingEngine()
