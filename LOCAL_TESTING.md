# Local Testing Guide

## Running the Booking Bot Locally with Visible Browser

This guide explains how to run the booking bot on your local machine with a visible browser window for debugging and testing.

## Files for Local Development

- `booking_engine_local.py` - Modified booking engine that runs in visible (non-headless) mode
- `test_local_booking.py` - Simple test script to run a booking locally

## Prerequisites

1. Make sure you have all dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure you have a `.env` file with your credentials:
   ```
   ESTELLE_USERNAME=your.email@example.com
   ESTELLE_PASSWORD=your_password
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

## Running a Test Booking Locally

### Option 1: Quick Test with Visible Browser

Simply run:
```bash
python test_local_booking.py
```

This will:
- Open a visible Chrome browser window
- Login to Estelle Manor
- Navigate to the booking page
- Attempt to book (modify dates in the script as needed)
- Show you exactly what's happening in real-time
- Run slowly (500ms delays) so you can see each step

**You'll be able to see:**
- If the login works
- If the site redirects you
- What the booking page looks like
- Any popups or overlays that might be blocking
- Exactly where it fails (if it does)

### Option 2: Using the Local Engine in Your Own Code

```python
from booking_engine_local import BookingEngine

# Create instance
engine = BookingEngine()

# Run your booking logic
# The browser will be visible on your screen
```

## Key Differences from Cloud/Headless Version

| Feature | Cloud Version (`booking_engine.py`) | Local Version (`booking_engine_local.py`) |
|---------|-------------------------------------|-------------------------------------------|
| Browser Mode | Headless (invisible) | Headed (visible window) |
| Speed | Full speed | Slow motion (500ms delays) |
| Display | Xvfb virtual display | Your actual screen |
| Use Case | Production/automated | Development/debugging |
| Detection Risk | Higher (headless detection) | Lower (real browser) |

## Troubleshooting Local Tests

### Browser doesn't open
- Make sure you have a display/GUI environment (not SSH without X forwarding)
- On Linux, ensure X11 is running
- On WSL, you may need to install an X server

### Playwright browser not found
```bash
playwright install chromium
```

### Permission errors on screenshots
```bash
mkdir -p data/screenshots
chmod 755 data/screenshots
```

## Debugging Tips

1. **Watch the browser** - The visible window lets you see exactly what the bot sees
2. **Check for redirects** - If the booking page shows the homepage, you're being redirected
3. **Look for popups** - Cookie banners, newsletters, etc. that might block elements
4. **Verify selectors** - The browser console (F12) can help check if `#from_date` exists
5. **Check timing** - Sometimes waiting longer helps (modify `asyncio.sleep()` values)

## Comparing Cloud vs Local Behavior

If the booking works locally but fails in the cloud, the issue is likely:
- **Headless detection** - Site detects automated headless browsers
- **IP-based blocking** - Cloud datacenter IPs are flagged
- **TLS fingerprinting** - Different TLS signatures between environments
- **Timing differences** - Cloud might be slower/faster affecting race conditions

## Next Steps After Local Testing

If it works locally:
1. The code logic is correct
2. The selectors are correct
3. The issue is environment-specific (headless/cloud detection)
4. Consider solutions:
   - Use a residential proxy
   - Use a browser automation service
   - Run it locally on a schedule (cron job)
   - Contact Estelle Manor for API access

If it fails locally too:
1. Check if login is actually working
2. Verify the booking URL is correct
3. Check if site structure has changed
4. Look for new security measures on the site
