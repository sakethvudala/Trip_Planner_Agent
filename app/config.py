"""Application configuration and settings management."""
import os
import json
from functools import lru_cache
from typing import Optional, List

from pydantic_settings import BaseSettings
from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn, AnyHttpUrl


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "trip-planner"
    APP_ENV: str = "local"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BASE_URL: str = "http://localhost:8000"
    API_PREFIX: str = "/api"
    RELOAD: bool = True
    WORKERS: int = 1
    # NOTE: Keep this as a string to avoid pydantic attempting JSON decode before validators.
    # Expose a parsed property `ALLOWED_ORIGINS` below for application use.
    ALLOWED_ORIGINS_RAW: str = Field("*", alias="ALLOWED_ORIGINS")
    
    # Google Gemini
    GOOGLE_API_KEY: str
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
    
    # Timeouts
    REQUEST_TIMEOUT: int = 30  # seconds
    LLM_TIMEOUT: int = 60  # seconds
    TOOL_TIMEOUT: int = 10  # seconds
    
    # Agent settings
    MAX_AGENT_STEPS: int = 10
    
    # Agent metadata
    AGENT_NAME: str = "Trip Planner Agent"
    AGENT_DESCRIPTION: str = "A multi-agent system for intelligent trip planning and management."
    AGENT_VERSION: str = "1.0.0"
    AGENT_SUPPORT_EMAIL: str = "support@trip-planner.com"
    AGENT_SUPPORT_URL: str = "https://trip-planner.com/support"
    AGENT_LOGO_URL: str = "${BASE_URL}/static/logo.png"
    AGENT_LEGAL_URL: str = "https://trip-planner.com/legal"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS from the raw string value.
        Supports:
        - JSON array string: '["http://a","http://b"]'
        - Comma-separated string: 'http://a,http://b'
        - Asterisk '*': allow all
        """
        raw = (self.ALLOWED_ORIGINS_RAW or "").strip()
        if not raw:
            return ["*"]
        if raw == "*":
            return ["*"]
        # Try JSON array first
        if raw.startswith("[") and raw.endswith("]"):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [str(x) for x in data if str(x).strip()]
            except Exception:
                pass
        # Fallback to comma-separated parsing
        return [p.strip() for p in raw.split(",") if p.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get application settings with caching.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()

# Export settings for direct import
settings = get_settings()  # type: ignore
