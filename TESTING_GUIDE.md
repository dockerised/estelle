# Testing Guide

Complete guide for testing the Padel Court Booking System.

## Prerequisites

Before testing, ensure you have:

1. Docker and Docker Compose installed
2. Your Estelle Manor credentials
3. A Discord webhook URL for notifications
4. `.env` file configured

## Test Plan

### Phase 1: Environment Setup

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env with test credentials**
   ```bash
   nano .env
   ```

3. **Enable dry-run mode for initial testing**
   ```ini
   DRY_RUN=true
   LOG_LEVEL=DEBUG
   ```

### Phase 2: Application Startup

1. **Build Docker image**
   ```bash
   docker-compose build
   ```

2. **Start application**
   ```bash
   docker-compose up -d
   ```

3. **Check logs**
   ```bash
   docker-compose logs -f
   ```

   Expected log output:
   ```
   INFO - FastAPI application starting up
   INFO - APScheduler started
   INFO - Rescheduled 0 pending bookings
   INFO - Application startup complete
   ```

4. **Verify health endpoint**
   ```bash
   curl http://localhost:8000/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "scheduler": "running",
     "bookings": {
       "total": 0,
       "pending": 0,
       "booked": 0,
       "failed": 0
     }
   }
   ```

### Phase 3: Discord Notification Test

1. **Send test notification**
   ```bash
   curl -X POST http://localhost:8000/test/notification
   ```

2. **Check Discord channel**
   - You should receive a test message from "Padel Booking Bot"
   - If not, verify webhook URL in `.env`

### Phase 4: CSV Upload Test

1. **Create test CSV with FUTURE dates**
   ```csv
   Date, Time1, Time2, Status
   2026-02-15, 7pm, 8pm, Book
   2026-02-16, 11am, 12pm, Book
   ```

   Important: Use dates at least 2 weeks in the future!

2. **Upload CSV**
   ```bash
   curl -X POST http://localhost:8000/bookings/upload \
     -F "file=@example_bookings.csv"
   ```

   Expected response:
   ```json
   {
     "success": true,
     "message": "Successfully added 2 bookings",
     "data": {
       "added": 2,
       "skipped": 0,
       "errors": [],
       "total_processed": 2
     }
   }
   ```

3. **Verify bookings were created**
   ```bash
   curl http://localhost:8000/bookings
   ```

4. **Check individual booking**
   ```bash
   curl http://localhost:8000/bookings/1
   ```

   Expected fields:
   - `booking_date`: Target date
   - `time_primary`: First choice time
   - `time_fallback`: Backup time
   - `status`: "scheduled"
   - `execute_at`: 2 weeks before at 23:50

### Phase 5: Scheduling Verification

1. **Check upcoming bookings**
   ```bash
   curl http://localhost:8000/bookings/upcoming/list
   ```

2. **Verify execution time calculation**
   - Booking date: 2026-02-15
   - Expected execution: 2026-02-01 23:50:00
   - Verify this matches the `execute_at` field

3. **Check APScheduler jobs**
   ```bash
   docker-compose logs | grep "Scheduled booking"
   ```

### Phase 6: Dry-Run Booking Test

For this test, you need to manually trigger a booking execution.

**Option A: Modify execution time in database**

1. **Access database**
   ```bash
   docker exec -it padel-booking sqlite3 /app/data/estelle.db
   ```

2. **Update execution time to now + 2 minutes**
   ```sql
   UPDATE bookings
   SET execute_at = datetime('now', '+2 minutes')
   WHERE id = 1;

   SELECT id, booking_date, execute_at FROM bookings;
   .quit
   ```

3. **Restart to reload schedule**
   ```bash
   docker-compose restart
   ```

4. **Watch logs**
   ```bash
   docker-compose logs -f
   ```

5. **Wait for execution** (2 minutes)
   - Watch for login activity
   - Check for "DRY RUN" messages
   - Verify screenshot creation in `data/screenshots/`

**Option B: Use Python to test booking engine directly**

1. **Create test script** (`test_booking.py`):
   ```python
   import asyncio
   from booking_engine import engine
   from database import db

   async def test():
       booking_id = 1
       booking = db.get_booking(booking_id)

       await engine.execute_booking(
           booking_id=booking_id,
           booking_date=booking["booking_date"],
           time_primary=booking["time_primary"],
           time_fallback=booking["time_fallback"]
       )

       await engine.cleanup()

   asyncio.run(test())
   ```

2. **Run inside container**
   ```bash
   docker exec -it padel-booking python test_booking.py
   ```

### Phase 7: Production Test (Live Booking)

⚠️ **CRITICAL: This will attempt a real booking!**

1. **Disable dry-run mode**
   ```bash
   # Edit .env
   DRY_RUN=false

   # Restart
   docker-compose restart
   ```

