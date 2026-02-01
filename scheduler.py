"""APScheduler booking scheduler for automated Padel court bookings."""
import asyncio
import logging
import csv
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import settings
from database import db
from booking_engine import engine
from notifications import notifier
from events_monitor import events_monitor

logger = logging.getLogger(__name__)


class BookingScheduler:
    """Manages booking queue and schedules executions."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        logger.info("APScheduler started")

        # Setup events monitoring if enabled
        self.setup_events_monitoring()

    def parse_csv_content(self, csv_content: str) -> List[Dict[str, str]]:
        """
        Parse CSV content into booking entries.
        Expected format: Date, Time1, Time2, Status
        """
        bookings = []
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
            # Clean up field names (strip whitespace)
            cleaned_row = {k.strip(): v.strip() for k, v in row.items()}

            # Validate required fields
            if "Date" not in cleaned_row or "Time1" not in cleaned_row:
                logger.warning(f"Skipping invalid row: {cleaned_row}")
                continue

            # Only process rows with Status = 'Book' (case insensitive)
            status = cleaned_row.get("Status", "").lower()
            if status != "book":
                logger.debug(f"Skipping row with status: {status}")
                continue

            bookings.append({
                "date": cleaned_row["Date"],
                "time_primary": cleaned_row["Time1"],
                "time_fallback": cleaned_row.get("Time2", "").strip() or None,
            })

        logger.info(f"Parsed {len(bookings)} bookings from CSV")
        return bookings

    def calculate_execution_time(self, booking_date: str) -> datetime:
        """
        Calculate when to execute the booking.
        Execute 15 days before the booking date (2-week window), at 11:50pm.
        This accounts for the fact that courts become available at midnight
        15 days before the booking date.
        """
        target_date = datetime.strptime(booking_date, "%Y-%m-%d")

        # 15 days before (courts released at midnight, we login 10 mins before)
        execution_date = target_date - timedelta(days=15)

        # Set time to 11:50pm (23:50)
        # Use pre_login_minutes setting (default 10 minutes before midnight)
        minutes_before = settings.pre_login_minutes
        execution_time = execution_date.replace(
            hour=23,
            minute=60 - minutes_before,
            second=0,
            microsecond=0
        )

        logger.info(
            f"Booking for {booking_date} scheduled at "
            f"{execution_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return execution_time

    async def add_bookings_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """
        Add bookings from CSV content.
        Returns summary of added bookings.
        """
        try:
            bookings = self.parse_csv_content(csv_content)

            added = 0
            skipped = 0
            errors = []

            for booking in bookings:
                try:
                    execution_time = self.calculate_execution_time(booking["date"])

                    # Check if execution time is in the past
                    if execution_time < datetime.now():
                        logger.warning(
                            f"Skipping booking for {booking['date']} - "
                            f"execution time has passed"
                        )
                        skipped += 1
                        continue

                    # Create booking in database
                    booking_id = db.create_booking(
                        booking_date=booking["date"],
                        time_primary=booking["time_primary"],
                        time_fallback=booking["time_fallback"],
                        execute_at=execution_time.isoformat()
                    )

                    # Schedule the booking execution
                    self.schedule_booking(booking_id, execution_time)

                    added += 1
                    logger.info(f"Added booking ID {booking_id} for {booking['date']}")

                except Exception as e:
                    error_msg = f"Error adding booking for {booking.get('date', 'unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            result = {
                "added": added,
                "skipped": skipped,
                "errors": errors,
                "total_processed": len(bookings)
            }

            logger.info(
                f"CSV import complete: {added} added, {skipped} skipped, "
                f"{len(errors)} errors"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
            raise

    def schedule_booking(self, booking_id: int, execution_time: datetime):
        """Schedule a booking execution."""
        try:
            # Get booking details
            booking = db.get_booking(booking_id)
            if not booking:
                logger.error(f"Booking ID {booking_id} not found")
                return

            # Create APScheduler job
            job_id = f"booking_{booking_id}"

            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Schedule new job
            self.scheduler.add_job(
                func=self._execute_booking_wrapper,
                trigger=DateTrigger(run_date=execution_time),
                args=[booking_id],
                id=job_id,
                name=f"Booking {booking_id} for {booking['booking_date']}",
                replace_existing=True
            )

            logger.info(
                f"Scheduled booking {booking_id} for execution at "
                f"{execution_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Update status to 'scheduled'
            db.update_booking_status(booking_id, "scheduled")

        except Exception as e:
            logger.error(f"Failed to schedule booking {booking_id}: {e}")
            db.update_booking_status(booking_id, "failed", error_message=str(e))

    async def _execute_booking_wrapper(self, booking_id: int):
        """
        Wrapper for booking execution (called by APScheduler).
        APScheduler doesn't directly support async functions well, so we wrap it.
        """
        try:
            logger.info(f"Executing booking ID {booking_id}")

            booking = db.get_booking(booking_id)
            if not booking:
                logger.error(f"Booking ID {booking_id} not found")
                return

            # Execute the booking
            await engine.execute_booking(
                booking_id=booking_id,
                booking_date=booking["booking_date"],
                time_primary=booking["time_primary"],
                time_fallback=booking["time_fallback"]
            )

        except Exception as e:
            logger.error(f"Error executing booking {booking_id}: {e}")
            db.update_booking_status(booking_id, "failed", error_message=str(e))
            await notifier.system_error(
                f"Failed to execute booking {booking_id}",
                str(e)
            )

    def reschedule_pending_bookings(self):
        """
        Reschedule all pending bookings on startup.
        This ensures bookings survive application restarts.
        """
        try:
            # Get all pending/scheduled bookings
            pending = db.get_all_bookings("pending") + db.get_all_bookings("scheduled")

            rescheduled = 0
            for booking in pending:
                execution_time = datetime.fromisoformat(booking["execute_at"])

                # Skip if execution time has passed
                if execution_time < datetime.now():
                    logger.warning(
                        f"Booking {booking['id']} execution time has passed, "
                        f"marking as failed"
                    )
                    db.update_booking_status(
                        booking["id"],
                        "failed",
                        error_message="Execution time passed"
                    )
                    continue

                self.schedule_booking(booking["id"], execution_time)
                rescheduled += 1

            logger.info(f"Rescheduled {rescheduled} pending bookings")

        except Exception as e:
            logger.error(f"Error rescheduling pending bookings: {e}")

    def get_upcoming_bookings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming scheduled bookings."""
        pending = db.get_all_bookings("scheduled")
        pending.sort(key=lambda x: x["execute_at"])
        return pending[:limit]

    def cancel_booking(self, booking_id: int) -> bool:
        """Cancel a scheduled booking."""
        try:
            booking = db.get_booking(booking_id)
            if not booking:
                logger.error(f"Booking {booking_id} not found")
                return False

            # Remove from scheduler
            job_id = f"booking_{booking_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Update database
            db.update_booking_status(booking_id, "cancelled")

            logger.info(f"Cancelled booking {booking_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling booking {booking_id}: {e}")
            return False

    def delete_booking(self, booking_id: int) -> bool:
        """Delete a booking completely."""
        try:
            # Remove from scheduler
            job_id = f"booking_{booking_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Delete from database
            db.delete_booking(booking_id)

            logger.info(f"Deleted booking {booking_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting booking {booking_id}: {e}")
            return False

    async def send_daily_summary(self):
        """Send daily summary notification."""
        try:
            stats = db.get_stats()
            await notifier.daily_summary(stats)
            logger.info("Daily summary sent")
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    def setup_events_monitoring(self):
        """Setup periodic events monitoring job."""
        if not settings.events_monitoring_enabled:
            logger.info("Events monitoring is disabled")
            return

        # Add periodic job to check for events
        self.scheduler.add_job(
            func=self._check_events_wrapper,
            trigger=IntervalTrigger(hours=settings.events_check_interval_hours),
            id='events_monitoring',
            name='Check What\'s On for new events',
            replace_existing=True
        )

        logger.info(
            f"Events monitoring enabled - checking every "
            f"{settings.events_check_interval_hours} hours"
        )

        # Run initial check after 10 seconds
        from datetime import datetime, timedelta
        initial_run = datetime.now() + timedelta(seconds=10)
        self.scheduler.add_job(
            func=self._check_events_wrapper,
            trigger=DateTrigger(run_date=initial_run),
            id='events_monitoring_initial',
            name='Initial events check'
        )
        logger.info("Scheduled initial events check in 10 seconds")

    async def _check_events_wrapper(self):
        """Wrapper for events checking."""
        try:
            logger.info("Running periodic events check")
            await events_monitor.check_for_new_events()
        except Exception as e:
            logger.error(f"Error in events monitoring: {e}")
            await notifier.system_error("Events monitoring failed", str(e))

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        logger.info("Shutting down scheduler")
        self.scheduler.shutdown(wait=True)


# Global scheduler instance
scheduler = BookingScheduler()
