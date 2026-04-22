"""
Core application configuration using Pydantic v2 Settings.
Handles environment-based configuration for dev/staging/prod.
"""
from typing import List, Literal
from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    Uses Pydantic v2 Settings for type validation and .env file support.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "FastAPI Backend"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: PostgresDsn
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: RedisDsn
    REDIS_CACHE_TTL: int = 300
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Internal worker / service-to-service calls (set in production)
    INTERNAL_API_KEY: str = "dev-internal-key-change-me"

    # Short-lived WebSocket session token (minutes)
    WS_SESSION_TOKEN_EXPIRE_MINUTES: int = 5
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Public URL for links in transactional email (Next.js app)
    PUBLIC_APP_URL: str = "http://localhost:3000"

    # Transactional email: ses | console | none
    EMAIL_PROVIDER: Literal["ses", "console", "none"] = "console"
    AWS_REGION: str = "us-east-1"
    SES_FROM_EMAIL: str = "noreply@example.com"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if isinstance(v, str) and "postgresql://" in v:
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    @property
    def database_url_sync(self) -> str:
        """
        Synchronous PostgreSQL URL (e.g. for psycopg2 / one-off scripts).

        Alembic in this project runs online migrations with SQLAlchemy asyncio;
        use ``DATABASE_URL`` (asyncpg) there, not this property.
        """
        return str(self.DATABASE_URL).replace("+asyncpg", "")


# Global settings instance
settings = Settings()
