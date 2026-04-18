"""
Base SQLAlchemy model with common fields and utilities.
Uses SQLAlchemy 2.0 declarative style with proper typing.
"""
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base model for all database models.
    Provides common fields and utility methods.
    """
    
    # Type annotation for the table name
    __abstract__ = True
    
    # Automatically generate __tablename__ from class name
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()


class TimestampMixin:
    """
    Mixin for adding timestamp fields to models.
    Automatically manages created_at and updated_at fields.
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class BaseModel(Base, TimestampMixin):
    """
    Base model with timestamps for most domain models.
    Inherit from this for models that need audit fields.
    """
    
    __abstract__ = True
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.
        Useful for serialization and debugging.
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """String representation of the model."""
        attrs = ", ".join(
            f"{k}={v!r}"
            for k, v in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({attrs})"
