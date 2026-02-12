"""Redis-based persistence for bookings across scale-to-zero cycles."""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import redis
from config import settings

logger = logging.getLogger(__name__)


class RedisBookingStore:
    """Persistent booking storage using Redis."""

    def __init__(self, redis_url: str = None):
        """Initialize Redis connection."""
        self.redis_url = redis_url or settings.redis_url
        self._client = None
        self.key_prefix = "estelle:booking:"
        self.queue_key = "estelle:booking_queue"

    def connect(self):
        """Connect to Redis."""
        try:
            self._client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self._client.ping()
            logger.info(f"✅ Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self._client = None
            return False

    @property
    def client(self):
        """Get Redis client, connecting if needed."""
        if self._client is None:
            self.connect()
        return self._client

    def save_booking(self, booking: Dict) -> bool:
        """
        Save a booking to Redis.

        Args:
            booking: Dict with keys: id, booking_date, time_primary, time_fallback,
                    status, execute_at, etc.
        """
        try:
            if not self.client:
                logger.error("Redis not connected, cannot save booking")
                return False

            booking_id = booking['id']
            key = f"{self.key_prefix}{booking_id}"

            # Save booking data
            self.client.set(key, json.dumps(booking))

            # Add to queue if status is 'pending' or 'scheduled'
            if booking.get('status') in ['pending', 'scheduled']:
                self.client.sadd(self.queue_key, booking_id)
                logger.info(f"✅ Saved booking {booking_id} to Redis queue")

            return True

        except Exception as e:
            logger.error(f"Failed to save booking to Redis: {e}")
            return False

    def get_booking(self, booking_id: int) -> Optional[Dict]:
        """Get a booking by ID from Redis."""
        try:
            if not self.client:
                return None

            key = f"{self.key_prefix}{booking_id}"
            data = self.client.get(key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            logger.error(f"Failed to get booking from Redis: {e}")
            return None

    def get_pending_bookings(self) -> List[Dict]:
        """Get all pending bookings from Redis queue."""
        try:
            if not self.client:
                return []

            # Get all booking IDs from queue
            booking_ids = self.client.smembers(self.queue_key)

            bookings = []
            for booking_id in booking_ids:
                booking = self.get_booking(int(booking_id))
                if booking and booking.get('status') in ['pending', 'scheduled']:
                    bookings.append(booking)
                else:
                    # Remove from queue if not pending/scheduled
                    self.client.srem(self.queue_key, booking_id)

            logger.info(f"📋 Found {len(bookings)} pending bookings in Redis")
            return bookings

        except Exception as e:
            logger.error(f"Failed to get pending bookings: {e}")
            return []

    def update_booking_status(self, booking_id: int, status: str, **kwargs) -> bool:
        """Update booking status and additional fields."""
        try:
            booking = self.get_booking(booking_id)
            if not booking:
                logger.warning(f"Booking {booking_id} not found in Redis")
                return False

            # Update fields
            booking['status'] = status
            booking['updated_at'] = datetime.now().isoformat()

            for key, value in kwargs.items():
                booking[key] = value

            # Save updated booking
            self.save_booking(booking)

            # Remove from queue if no longer pending/scheduled
            if status not in ['pending', 'scheduled']:
                self.client.srem(self.queue_key, booking_id)
                logger.info(f"Removed booking {booking_id} from queue (status: {status})")

            return True

        except Exception as e:
            logger.error(f"Failed to update booking status: {e}")
            return False

    def delete_booking(self, booking_id: int) -> bool:
        """Delete a booking from Redis."""
        try:
            if not self.client:
                return False

            key = f"{self.key_prefix}{booking_id}"
            self.client.delete(key)
            self.client.srem(self.queue_key, booking_id)

            logger.info(f"🗑️ Deleted booking {booking_id} from Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to delete booking: {e}")
            return False

    def get_next_booking_id(self) -> int:
        """Get next available booking ID."""
        try:
            if not self.client:
                return 1

            counter_key = f"{self.key_prefix}counter"
            return self.client.incr(counter_key)

        except Exception as e:
            logger.error(f"Failed to get next booking ID: {e}")
            return 1


# Global Redis store instance
redis_store = RedisBookingStore()
