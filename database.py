"""SQLite database models and operations."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from config import settings

# Import Redis store - will be initialized after this module loads
redis_store = None


class Database:
    """SQLite database manager for booking state."""

    def __init__(self, db_path: Path = settings.database_path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_conn(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        """Create tables if they don't exist."""
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_date TEXT NOT NULL,
                    time_primary TEXT NOT NULL,
                    time_fallback TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    execute_at TEXT NOT NULL,
                    court_name TEXT,
                    booked_time TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_message TEXT,
                    screenshot_path TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_bookings_status
                ON bookings(status);

                CREATE INDEX IF NOT EXISTS idx_bookings_execute_at
                ON bookings(execute_at);

                CREATE TABLE IF NOT EXISTS execution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    details TEXT,
                    screenshot_path TEXT,
                    FOREIGN KEY (booking_id) REFERENCES bookings(id)
                );

                CREATE INDEX IF NOT EXISTS idx_log_booking_id
                ON execution_log(booking_id);

                CREATE INDEX IF NOT EXISTS idx_log_timestamp
                ON execution_log(timestamp);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date TEXT,
                    description TEXT,
                    link TEXT,
                    discovered_at TEXT NOT NULL,
                    UNIQUE(title)
                );

                CREATE INDEX IF NOT EXISTS idx_events_discovered
                ON events(discovered_at);
            """)

    def create_booking(
        self,
        booking_date: str,
        time_primary: str,
        time_fallback: Optional[str],
        execute_at: str
    ) -> int:
        """Create a new booking entry and persist to Redis."""
        global redis_store
        if redis_store is None:
            from redis_persistence import redis_store as _redis_store
            redis_store = _redis_store

        now = datetime.utcnow().isoformat()
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookings
                (booking_date, time_primary, time_fallback, status, execute_at, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, ?)
                """,
                (booking_date, time_primary, time_fallback, execute_at, now, now)
            )
            booking_id = cursor.lastrowid

            # Also save to Redis for persistence across scale-to-zero
            booking_data = {
                'id': booking_id,
                'booking_date': booking_date,
                'time_primary': time_primary,
                'time_fallback': time_fallback,
                'status': 'pending',
                'execute_at': execute_at,
                'created_at': now,
                'updated_at': now
            }
            redis_store.save_booking(booking_data)

            return booking_id

    def create_booking_from_dict(self, booking_dict: Dict) -> int:
        """Create booking from Redis dict (for loading from persistence)."""
        now = datetime.utcnow().isoformat()
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO bookings
                (id, booking_date, time_primary, time_fallback, status, execute_at,
                 court_name, booked_time, error_message, screenshot_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_dict['id'],
                    booking_dict['booking_date'],
                    booking_dict['time_primary'],
                    booking_dict.get('time_fallback'),
                    booking_dict.get('status', 'pending'),
                    booking_dict['execute_at'],
                    booking_dict.get('court_name'),
                    booking_dict.get('booked_time'),
                    booking_dict.get('error_message'),
                    booking_dict.get('screenshot_path'),
                    booking_dict.get('created_at', now),
                    booking_dict.get('updated_at', now)
                )
            )
            return cursor.lastrowid

    def update_booking_status(
        self,
        booking_id: int,
        status: str,
        court_name: Optional[str] = None,
        booked_time: Optional[str] = None,
        error_message: Optional[str] = None,
        screenshot_path: Optional[str] = None
    ):
        """Update booking status and details, syncing to Redis."""
        global redis_store
        if redis_store is None:
            from redis_persistence import redis_store as _redis_store
            redis_store = _redis_store

        now = datetime.utcnow().isoformat()
        with self.get_conn() as conn:
            conn.execute(
                """
                UPDATE bookings
                SET status = ?,
                    court_name = COALESCE(?, court_name),
                    booked_time = COALESCE(?, booked_time),
                    error_message = ?,
                    screenshot_path = COALESCE(?, screenshot_path),
                    updated_at = ?
                WHERE id = ?
                """,
                (status, court_name, booked_time, error_message, screenshot_path, now, booking_id)
            )

        # Also update in Redis for persistence
        update_fields = {}
        if court_name:
            update_fields['court_name'] = court_name
        if booked_time:
            update_fields['booked_time'] = booked_time
        if error_message is not None:
            update_fields['error_message'] = error_message
        if screenshot_path:
            update_fields['screenshot_path'] = screenshot_path

        redis_store.update_booking_status(booking_id, status, **update_fields)

    def get_pending_bookings(self, execute_before: str) -> List[Dict[str, Any]]:
        """Get all pending bookings that should be executed before given time."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM bookings
                WHERE status = 'pending' AND execute_at <= ?
                ORDER BY execute_at ASC
                """,
                (execute_before,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_bookings(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all bookings, optionally filtered by status."""
        with self.get_conn() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM bookings WHERE status = ? ORDER BY execute_at DESC",
                    (status,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM bookings ORDER BY execute_at DESC"
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_booking(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """Get a single booking by ID."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def log_execution(
        self,
        booking_id: int,
        action: str,
        result: str,
        details: Optional[str] = None,
        screenshot_path: Optional[str] = None
    ):
        """Log an execution step."""
        now = datetime.utcnow().isoformat()
        with self.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO execution_log
                (booking_id, timestamp, action, result, details, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (booking_id, now, action, result, details, screenshot_path)
            )

    def get_booking_logs(self, booking_id: int) -> List[Dict[str, Any]]:
        """Get execution logs for a booking."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM execution_log
                WHERE booking_id = ?
                ORDER BY timestamp ASC
                """,
                (booking_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_booking(self, booking_id: int):
        """Delete a booking and its logs."""
        with self.get_conn() as conn:
            conn.execute("DELETE FROM execution_log WHERE booking_id = ?", (booking_id,))
            conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))

    def get_stats(self) -> Dict[str, Any]:
        """Get booking statistics."""
        with self.get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE status = 'pending'"
            ).fetchone()[0]
            booked = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE status = 'booked'"
            ).fetchone()[0]
            failed = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE status = 'failed'"
            ).fetchone()[0]

            return {
                "total": total,
                "pending": pending,
                "booked": booked,
                "failed": failed
            }

    def store_event(self, event: Dict[str, Any]):
        """Store a new event."""
        with self.get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO events (title, date, description, link, discovered_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event['title'], event.get('date'), event.get('description'),
                 event.get('link'), event['discovered_at'])
            )

    def get_seen_events(self) -> List[Dict[str, Any]]:
        """Get all previously seen events."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM events ORDER BY discovered_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently discovered events."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM events ORDER BY discovered_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]


# Global database instance
db = Database()
