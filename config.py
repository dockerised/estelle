"""Configuration management using pydantic-settings."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Estelle Manor Credentials
    estelle_username: str
    estelle_password: str

    # Discord Webhook
    discord_webhook_url: str

    # Application Settings
    dry_run: bool = False
    log_level: str = "INFO"
    database_path: Path = Path("./data/estelle.db")
    browser_state_path: Path = Path("./data/browser_state.json")

    # Timing Configuration
    pre_login_minutes: int = 10

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # URLs
    login_url: str = "https://home.estellemanor.com/page/login"
    booking_url: str = "https://home.estellemanor.com/spa/16499"

    # Events Monitoring
    events_monitoring_enabled: bool = False
    events_check_interval_hours: int = 6  # Check every 6 hours

    # Redis Configuration (for persistent bookings across scale-to-zero)
    redis_url: str = "redis://redis-shared.dev.cpln.local:6379"


settings = Settings()
