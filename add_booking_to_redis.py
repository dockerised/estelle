#!/usr/bin/env python3
"""
Add bookings directly to Redis (works even when workload is scaled to 0).
Usage: python add_booking_to_redis.py "2026-03-15" "10am" "12pm"
"""
import sys
import json
from datetime import datetime, timedelta
import redis

REDIS_URL = "redis://redis-shared.dev.cpln.local:6379"


def add_booking(booking_date: str, time_primary: str, time_fallback: str = None):
    """Add a booking directly to Redis."""

    # Connect to Redis
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    try:
        client.ping()
        print(f"✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return False

    # Get next booking ID
    booking_id = client.incr("estelle:booking:counter")

    # Calculate execution time (11:50 PM the day before)
    booking_dt = datetime.strptime(booking_date, "%Y-%m-%d")
    execute_dt = booking_dt.replace(hour=23, minute=50) - timedelta(days=1)

    # Create booking data
    now = datetime.now().isoformat()
    booking = {
        'id': booking_id,
        'booking_date': booking_date,
        'time_primary': time_primary,
        'time_fallback': time_fallback,
        'status': 'pending',
        'execute_at': execute_dt.isoformat(),
        'created_at': now,
        'updated_at': now
    }

    # Save to Redis
    key = f"estelle:booking:{booking_id}"
    client.set(key, json.dumps(booking))

    # Add to queue
    client.sadd("estelle:booking_queue", booking_id)

    print(f"\n✅ Booking created successfully!")
    print(f"   ID: {booking_id}")
    print(f"   Date: {booking_date}")
    print(f"   Time: {time_primary}" + (f" (fallback: {time_fallback})" if time_fallback else ""))
    print(f"   Will execute: {execute_dt.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Status: Persisted in Redis")
    print(f"\n📅 This booking will be loaded and executed when the workload scales up!")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_booking_to_redis.py <date> <time_primary> [time_fallback]")
        print("Example: python add_booking_to_redis.py 2026-03-15 10am 12pm")
        sys.exit(1)

    booking_date = sys.argv[1]
    time_primary = sys.argv[2]
    time_fallback = sys.argv[3] if len(sys.argv) > 3 else None

    add_booking(booking_date, time_primary, time_fallback)
