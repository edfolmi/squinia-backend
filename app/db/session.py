"""
Database session management using async SQLAlchemy 2.0.
Implements async context managers and proper connection pooling.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages database engine and session lifecycle.
    Implements singleton pattern for engine management.
    """
    
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
    
    def init_engine(self) -> None:
        """
        Initialize the async database engine with connection pooling.
        Called once during application startup.
        """
        if self._engine is not None:
            logger.warning("Database engine already initialized")
            return
        
        # Create async engine with connection pool
        self._engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            # Use NullPool for testing environments
            poolclass=NullPool if settings.ENVIRONMENT == "testing" else None
        )
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        logger.info(
            "Database engine initialized",
            environment=settings.ENVIRONMENT,
            pool_size=settings.DB_POOL_SIZE
        )
    
    async def close_engine(self) -> None:
        """
        Close database engine and cleanup connections.
        Called during application shutdown.
        """
        if self._engine is None:
            return
        
        await self._engine.dispose()
        self._engine = None
        self._session_factory = None
        logger.info("Database engine closed")
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine instance."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized. Call init_engine() first.")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized. Call init_engine() first.")
        return self._session_factory
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency for getting database sessions.
        Automatically handles session lifecycle and cleanup.
        
        Yields:
            AsyncSession: Database session for the request
        """
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
db_manager = DatabaseManager()


# Convenience function for dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async for session in db_manager.get_session():
        yield session
