"""
Calendar invite generation utilities for padel court bookings.

Generates RFC 5545 compliant .ics files for booking confirmations.
"""

import logging
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Alarm

logger = logging.getLogger(__name__)


class CalendarInviteGenerator:
    """Generate calendar invite files for padel court bookings."""

    TIMEZONE = ZoneInfo("Europe/London")
    DEFAULT_DURATION_HOURS = 1
    REMINDER_MINUTES_BEFORE = 60
    LOCATION = "Estelle Manor Padel Courts"

    def parse_time_to_datetime(self, booking_date: str, booking_time: str) -> datetime:
        """
        Convert booking date and time strings to timezone-aware datetime.

        Args:
            booking_date: Date in "YYYY-MM-DD" format (e.g., "2026-02-17")
            booking_time: Time in "10am", "7pm", or "7:30pm" format

        Returns:
            Timezone-aware datetime object in Europe/London timezone

        Raises:
            ValueError: If time format is invalid
        """
        try:
            # Parse time string
            time_str = booking_time.lower().strip()

            # Handle am/pm format
            if 'am' in time_str or 'pm' in time_str:
                is_pm = 'pm' in time_str
                time_str = time_str.replace('am', '').replace('pm', '').strip()

                # Parse hour and optional minutes
                if ':' in time_str:
                    hour_str, minute_str = time_str.split(':')
                    hour = int(hour_str)
                    minute = int(minute_str)
                else:
                    hour = int(time_str)
                    minute = 0

                # Convert to 24-hour format
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
            else:
                raise ValueError(f"Invalid time format: {booking_time}")

            # Validate hour and minute
            if not (0 <= hour < 24):
                raise ValueError(f"Hour must be between 0-23: {hour}")
            if not (0 <= minute < 60):
                raise ValueError(f"Minute must be between 0-59: {minute}")

            # Parse date and combine with time
            date_obj = datetime.strptime(booking_date, "%Y-%m-%d").date()
            dt = datetime.combine(date_obj, datetime.min.time().replace(hour=hour, minute=minute))

            # Make timezone-aware
            return dt.replace(tzinfo=self.TIMEZONE)

        except (ValueError, AttributeError) as e:
            raise ValueError(f"Failed to parse time '{booking_time}': {e}")

    def generate_ics(
        self,
        booking_date: str,
        booking_time: str,
        court_name: str,
        duration_hours: int = None
    ) -> BytesIO:
        """
        Generate .ics calendar file for a booking.

        Args:
            booking_date: Date in "YYYY-MM-DD" format
            booking_time: Time in "10am", "7pm", or "7:30pm" format
            court_name: Name of the booked court
            duration_hours: Duration in hours (default: 1)

        Returns:
            BytesIO object containing .ics file data

        Raises:
            ValueError: If date/time parsing fails
        """
        if duration_hours is None:
            duration_hours = self.DEFAULT_DURATION_HOURS

        try:
            # Parse start time
            start_dt = self.parse_time_to_datetime(booking_date, booking_time)
            end_dt = start_dt + timedelta(hours=duration_hours)

            # Create calendar
            cal = Calendar()
            cal.add('prodid', '-//Padel Court Booking System//EN')
            cal.add('version', '2.0')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')

            # Create event
            event = Event()
            event.add('summary', f'Padel Court Booking - {court_name}')
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event.add('dtstamp', datetime.now(tz=self.TIMEZONE))
            event.add('location', self.LOCATION)
            event.add('status', 'CONFIRMED')
            event.add('transp', 'OPAQUE')  # Show as busy

            # Add description
            description = (
                f"Padel Court Booking Confirmation\n\n"
                f"Date: {booking_date}\n"
                f"Time: {booking_time}\n"
                f"Court: {court_name}\n"
                f"Location: {self.LOCATION}\n"
                f"Duration: {duration_hours} hour(s)"
            )
            event.add('description', description)

            # Add reminder alarm (1 hour before)
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', f'Padel Court Booking - {court_name}')
            alarm.add('trigger', timedelta(minutes=-self.REMINDER_MINUTES_BEFORE))
            event.add_component(alarm)

            # Add event to calendar
            cal.add_component(event)

            # Generate .ics file in memory
            ics_data = cal.to_ical()
            return BytesIO(ics_data)

        except Exception as e:
            logger.error(f"Failed to generate calendar invite: {e}")
            raise

    def generate_filename(self, booking_date: str, booking_time: str) -> str:
        """
        Generate descriptive filename for .ics file.

        Args:
            booking_date: Date in "YYYY-MM-DD" format
            booking_time: Time in "10am", "7pm", etc. format

        Returns:
            Filename like "padel_booking_2026-02-17_10am.ics"
        """
        # Sanitize time for filename (remove colons)
        time_safe = booking_time.lower().replace(':', '').replace(' ', '')
        return f"padel_booking_{booking_date}_{time_safe}.ics"


# Singleton instance
calendar_generator = CalendarInviteGenerator()