2. **Upload booking for TONIGHT**
   ```csv
   Date, Time1, Time2, Status
   2026-02-14, 7pm, 8pm, Book
   ```

   Where 2026-02-14 is exactly 2 weeks from today.

3. **Manually trigger execution** (using Option A or B from Phase 6)

4. **Monitor execution**
   ```bash
   docker-compose logs -f
   ```

5. **Verify Discord notification**

6. **Check booking status**
   ```bash
   curl http://localhost:8000/bookings/1
   ```

7. **View screenshot**
   ```bash
   ls -lh data/screenshots/
   ```

8. **Verify on Estelle Manor website**
   - Login to https://home.estellemanor.com
   - Check your bookings

### Phase 8: Error Handling Tests

1. **Test invalid CSV**
   ```csv
   Date, Time1, Status
   invalid-date, 99pm, Book
   ```

   Expected: Graceful error handling

2. **Test unavailable time slot**
   - Create booking for a time that's already fully booked
   - Expected: Fallback to Time2, or Discord notification

3. **Test network issues**
   - Disconnect network briefly during execution
   - Expected: Error logged, Discord notification, screenshot saved

### Phase 9: Cleanup Tests

1. **Cancel a booking**
   ```bash
   curl -X POST http://localhost:8000/bookings/1/cancel
   ```

2. **Delete a booking**
   ```bash
   curl -X DELETE http://localhost:8000/bookings/2
   ```

3. **Verify database**
   ```bash
   docker exec -it padel-booking sqlite3 /app/data/estelle.db
   ```
   ```sql
   SELECT id, status FROM bookings;
   .quit
   ```

### Phase 10: Performance & Reliability

1. **Upload bulk bookings** (50+ rows)
   - Verify all are scheduled correctly
   - Check memory usage: `docker stats padel-booking`

2. **Restart test**
   ```bash
   docker-compose restart
   ```
   - Verify bookings are rescheduled
   - Check logs for "Rescheduled X pending bookings"

3. **Container crash recovery**
   ```bash
   docker-compose down
   docker-compose up -d
   ```
   - Verify all scheduled bookings are restored

## Test Checklist

- [ ] Environment setup complete
- [ ] Application starts successfully
- [ ] Health check passes
- [ ] Discord notifications work
- [ ] CSV upload successful
- [ ] Bookings scheduled correctly
- [ ] Execution time calculated properly (2 weeks before at 11:50pm)
- [ ] Dry-run booking test passes
- [ ] Screenshots saved on execution
- [ ] Login successful
- [ ] Booking page navigation works
- [ ] Time slot detection works
- [ ] Fallback logic works (Time1 → Time2)
- [ ] Confirmation verification works
- [ ] Discord notifications sent on success/failure
- [ ] Production booking test successful (optional)
- [ ] Error handling works
- [ ] Cancel/delete operations work
- [ ] Application survives restarts

## Common Issues

### Login Fails
- Verify credentials in `.env`
- Check if Estelle Manor site is accessible
- Delete stale session: `rm data/browser_state.json`

### Time Slot Not Found
- Verify date format (YYYY-MM-DD)
- Check time format ("7pm", "11am")
- Enable DEBUG logging to see HTML content

### Discord Notifications Not Sent
- Test webhook URL manually
- Check webhook permissions
- Verify URL has no extra spaces/characters

### Execution Time Wrong
- Check system timezone
- Verify booking date is at least 2 weeks in future
- Check `execute_at` field in database

### Browser Crashes
- Check Docker memory limits
- View Playwright logs
- Try non-headless mode for debugging

## Debug Mode

Enable maximum logging:

```bash
# .env
DRY_RUN=true
LOG_LEVEL=DEBUG
```

View detailed logs:
```bash
docker-compose logs -f | grep -i "playwright\|booking\|schedule"
```

Access container for debugging:
```bash
docker exec -it padel-booking bash
```

## Success Criteria

The system is ready for production when:

1. ✅ All Phase 1-6 tests pass
2. ✅ At least one successful dry-run execution
3. ✅ Discord notifications work reliably
4. ✅ Application survives restart with bookings intact
5. ✅ Screenshots are captured on both success and failure
6. ✅ Database logs show complete execution trace
7. ✅ No errors in logs during normal operation

## Production Deployment

Once testing is complete:

1. Set `DRY_RUN=false` in `.env`
2. Set `LOG_LEVEL=INFO`
3. Upload your real booking CSV
4. Monitor first few executions closely
5. Set up daily summary schedule (optional)

## Monitoring in Production

Daily checks:
```bash
# Check health
curl http://localhost:8000/health

# View statistics
curl http://localhost:8000/stats

# Check upcoming bookings
curl http://localhost:8000/bookings/upcoming/list

# View recent logs
docker-compose logs --tail=100
```

Weekly checks:
- Review failed bookings
- Check screenshot folder size
- Verify database size
- Test Discord webhook still works
