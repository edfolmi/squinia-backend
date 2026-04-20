"""Assignment and submission use-cases."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.auth.membership import OrgRole
from app.models.simulation.assignment import AssignmentStatus, AssignmentType
from app.repositories.simulation import AssignmentRepository
from app.schemas.simulation.assignment import AssignmentUpdate
from app.schemas.simulation.requests import AssignmentCreateRequest, AssignmentGradeRequest, AssignmentSubmitRequest

logger = get_logger(__name__)


class AssignmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.assignments = AssignmentRepository(db)

    async def create(
        self,
        tenant_id: UUID,
        assigner_id: UUID,
        body: AssignmentCreateRequest,
    ) -> dict:
        row = await self.assignments.create(
            {
                "tenant_id": tenant_id,
                "session_id": body.session_id,
                "assigned_to": body.assigned_to,
                "assigned_by": assigner_id,
                "type": body.type,
                "status": AssignmentStatus.PENDING,
                "title": body.title,
                "instructions": body.instructions,
                "content": body.content,
                "due_at": body.due_at,
            },
        )
        await self.db.commit()
        return {"assignment": row}

    async def list(
        self,
        tenant_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
        page: int,
        limit: int,
        *,
        assigned_to: UUID | None = None,
        assigned_to_me: bool = False,
        status: AssignmentStatus | None = None,
    ) -> dict:
        offset = (page - 1) * limit
        target_user = assigned_to
        if assigned_to_me:
            target_user = viewer_id
        if org_role == OrgRole.STUDENT:
            target_user = viewer_id
        items = await self.assignments.list_for_tenant(
            tenant_id,
            offset=offset,
            limit=limit,
            assigned_to=target_user,
            status=status,
        )
        total = await self.assignments.count_for_tenant(tenant_id, assigned_to=target_user, status=status)
        return {"items": items, "total": total, "page": page, "limit": limit}

    async def get_detail(self, tenant_id: UUID, assignment_id: UUID, viewer_id: UUID, org_role: OrgRole) -> dict:
        row = await self.assignments.get(assignment_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Assignment not found")
        if org_role == OrgRole.STUDENT and row.assigned_to != viewer_id:
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot view this assignment")
        sub = await self.assignments.get_submission(assignment_id, row.assigned_to)
        return {"assignment": row, "submission": sub}

    async def update(
        self,
        tenant_id: UUID,
        assignment_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
        body: AssignmentUpdate,
    ) -> dict:
        if org_role == OrgRole.STUDENT:
            raise AppError(status_code=403, code="FORBIDDEN", message="Students cannot update assignments")
        row = await self.assignments.get(assignment_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Assignment not found")
        data = body.model_dump(exclude_unset=True)
        updated = await self.assignments.update(assignment_id, tenant_id, data)
        await self.db.commit()
        return {"assignment": updated}

    async def soft_delete(self, tenant_id: UUID, assignment_id: UUID, org_role: OrgRole) -> None:
        if org_role == OrgRole.STUDENT:
            raise AppError(status_code=403, code="FORBIDDEN", message="Students cannot delete assignments")
        row = await self.assignments.get(assignment_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Assignment not found")
        await self.assignments.soft_delete(assignment_id, tenant_id)
        await self.db.commit()

    async def submit(
        self,
        tenant_id: UUID,
        assignment_id: UUID,
        student_id: UUID,
        body: AssignmentSubmitRequest,
    ) -> dict:
        row = await self.assignments.get(assignment_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Assignment not found")
        if row.assigned_to != student_id:
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot submit for another user")
        if row.status in (AssignmentStatus.SUBMITTED, AssignmentStatus.GRADED):
            raise AppError(status_code=409, code="ALREADY_SUBMITTED", message="Assignment already submitted")
        if row.due_at and row.due_at < datetime.now(timezone.utc):
            raise AppError(status_code=400, code="ASSIGNMENT_OVERDUE", message="Assignment is past due date")

        sub = await self.assignments.upsert_submission(
            assignment_id,
            student_id,
            {
                "content": body.content,
                "files": body.files,
            },
        )
        new_status = AssignmentStatus.SUBMITTED
        await self.assignments.update(assignment_id, tenant_id, {"status": new_status})
        await self.db.commit()
        logger.info("Assignment submitted", assignment_id=str(assignment_id), user_id=str(student_id))
        return {"submission": sub, "assignment": await self.assignments.get(assignment_id, tenant_id)}

    async def get_submission(
        self,
        tenant_id: UUID,
        assignment_id: UUID,
        viewer_id: UUID,
        org_role: OrgRole,
    ) -> dict:
        row = await self.assignments.get(assignment_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Assignment not found")
        if org_role == OrgRole.STUDENT and row.assigned_to != viewer_id:
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot view this submission")
        sub = await self.assignments.get_submission(assignment_id, row.assigned_to)
        return {"submission": sub, "assignment": row}

    async def grade(
        self,
        tenant_id: UUID,
        assignment_id: UUID,
        org_role: OrgRole,
        body: AssignmentGradeRequest,
    ) -> dict:
        if org_role not in (OrgRole.INSTRUCTOR, OrgRole.ORG_ADMIN, OrgRole.ORG_OWNER):
            raise AppError(status_code=403, code="FORBIDDEN", message="Only instructors or admins can grade")
        row = await self.assignments.get(assignment_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Assignment not found")
        sub = await self.assignments.get_submission(assignment_id, row.assigned_to)
        if not sub:
            raise AppError(status_code=400, code="NO_SUBMISSION", message="No submission to grade")
        await self.assignments.upsert_submission(
            assignment_id,
            row.assigned_to,
            {
                "score": body.score,
                "feedback": body.feedback,
                "graded_at": datetime.now(timezone.utc),
            },
        )
        await self.assignments.update(assignment_id, tenant_id, {"status": AssignmentStatus.GRADED})
        await self.db.commit()
        fresh_sub = await self.assignments.get_submission(assignment_id, row.assigned_to)
        return {"submission": fresh_sub, "assignment": await self.assignments.get(assignment_id, tenant_id)}
