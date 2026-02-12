"""Monitor What's On page for new events at Estelle Manor."""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext
from config import settings
from database import db
from notifications import notifier

logger = logging.getLogger(__name__)


class EventsMonitor:
    """Monitor What's On page for new events."""

    def __init__(self):
        self.whats_on_url = "https://home.estellemanor.com/whats-on"
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None

    async def init_browser(self):
        """Initialize browser if needed."""
        if not self._browser:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )

    async def cleanup(self):
        """Cleanup browser resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch_events(self) -> List[Dict[str, Any]]:
        """Fetch current events from What's On page."""
        try:
            await self.init_browser()
            page = await self._context.new_page()

            # Login first
            logger.info("Logging in to access What's On page")
            await page.goto(settings.login_url, wait_until="load", timeout=60000)
            await asyncio.sleep(2)
            await page.fill('input[name="email"]', settings.estelle_username)
            await page.fill('input[name="password"]', settings.estelle_password)
            await page.click('input[type="submit"]')
            await asyncio.sleep(5)

            logger.info(f"Fetching events from {self.whats_on_url}")
            await page.goto(self.whats_on_url, wait_until="load", timeout=60000)
            await asyncio.sleep(3)

            # Debug: save page content
            await page.screenshot(path="/tmp/whats_on_debug.png", full_page=True)
            html = await page.content()
            with open('/tmp/whats_on_debug.html', 'w') as f:
                f.write(html)
            page_title = await page.title()
            logger.info(f"Page title: {page_title}")

            events = []

            # Try to find event cards/listings
            # Based on testing, look for any heading elements that might be event titles
            event_containers = await page.locator('h2, h3, h4, .title, [class*="title"]').all()

            # Filter out obvious non-events
            filtered_containers = []
            ignore_list = [
                'login', 'home', 'menu', 'search', 'estelle manor',
                'book a room', 'book a stay', 'make a booking', 'reserve',
                'contact us', 'about us', 'privacy policy', 'terms',
                'footer', 'header', 'navigation', 'subscribe',
                'follow us', 'social media', 'back to top'
            ]
            for container in event_containers:
                text = (await container.text_content() or '').strip()
                text_lower = text.lower()
                # Skip empty or generic site navigation
                if text and text_lower not in ignore_list and len(text) > 5:
                    # Also skip if it's just the site name with no additional info
                    if text_lower == 'estelle manor':
                        continue
                    filtered_containers.append(container)

            event_containers = filtered_containers
            logger.info(f"Found {len(event_containers)} potential event containers")

            for i, container in enumerate(event_containers[:30]):  # Limit to 30 to avoid noise
                try:
                    # The container itself is likely the title heading
                    title = (await container.text_content() or '').strip()

                    if not title or len(title) > 150:  # Skip very long text (probably not a title)
                        continue

                    # Try to find associated content by looking at parent or siblings
                    parent = container.locator('..')
                    date_text = ''
                    description = ''
                    link = ''

                    # Look for date near the title
                    try:
                        date_elem = parent.locator('.date, .datetime, time, [class*="date"]').first
                        if await date_elem.count() > 0:
                            date_text = (await date_elem.text_content() or '').strip()
                    except:
                        pass

                    # Look for description
                    try:
                        desc_elem = parent.locator('p').first
                        if await desc_elem.count() > 0:
                            description = (await desc_elem.text_content() or '').strip()[:200]
                    except:
                        pass

                    # Look for link
                    try:
                        link_elem = parent.locator('a').first
                        if await link_elem.count() > 0:
                            href = await link_elem.get_attribute('href')
                            if href:
                                link = href if href.startswith('http') else f"https://home.estellemanor.com{href}"
                    except:
                        pass

                    # Skip if link points to generic pages (not actual events)
                    if link and any(generic in link.lower() for generic in ['/book-a-room', '/reserve', '/contact', '/about']):
                        logger.debug(f"Skipping non-event link: {title}")
                        continue

                    # Skip if title is too generic
                    generic_titles = ['estelle manor', 'book now', 'reserve', 'learn more']
                    if title.lower() in generic_titles:
                        logger.debug(f"Skipping generic title: {title}")
                        continue

                    event = {
                        'title': title,
                        'date': date_text,
                        'description': description,
                        'link': link,
                        'discovered_at': datetime.utcnow().isoformat()
                    }
                    events.append(event)
                    logger.debug(f"Found event: {event['title']}")

                except Exception as e:
                    logger.debug(f"Error parsing event container {i}: {e}")

            await page.close()
            logger.info(f"Successfully fetched {len(events)} events")
            return events

        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []

    async def check_for_new_events(self):
        """Check for new events and notify."""
        if not settings.events_monitoring_enabled:
            logger.debug("Events monitoring is disabled")
            return

        logger.info("Checking for new events on What's On page")

        try:
            # Fetch current events
            current_events = await self.fetch_events()

            if not current_events:
                logger.warning("No events found on page")
                return

            # Get previously seen events
            seen_events = db.get_seen_events()
            seen_titles = {e['title'] for e in seen_events}

            # Find new events
            new_events = [e for e in current_events if e['title'] not in seen_titles]

            if new_events:
                logger.info(f"Found {len(new_events)} new events!")

                # Store new events
                for event in new_events:
                    db.store_event(event)

                # Send notification
                await self.notify_new_events(new_events)

            else:
                logger.info("No new events found")

        except Exception as e:
            logger.error(f"Error checking for new events: {e}")
            await notifier.system_error(
                "Events monitoring error",
                str(e)
            )

    async def notify_new_events(self, events: List[Dict[str, Any]]):
        """Send Discord notification for new events."""
        try:
            if len(events) == 1:
                # Single event notification
                event = events[0]
                embed = {
                    "title": f"🎉 New Event at Estelle Manor!",
                    "description": event['title'],
                    "color": 5814783,  # Purple
                    "fields": [],
                    "timestamp": datetime.utcnow().isoformat()
                }

                if event['date']:
                    embed["fields"].append({
                        "name": "Date",
                        "value": event['date'],
                        "inline": True
                    })

                if event['description']:
                    embed["fields"].append({
                        "name": "Description",
                        "value": event['description'][:1000],
                        "inline": False
                    })

                if event['link']:
                    embed["fields"].append({
                        "name": "Link",
                        "value": event['link'],
                        "inline": False
                    })

                embed["fields"].append({
                    "name": "View All Events",
                    "value": "https://home.estellemanor.com/whats-on",
                    "inline": False
                })

                await notifier.send_message(
                    content=f"📅 **New event posted at Estelle Manor: {event['title']}**",
                    embeds=[embed]
                )

            else:
                # Multiple events notification
                event_names = "\n".join([f"• {e['title']}" for e in events[:10]])
                if len(events) > 10:
                    event_names += f"\n...and {len(events) - 10} more"

                # Include first 3 event names in the content
                first_three = ", ".join([e['title'] for e in events[:3]])
                if len(events) > 3:
                    first_three += f" and {len(events) - 3} more"

                embed = {
                    "title": f"🎉 {len(events)} New Events at Estelle Manor!",
                    "description": event_names,
                    "color": 5814783,
                    "fields": [{
                        "name": "View All Events",
                        "value": "https://home.estellemanor.com/whats-on",
                        "inline": False
                    }],
                    "timestamp": datetime.utcnow().isoformat()
                }

                await notifier.send_message(
                    content=f"📅 **{len(events)} new events: {first_three}**",
                    embeds=[embed]
                )

            logger.info(f"Sent Discord notification for {len(events)} new events")

        except Exception as e:
            logger.error(f"Error sending event notification: {e}")


# Global instance
events_monitor = EventsMonitor()
