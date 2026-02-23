"""Configuration management for Cyperf CVE Tracker API."""

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with validation.

    All values are loaded from environment variables. Cyperf credentials
    are required at startup; the app will refuse to start if they are missing.
    """

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./cyperf_cve.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # NVD API
    nvd_api_key: str | None = None

    # Cyperf credentials (REQUIRED)
    cyperf_controller_ip: str
    cyperf_username: str
    cyperf_password: str

    # Sync configuration
    cyperf_sync_interval_hours: int = 24

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **data: dict) -> None:
        """Initialize settings and validate Cyperf credentials.

        Raises:
            ValueError: If any required Cyperf credential is missing.
        """
        super().__init__(**data)

        # Validate Cyperf credentials at initialization time
        if not self.cyperf_controller_ip:
            raise ValueError("CYPERF_CONTROLLER_IP environment variable is required but not set")
        if not self.cyperf_username:
            raise ValueError("CYPERF_USERNAME environment variable is required but not set")
        if not self.cyperf_password:
            raise ValueError("CYPERF_PASSWORD environment variable is required but not set")

        # Log successful configuration
        logger.info(f"✓ Configuration loaded ({self.environment} mode)")
        logger.info(f"✓ Database URL: {self.database_url}")
        logger.info(f"✓ Redis URL: {self.redis_url}")
        logger.info(f"✓ Cyperf Controller: {self.cyperf_controller_ip}")
        logger.info("✓ All required credentials configured")


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached singleton).

    Returns:
        Settings: Validated application settings instance.
    """
    return Settings()
