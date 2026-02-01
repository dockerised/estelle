# Padel Court Booking Automation

Automated booking system for Padel courts at Estelle Manor using Playwright and FastAPI.

## Features

- 🤖 **Automated Booking**: Automatically books Padel courts at midnight when slots are released
- 📅 **2-Week Booking Window**: Handles the 2-week advance booking constraint
- ⏰ **Smart Scheduling**: Logs in at 11:50pm, prepares the booking page, then submits at midnight
- 🔄 **Fallback Times**: Supports primary and fallback time slot preferences
- 📊 **REST API**: Upload booking CSVs, view status, manage bookings
- 💬 **Discord Notifications**: Real-time alerts for booking success/failure
- 🧪 **Dry-Run Mode**: Test the system without actually completing bookings
- 🐳 **Docker Ready**: Containerized deployment with docker-compose

## Quick Start

### 1. Setup Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
- `ESTELLE_USERNAME`: Your Estelle Manor username
- `ESTELLE_PASSWORD`: Your Estelle Manor password
- `DISCORD_WEBHOOK_URL`: Your Discord webhook URL for notifications

### 2. Run with Docker

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

### 3. Upload Bookings

Create a CSV file (`bookings.csv`):

```csv
Date, Time1, Time2, Status
2026-02-15, 7pm, 8pm, Book
2026-02-16, 11am, 12pm, Book
2026-02-20, 6pm, 7pm, Book
```

Upload via API:

```bash
curl -X POST http://localhost:8000/bookings/upload \
  -F "file=@bookings.csv"
```

## API Endpoints

### Upload Bookings
```bash
POST /bookings/upload
Content-Type: multipart/form-data
```

### List Bookings
```bash
GET /bookings?status=pending
GET /bookings?status=booked
```

### Get Booking Details
```bash
GET /bookings/{id}
```

### Delete Booking
```bash
DELETE /bookings/{id}
```

### Cancel Booking
```bash
POST /bookings/{id}/cancel
```

### Get Statistics
```bash
GET /stats
```

### Health Check
```bash
GET /health
```

### Test Notification
```bash
POST /test/notification
```

## CSV Format

The booking CSV must have these columns:

| Column | Required | Example | Description |
|--------|----------|---------|-------------|
| Date | Yes | 2026-02-15 | Booking date (YYYY-MM-DD) |
| Time1 | Yes | 7pm | Primary desired time |
| Time2 | No | 8pm | Fallback time if Time1 unavailable |
| Status | Yes | Book | Must be "Book" to process |

Supported time formats:
- `7pm`, `8pm`, `11pm`
- `11am`, `12pm`, `1pm`
- `7:30pm`, `8:00am`

## How It Works

1. **CSV Upload**: Upload a CSV with your desired booking dates and times
2. **Scheduling**: System calculates when to execute (2 weeks before, at 11:50pm)
3. **Pre-Login**: At 11:50pm, logs into Estelle Manor and navigates to booking page
4. **Midnight Submission**: At 00:00:00, fills date and clicks "Show Availability"
5. **Slot Selection**: Finds and clicks your preferred time slot (Time1 or Time2)
6. **Confirmation**: Verifies booking confirmation page appears
7. **Notification**: Sends Discord notification with booking result

## Configuration

Edit `.env` to customize:

```bash
# Credentials
ESTELLE_USERNAME=your@email.com
ESTELLE_PASSWORD=your_password

# Discord webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Application settings
DRY_RUN=false          # Set to true to test without booking
LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR
PRE_LOGIN_MINUTES=10   # Minutes before midnight to login

# API settings
API_HOST=0.0.0.0
API_PORT=8000
```

## Dry-Run Mode

Test the system without actually completing bookings:

```bash
# Set in .env
DRY_RUN=true

# Or via environment variable
docker-compose run -e DRY_RUN=true padel-booking
```

In dry-run mode:
- ✅ Logs in and navigates pages
- ✅ Finds available time slots
- ✅ Takes screenshots
- ❌ Does NOT click to book
- ✅ Sends test notifications

## Discord Webhook Setup

1. Go to your Discord server settings
2. Navigate to Integrations → Webhooks
3. Create a new webhook
4. Copy the webhook URL
5. Add to `.env` as `DISCORD_WEBHOOK_URL`

## Monitoring

### View Logs
```bash
docker-compose logs -f
```

### Check Status
```bash
curl http://localhost:8000/health
```

### View Statistics
```bash
curl http://localhost:8000/stats
```

### Get Upcoming Bookings
```bash
curl http://localhost:8000/bookings/upcoming/list
```

## Troubleshooting

### Booking Failed to Confirm
- Check logs: `docker-compose logs -f`
- View screenshot: `data/screenshots/`
- Enable DEBUG logging: `LOG_LEVEL=DEBUG`

### Login Issues
- Verify credentials in `.env`
- Check if session state is corrupt: `rm data/browser_state.json`
- Run in non-headless mode for debugging

### Time Slot Not Found
- Check date format (YYYY-MM-DD)
- Verify time format (e.g., "7pm", "11am")
- Ensure court is available (not fully booked)

### Discord Notifications Not Working
- Test webhook: `curl -X POST http://localhost:8000/test/notification`
- Verify webhook URL in `.env`
- Check Discord server permissions

## Development

### Local Setup (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create directories
mkdir -p data/screenshots logs

# Run application
python app.py
```

### Run Tests

```bash
# Set dry-run mode
export DRY_RUN=true

# Upload test booking
curl -X POST http://localhost:8000/bookings/upload \
  -F "file=@test_bookings.csv"

# Check execution
curl http://localhost:8000/bookings
```

## File Structure

```
gc-estelle/
├── app.py                  # Main entry point
├── config.py               # Configuration management
├── database.py             # SQLite operations
├── booking_engine.py       # Playwright automation
├── scheduler.py            # APScheduler booking queue
├── api.py                  # FastAPI endpoints
├── notifications.py        # Discord notifications
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker compose config
├── .env                    # Environment variables (create from .env.example)
├── data/
│   ├── estelle.db          # SQLite database
│   ├── browser_state.json  # Saved browser session
│   └── screenshots/        # Error screenshots
└── logs/
    └── booking.log         # Application logs
```

## Database Schema

### bookings table
- `id`: Unique booking ID
- `booking_date`: Target date to book (YYYY-MM-DD)
- `time_primary`: Primary desired time
- `time_fallback`: Fallback time (optional)
- `status`: pending, scheduled, booked, failed, cancelled
- `execute_at`: When to execute the booking (ISO timestamp)
- `court_name`: Booked court name (after booking)
- `booked_time`: Actual booked time
- `created_at`: When booking was created
- `updated_at`: Last update time
- `error_message`: Error details (if failed)
- `screenshot_path`: Screenshot path (if available)

### execution_log table
- `id`: Log entry ID
- `booking_id`: Related booking
- `timestamp`: When action occurred
- `action`: Action type (login, prepare_page, booking, etc.)
- `result`: Result (success, failed, error)
- `details`: Additional details
- `screenshot_path`: Screenshot path (if available)

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. View screenshots: `data/screenshots/`
3. Check booking details: `curl http://localhost:8000/bookings/{id}`

## License

MIT License - see LICENSE file for details
