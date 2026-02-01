"""FastAPI REST API for Padel booking system."""
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import db
from scheduler import scheduler
from notifications import notifier
from booking_engine import engine
from events_monitor import events_monitor
from config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Padel Court Booking API",
    description="Automated Padel court booking system for Estelle Manor",
    version="1.0.0"
)


class BookingResponse(BaseModel):
    """Response model for booking operations."""
    success: bool
    message: str
    data: Optional[dict] = None


class StatsResponse(BaseModel):
    """Response model for statistics."""
    total: int
    pending: int
    booked: int
    failed: int


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Padel Court Booking API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "upload_csv": "POST /bookings/upload",
            "list_bookings": "GET /bookings",
            "get_booking": "GET /bookings/{id}",
            "delete_booking": "DELETE /bookings/{id}",
            "stats": "GET /stats",
            "health": "GET /health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database connectivity
        stats = db.get_stats()

        # Check scheduler
        scheduler_running = scheduler.scheduler.running

        return {
            "status": "healthy",
            "database": "connected",
            "scheduler": "running" if scheduler_running else "stopped",
            "bookings": stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/bookings/upload", response_model=BookingResponse)
async def upload_bookings_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file with booking requests.

    Expected CSV format:
    ```
    Date, Time1, Time2, Status
    2026-01-31, 7pm, 8pm, Book
    2026-02-15, 11am, 12pm, Book
    ```

    - **Date**: Booking date in YYYY-MM-DD format
    - **Time1**: Primary desired time (e.g., "7pm", "11am")
    - **Time2**: Fallback time (optional)
    - **Status**: Must be "Book" to process
    """
    try:
        # Read CSV content
        content = await file.read()
        csv_text = content.decode("utf-8")

        # Process bookings
        result = await scheduler.add_bookings_from_csv(csv_text)

        if result["errors"]:
            return BookingResponse(
                success=True,
                message=f"Processed with {len(result['errors'])} errors",
                data=result
            )
        else:
            return BookingResponse(
                success=True,
                message=f"Successfully added {result['added']} bookings",
                data=result
            )

    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/bookings")
async def list_bookings(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    List all bookings, optionally filtered by status.

    Valid status values: pending, scheduled, booked, failed, cancelled
    """
    try:
        bookings = db.get_all_bookings(status)

        # Limit results
        bookings = bookings[:limit]

        return {
            "count": len(bookings),
            "bookings": bookings
        }

    except Exception as e:
        logger.error(f"Error listing bookings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: int):
    """Get detailed information about a specific booking including execution logs."""
    try:
        booking = db.get_booking(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        # Get execution logs
        logs = db.get_booking_logs(booking_id)

        return {
            "booking": booking,
            "logs": logs
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting booking {booking_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/bookings/{booking_id}", response_model=BookingResponse)
async def delete_booking(booking_id: int):
    """
    Delete a booking completely.
    This will cancel the scheduled execution and remove from database.
    """
    try:
        success = scheduler.delete_booking(booking_id)

        if success:
            return BookingResponse(
                success=True,
                message=f"Booking {booking_id} deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Booking not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting booking {booking_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(booking_id: int):
    """
    Cancel a booking without deleting it.
    This will remove it from the scheduler but keep the record.
    """
    try:
        success = scheduler.cancel_booking(booking_id)

        if success:
            return BookingResponse(
                success=True,
                message=f"Booking {booking_id} cancelled successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Booking not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings/upcoming/list")
async def get_upcoming_bookings(limit: int = Query(10, ge=1, le=100)):
    """Get upcoming scheduled bookings."""
    try:
        bookings = scheduler.get_upcoming_bookings(limit)
        return {
            "count": len(bookings),
            "bookings": bookings
        }

    except Exception as e:
        logger.error(f"Error getting upcoming bookings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get booking statistics."""
    try:
        stats = db.get_stats()
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/notification")
async def test_notification():
    """Send a test Discord notification."""
    try:
        await notifier.send_message(
            content="🧪 Test notification from Padel Booking Bot",
            embeds=[{
                "title": "Test Notification",
                "description": "If you see this, Discord notifications are working!",
                "color": 3447003
            }]
        )
        return {"success": True, "message": "Test notification sent"}

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/recent")
async def get_recent_events(limit: int = Query(20, ge=1, le=100)):
    """Get recently discovered events."""
    try:
        events = db.get_recent_events(limit)
        return {
            "count": len(events),
            "events": events,
            "monitoring_enabled": settings.events_monitoring_enabled
        }
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/events/check-now")
async def check_events_now():
    """Manually trigger events check."""
    try:
        await events_monitor.check_for_new_events()
        return {"success": True, "message": "Events check completed"}
    except Exception as e:
        logger.error(f"Error checking events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("FastAPI application starting up")

    # Reschedule any pending bookings
    scheduler.reschedule_pending_bookings()

    logger.info("Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("FastAPI application shutting down")

    # Shutdown scheduler
    scheduler.shutdown()

    # Cleanup browser
    await engine.cleanup()

    logger.info("Application shutdown complete")
