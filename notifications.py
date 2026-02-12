"""Discord webhook notifications."""
import httpx
import logging
from typing import Optional, Dict
from datetime import datetime
from io import BytesIO
from config import settings
from calendar_utils import calendar_generator

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send notifications via Discord webhook."""

    def __init__(self, webhook_url: str = settings.discord_webhook_url):
        self.webhook_url = webhook_url

    async def send_message(
        self,
        content: str,
        embeds: Optional[list] = None,
        username: str = "Padel Booking Bot",
        files: Optional[Dict[str, BytesIO]] = None
    ) -> bool:
        """
        Send a message to Discord.

        Args:
            content: Message content
            embeds: List of embed objects
            username: Bot username to display
            files: Optional dict of filename -> BytesIO file data for attachments

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            payload = {
                "username": username,
                "content": content,
            }
            if embeds:
                payload["embeds"] = embeds

            async with httpx.AsyncClient() as client:
                if files:
                    # Use multipart/form-data for file attachments
                    import json

                    # Prepare files for multipart upload
                    files_data = {}
                    for idx, (filename, file_data) in enumerate(files.items()):
                        file_data.seek(0)  # Reset file pointer
                        files_data[f'files[{idx}]'] = (filename, file_data, 'text/calendar')

                    # JSON payload goes in payload_json field
                    multipart_data = {
                        'payload_json': json.dumps(payload)
                    }

                    response = await client.post(
                        self.webhook_url,
                        data=multipart_data,
                        files=files_data,
                        timeout=10.0
                    )
                else:
                    # Standard JSON request
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        timeout=10.0
                    )

                response.raise_for_status()
                logger.info("Discord notification sent successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    async def booking_success(
        self,
        booking_date: str,
        booked_time: str,
        court_name: Optional[str] = None
    ):
        """Notify about successful booking with calendar invite attachment."""
        embed = {
            "title": "✅ Booking Successful!",
            "color": 3066993,  # Green
            "fields": [
                {"name": "Date", "value": booking_date, "inline": True},
                {"name": "Time", "value": booked_time, "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        if court_name:
            embed["fields"].append(
                {"name": "Court", "value": court_name, "inline": False}
            )

        # Generate calendar invite file
        files = None
        try:
            ics_file = calendar_generator.generate_ics(
                booking_date=booking_date,
                booking_time=booked_time,
                court_name=court_name or "TBD"
            )
            filename = calendar_generator.generate_filename(booking_date, booked_time)
            files = {filename: ics_file}

            # Add calendar field to embed
            embed["fields"].append(
                {"name": "📅 Calendar", "value": "Download the attached .ics file to add to your calendar", "inline": False}
            )

            logger.info(f"Generated calendar invite: {filename}")

        except Exception as e:
            # Graceful fallback: send notification without calendar attachment
            logger.error(f"Failed to generate calendar invite: {e}", exc_info=True)

        await self.send_message(
            content="🎾 **Padel court booked successfully!**",
            embeds=[embed],
            files=files
        )

    async def booking_failed(
        self,
        booking_date: str,
        time_primary: str,
        time_fallback: Optional[str],
        error_message: str
    ):
        """Notify about booking failure."""
        times_attempted = time_primary
        if time_fallback:
            times_attempted += f", {time_fallback}"

        embed = {
            "title": "❌ Booking Failed",
            "color": 15158332,  # Red
            "fields": [
                {"name": "Date", "value": booking_date, "inline": True},
                {"name": "Times Attempted", "value": times_attempted, "inline": True},
                {"name": "Error", "value": error_message, "inline": False},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.send_message(
            content="⚠️ **Failed to book Padel court**",
            embeds=[embed]
        )

    async def booking_unavailable(
        self,
        booking_date: str,
        time_primary: str,
        time_fallback: Optional[str]
    ):
        """Notify when both time slots are unavailable."""
        times = time_primary
        if time_fallback:
            times += f" and {time_fallback}"

        embed = {
            "title": "⏰ No Availability",
            "color": 16776960,  # Yellow/Orange
            "fields": [
                {"name": "Date", "value": booking_date, "inline": True},
                {"name": "Times Requested", "value": times, "inline": True},
                {"name": "Status", "value": "Both time slots are fully booked", "inline": False},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.send_message(
            content="📅 **Requested time slots are unavailable**",
            embeds=[embed]
        )

    async def system_error(self, error_message: str, details: Optional[str] = None):
        """Notify about system errors."""
        embed = {
            "title": "🚨 System Error",
            "color": 10038562,  # Dark red
            "fields": [
                {"name": "Error", "value": error_message, "inline": False},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        if details:
            embed["fields"].append(
                {"name": "Details", "value": details[:1000], "inline": False}
            )

        await self.send_message(
            content="⚠️ **Booking system encountered an error**",
            embeds=[embed]
        )

    async def daily_summary(self, stats: dict):
        """Send daily summary of bookings."""
        embed = {
            "title": "📊 Daily Booking Summary",
            "color": 3447003,  # Blue
            "fields": [
                {"name": "Total Bookings", "value": str(stats["total"]), "inline": True},
                {"name": "Pending", "value": str(stats["pending"]), "inline": True},
                {"name": "Booked", "value": str(stats["booked"]), "inline": True},
                {"name": "Failed", "value": str(stats["failed"]), "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.send_message(
            content="📈 **Daily booking statistics**",
            embeds=[embed]
        )


# Global notifier instance
notifier = DiscordNotifier()
