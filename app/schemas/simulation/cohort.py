"""
Pydantic v2 schemas for Cohort.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.simulation.cohort import CohortStatus


class CohortBase(BaseModel):
    """Shared cohort fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: CohortStatus = CohortStatus.DRAFT
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CohortCreate(CohortBase):
    """Create a cohort within a tenant."""

    tenant_id: UUID

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Cohort Alpha 2026",
                "description": "First cohort of the year",
                "status": "DRAFT",
                "starts_at": "2026-06-01T00:00:00Z",
                "ends_at": "2026-08-31T23:59:59Z",
            }
        }
    )


class CohortUpdate(BaseModel):
    """Partial cohort update."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[CohortStatus] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CohortResponse(CohortBase):
    """Cohort returned to clients."""

    id: UUID
    tenant_id: UUID
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CohortList(BaseModel):
    """Paginated cohort list."""

    items: list[CohortResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
