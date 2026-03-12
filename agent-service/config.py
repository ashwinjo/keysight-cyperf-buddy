"""Agent service configuration — validated at startup."""

import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class AgentSettings(BaseSettings):
    gemini_api_key: str
    backend_api_url: str = "http://api:8000"
    backend_timeout_seconds: int = 10
    log_level: str = "INFO"
    environment: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}


_settings: AgentSettings | None = None


def get_settings() -> AgentSettings:
    global _settings
    if _settings is None:
        _settings = AgentSettings()  # Raises if GEMINI_API_KEY missing
        logger.info(
            "Agent config loaded: backend_api_url=%s", _settings.backend_api_url
        )
    return _settings
