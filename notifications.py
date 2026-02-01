"""Discord webhook notifications."""
import httpx
import logging
from typing import Optional
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send notifications via Discord webhook."""

    def __init__(self, webhook_url: str = settings.discord_webhook_url):
        self.webhook_url = webhook_url

    async def send_message(
        self,
        content: str,
        embeds: Optional[list] = None,
        username: str = "Padel Booking Bot"
    ) -> bool:
        """Send a message to Discord."""
        try:
            payload = {
                "username": username,
                "content": content,
            }
            if embeds:
                payload["embeds"] = embeds

            async with httpx.AsyncClient() as client:
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
        """Notify about successful booking."""
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

        await self.send_message(
            content="🎾 **Padel court booked successfully!**",
            embeds=[embed]
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
