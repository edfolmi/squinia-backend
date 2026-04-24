"""Simulation session lifecycle."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.auth.membership import OrgRole
from app.models.simulation.evaluation import EvalStatus
from app.models.simulation.scenario import ScenarioStatus
from app.models.simulation.simulation_session import SessionMode, SessionStatus, SimulationSession
from app.repositories.simulation import CohortRepository, EvaluationRepository, MessageRepository, ScenarioRepository, SessionRepository
from app.services.ai.text_simulation_chat import complete_text_chat_turn, complete_text_opening_turn
from app.schemas.simulation.requests import SimulationSessionStartRequest

logger = get_logger(__name__)


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.scenarios = ScenarioRepository(db)
        self.cohorts = CohortRepository(db)
        self.evaluations = EvaluationRepository(db)
        self.messages = MessageRepository(db)

    def _snapshot_from_scenario(self, scenario) -> dict:
        rubric = [
            {
                "id": str(i.id),
                "criterion": i.criterion,
                "description": i.description,
                "max_score": i.max_score,
                "weight": i.weight,
                "sort_order": i.sort_order,
            }
            for i in sorted(scenario.rubric_items, key=lambda x: (x.sort_order, str(x.id)))
        ]
        return {
            "scenario_id": str(scenario.id),
            "title": scenario.title,
            "description": scenario.description,
            "agent_role": scenario.agent_role.value,
            "difficulty": scenario.difficulty.value,
            "config": scenario.config or {},
            "rubric": rubric,
        }

    async def start_session(
        self,
        tenant_id: UUID,
        user_id: UUID,
        org_role: OrgRole,
        body: SimulationSessionStartRequest,
    ) -> dict:
        scenario = await self.scenarios.get_with_rubric(body.scenario_id, tenant_id)
        if not scenario:
            raise AppError(status_code=404, code="NOT_FOUND", message="Scenario not found")
        if scenario.status != ScenarioStatus.PUBLISHED:
            raise AppError(
                status_code=400,
                code="SCENARIO_NOT_PUBLISHED",
                message="Scenario must be published before starting a session",
            )
        if org_role == OrgRole.STUDENT and body.cohort_id:
            m = await self.cohorts.get_member(body.cohort_id, user_id)
            if not m:
                raise AppError(status_code=403, code="FORBIDDEN", message="Not a member of this cohort")

        snapshot = self._snapshot_from_scenario(scenario)
        now = datetime.now(timezone.utc)
        session = await self.sessions.create(
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "scenario_id": scenario.id,
                "cohort_id": body.cohort_id,
                "status": SessionStatus.IN_PROGRESS,
                "mode": body.mode,
                "turn_count": 0,
                "duration_seconds": 0,
                "scenario_snapshot": snapshot,
                "started_at": now,
            },
        )
        await self.db.commit()
        logger.info("Session started", session_id=str(session.id), user_id=str(user_id))
        return {
            "session_id": session.id,
            "scenario_snapshot": snapshot,
        }

    async def list_sessions(
        self,
        tenant_id: UUID,
        user_id: UUID,
        org_role: OrgRole,
        page: int,
        limit: int,
        *,
        status: SessionStatus | None = None,
        cohort_id: UUID | None = None,
    ) -> dict:
        offset = (page - 1) * limit
        if org_role == OrgRole.STUDENT:
            items = await self.sessions.list_for_user(
                tenant_id,
                user_id,
                offset=offset,
                limit=limit,
                status=status,
                cohort_id=cohort_id,
            )
            total = await self.sessions.count_for_user(
                tenant_id,
                user_id,
                status=status,
                cohort_id=cohort_id,
            )
        else:
            items = await self.sessions.list_for_tenant(
                tenant_id,
                offset=offset,
                limit=limit,
                status=status,
                cohort_id=cohort_id,
            )
            total = await self.sessions.count_for_tenant(tenant_id, status=status, cohort_id=cohort_id)
        return {"items": items, "total": total, "page": page, "limit": limit}

    def _assert_session_access(
        self,
        session: SimulationSession,
        user_id: UUID,
        org_role: OrgRole,
    ) -> None:
        if session.user_id != user_id and org_role == OrgRole.STUDENT:
            raise AppError(status_code=403, code="FORBIDDEN", message="Cannot access another user's session")
        if session.user_id != user_id and org_role not in (
            OrgRole.INSTRUCTOR,
            OrgRole.ORG_ADMIN,
            OrgRole.ORG_OWNER,
        ):
            raise AppError(status_code=403, code="FORBIDDEN", message="Insufficient privileges to view this session")

    async def get_detail(self, tenant_id: UUID, session_id: UUID, user_id: UUID, org_role: OrgRole) -> dict:
        row = await self.sessions.get_with_relations(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        eval_payload = None
        if row.evaluation and row.evaluation.status == EvalStatus.COMPLETED:
            eval_payload = row.evaluation
        return {"session": row, "messages": list(row.messages), "evaluation": eval_payload}

    async def end_session(self, tenant_id: UUID, session_id: UUID, user_id: UUID, org_role: OrgRole) -> dict:
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        if row.status in (SessionStatus.COMPLETED, SessionStatus.ABANDONED):
            raise AppError(status_code=400, code="SESSION_ENDED", message="Session already ended or abandoned")
        now = datetime.now(timezone.utc)
        await self.sessions.update(
            session_id,
            tenant_id,
            {
                "status": SessionStatus.COMPLETED,
                "ended_at": now,
            },
        )
        existing = await self.evaluations.get_by_session(session_id, tenant_id)
        if not existing:
            await self.evaluations.create(
                {
                    "session_id": session_id,
                    "tenant_id": tenant_id,
                    "status": EvalStatus.PENDING,
                },
            )
        await self.db.commit()
        logger.info("Session completed", session_id=str(session_id))
        return {"session": await self.sessions.get(session_id, tenant_id)}

    async def abandon_session(self, tenant_id: UUID, session_id: UUID, user_id: UUID, org_role: OrgRole) -> dict:
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        if row.status in (SessionStatus.COMPLETED, SessionStatus.ABANDONED):
            raise AppError(status_code=400, code="SESSION_ENDED", message="Session already ended or abandoned")
        now = datetime.now(timezone.utc)
        await self.sessions.update(
            session_id,
            tenant_id,
            {"status": SessionStatus.ABANDONED, "ended_at": now},
        )
        await self.db.commit()
        return {"session": await self.sessions.get(session_id, tenant_id)}

    async def list_messages(self, tenant_id: UUID, session_id: UUID, user_id: UUID, org_role: OrgRole) -> dict:
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        items = await self.messages.list_for_session(session_id)
        return {"items": items, "total": len(items)}

    async def issue_livekit_token(
        self,
        tenant_id: UUID,
        session_id: UUID,
        user_id: UUID,
        org_role: OrgRole,
    ) -> dict:
        """Return LiveKit server URL, room name, and participant JWT for VOICE/VIDEO sessions."""
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        if row.mode not in (SessionMode.VOICE, SessionMode.VIDEO):
            raise AppError(
                status_code=400,
                code="SESSION_MODE_NOT_LIVEKIT",
                message="LiveKit tokens are only issued for VOICE or VIDEO sessions.",
            )
        from app.services.ai.livekit_access import issue_livekit_participant_token

        server_url, room_name, participant_token = issue_livekit_participant_token(
            session_id=session_id,
            user_id=user_id,
            display_name="Learner",
        )
        return {
            "server_url": server_url,
            "room_name": room_name,
            "participant_token": participant_token,
        }

    async def evaluation_status(
        self,
        tenant_id: UUID,
        session_id: UUID,
        user_id: UUID,
        org_role: OrgRole,
    ) -> tuple[int, dict]:
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        ev = await self.evaluations.get_by_session_detail(session_id, tenant_id)
        if not ev:
            raise AppError(
                status_code=404,
                code="EVALUATION_NOT_FOUND",
                message="No evaluation exists for this session",
            )
        if ev.status in (EvalStatus.PENDING, EvalStatus.PROCESSING):
            return 202, {"evaluation": None, "status": ev.status.value}
        if ev.status == EvalStatus.FAILED:
            return 200, {"evaluation": ev, "status": ev.status.value}
        return 200, {"evaluation": ev, "status": ev.status.value}

    async def send_text_chat(
        self,
        tenant_id: UUID,
        session_id: UUID,
        user_id: UUID,
        org_role: OrgRole,
        text: str,
    ) -> dict:
        stripped = (text or "").strip()
        if not stripped:
            raise AppError(status_code=422, code="EMPTY_MESSAGE", message="Message text is required.")
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        if row.user_id != user_id:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Only the session owner can send chat messages.",
            )
        if row.status != SessionStatus.IN_PROGRESS:
            raise AppError(status_code=400, code="SESSION_ENDED", message="Session is not active.")
        if row.mode != SessionMode.TEXT:
            raise AppError(
                status_code=400,
                code="WRONG_MODE",
                message="Chat is only for TEXT sessions; use LiveKit for voice/video.",
            )
        return await complete_text_chat_turn(
            self.db,
            tenant_id=tenant_id,
            session_id=session_id,
            user_id=user_id,
            user_text=stripped,
        )

    async def post_text_opening(
        self,
        tenant_id: UUID,
        session_id: UUID,
        user_id: UUID,
        org_role: OrgRole,
    ) -> dict:
        row = await self.sessions.get(session_id, tenant_id)
        if not row:
            raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")
        self._assert_session_access(row, user_id, org_role)
        if row.user_id != user_id:
            raise AppError(
                status_code=403,
                code="FORBIDDEN",
                message="Only the session owner can start the conversation.",
            )
        if row.status != SessionStatus.IN_PROGRESS:
            raise AppError(status_code=400, code="SESSION_ENDED", message="Session is not active.")
        if row.mode != SessionMode.TEXT:
            raise AppError(status_code=400, code="WRONG_MODE", message="Opening is only for TEXT sessions.")
        return await complete_text_opening_turn(
            self.db,
            tenant_id=tenant_id,
            session_id=session_id,
            user_id=user_id,
        )
