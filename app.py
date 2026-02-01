"""Main application entry point."""
import asyncio
import logging
import sys
from pathlib import Path
import uvicorn
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("./logs/booking.log")
    ]
)

logger = logging.getLogger(__name__)


def setup_directories():
    """Create required directories."""
    Path("./data").mkdir(exist_ok=True)
    Path("./data/screenshots").mkdir(exist_ok=True)
    Path("./logs").mkdir(exist_ok=True)
    logger.info("Directories created")


def main():
    """Run the FastAPI application."""
    logger.info("Starting Padel Booking System")
    logger.info(f"DRY RUN MODE: {settings.dry_run}")

    # Setup directories
    setup_directories()

    # Run uvicorn server
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=False
    )


if __name__ == "__main__":
    main()
