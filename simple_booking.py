#!/usr/bin/env python3
"""
Simple Estelle Manor Padel Court Booking Script
Uses Firefox with Playwright - slow and simple
"""
import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
EMAIL = os.getenv('ESTELLE_USERNAME')
PASSWORD = os.getenv('ESTELLE_PASSWORD')
BOOKING_DATE = "28/02/2026"  # DD/MM/YYYY format
BOOKING_TIME = "8:00 PM"     # e.g., "8:00 PM", "7:00 PM", etc.

# Validate credentials
if not EMAIL or not PASSWORD:
    raise ValueError("Missing ESTELLE_USERNAME or ESTELLE_PASSWORD in .env file")

async def book_court():
    """Execute the booking flow step by step."""

    async with async_playwright() as p:
        # Launch Firefox - visible window, slow motion
        print("🦊 Launching Firefox...")
        browser = await p.firefox.launch(
            headless=False,
            slow_mo=1000  # 1 second delay between actions
        )

        # Create browser context and page
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            # STEP 1: Login
            print("\n📝 Step 1: Logging in...")
            await page.goto('https://home.estellemanor.com/page/login')
            await asyncio.sleep(2)

            await page.fill('input[name="email"]', EMAIL)
            await page.fill('input[name="password"]', PASSWORD)
            await page.click('input[type="submit"]')
            await asyncio.sleep(5)

            # Navigate to homepage to establish session
            await page.goto('https://home.estellemanor.com/')
            await asyncio.sleep(5)
            print("✅ Logged in")

            # STEP 2: Click "Book Now"
            print("\n🔘 Step 2: Clicking 'Book Now'...")
            await page.click('#book-now-button')
            await asyncio.sleep(3)
            print(f"   Current URL: {page.url}")

            # STEP 3: Click "Padel Courts"
            print("\n🎾 Step 3: Clicking 'Padel Courts'...")
            await page.click('a:has-text("Padel Courts")')
            await asyncio.sleep(3)
            print(f"   Current URL: {page.url}")

            # STEP 4: Click "BOOK - 1Hr"
            print("\n⏱️  Step 4: Clicking 'BOOK - 1Hr'...")
            await page.click('a:has-text("BOOK - 1Hr")')
            await asyncio.sleep(5)
            print(f"   Current URL: {page.url}")

            # STEP 5: Dismiss any popups
            print("\n🚫 Step 5: Dismissing popups...")
            for _ in range(3):
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)

            # STEP 6: Fill date
            print(f"\n📅 Step 6: Filling date: {BOOKING_DATE}...")
            await asyncio.sleep(2)

            # Wait for date input to be available
            await page.wait_for_selector('input#from_date', timeout=30000)

            # Fill date using JavaScript
            await page.evaluate(f'document.querySelector("#from_date").value = "{BOOKING_DATE}"')
            await page.evaluate('document.querySelector("#from_date").dispatchEvent(new Event("change", { bubbles: true }))')
            await asyncio.sleep(1)

            # STEP 7: Click "Show Availability"
            print("\n🔍 Step 7: Clicking 'Show Availability'...")
            await page.click('#btnApply')
            await asyncio.sleep(5)
            print("   Waiting for availability to load...")

            # STEP 8: Click the time slot
            print(f"\n🕐 Step 8: Looking for time slot: {BOOKING_TIME}...")
            await asyncio.sleep(2)

            # Find and click the time slot
            time_selector = f'span.slot_start_show:has-text("{BOOKING_TIME}")'
            time_element = page.locator(time_selector).first

            if await time_element.count() > 0:
                print(f"   Found {BOOKING_TIME} - clicking...")
                await time_element.click()
                await asyncio.sleep(3)
                print("✅ Time slot clicked!")
            else:
                print(f"❌ Time slot {BOOKING_TIME} not found!")
                # List available times for debugging
                all_times = await page.locator('span.slot_start_show').all_text_contents()
                print(f"   Available times: {all_times}")

            # STEP 9: Confirm booking (if there's a confirm button)
            print("\n✅ Step 9: Looking for confirmation button...")
            await asyncio.sleep(2)

            # Common confirmation button selectors
            confirm_selectors = [
                'button:has-text("Confirm")',
                'button:has-text("Book")',
                'a:has-text("Confirm")',
                '#btnConfirm',
                '.btn-confirm'
            ]

            for selector in confirm_selectors:
                try:
                    confirm_btn = page.locator(selector).first
                    if await confirm_btn.count() > 0:
                        print(f"   Found confirmation button: {selector}")
                        await confirm_btn.click()
                        await asyncio.sleep(3)
                        print("✅ Booking confirmed!")
                        break
                except:
                    continue

            # Final status
            print("\n" + "=" * 50)
            print("🎉 BOOKING FLOW COMPLETE!")
            print(f"Final URL: {page.url}")
            print("=" * 50)

            # Keep browser open for 30 seconds to see result
            print("\nBrowser will stay open for 30 seconds...")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("\nBrowser will stay open for 60 seconds for debugging...")
            await asyncio.sleep(60)

        finally:
            await browser.close()
            print("\n👋 Browser closed")

if __name__ == '__main__':
    print("=" * 50)
    print("🎾 ESTELLE MANOR PADEL COURT BOOKING")
    print("=" * 50)
    print(f"Date: {BOOKING_DATE}")
    print(f"Time: {BOOKING_TIME}")
    print("=" * 50)

    asyncio.run(book_court())
