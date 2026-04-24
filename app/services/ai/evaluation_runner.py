"""Background evaluation using OpenAI (JSON rubric scores) — GPT-4o-mini."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import db_manager
from app.models.simulation.evaluation import EvalStatus
from app.repositories.simulation import EvaluationRepository, MessageRepository, SessionRepository
from app.schemas.simulation.requests import EvalScoreCompleteItem, InternalEvalCompleteRequest
from app.services.simulation.evaluation import EvaluationService

logger = get_logger(__name__)


class _LLMScoreItem(BaseModel):
    rubric_item_id: str
    score: int = Field(..., ge=0)
    rationale: str | None = None


class _LLMEvalPayload(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    feedback_summary: str
    strengths: str | None = None
    improvements: str | None = None
    scores: list[_LLMScoreItem] = Field(default_factory=list)


def _transcript_from_messages(messages: list[Any]) -> str:
    lines: list[str] = []
    for m in messages:
        role = getattr(m.role, "value", m.role)
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines) if lines else "(no transcript)"


def _rubric_block(snapshot: dict[str, Any] | None) -> str:
    snap = snapshot or {}
    rubric = snap.get("rubric") if isinstance(snap.get("rubric"), list) else []
    parts: list[str] = []
    for item in rubric:
        if not isinstance(item, dict):
            continue
        rid = item.get("id", "")
        crit = item.get("criterion", "criterion")
        mx = item.get("max_score", 5)
        desc = (item.get("description") or "").strip()
        parts.append(f"- id={rid} | {crit} | max_score={mx} | {desc}")
    return "\n".join(parts) if parts else "(no rubric — give overall_score and qualitative feedback only; scores may be empty)"


async def run_openai_evaluation_job(session_id: UUID) -> None:
    """Called after session end; fills evaluation scores or marks FAILED."""
    async with db_manager.session_factory() as db:
        sessions = SessionRepository(db)
        evaluations = EvaluationRepository(db)

        row = await sessions.get_by_id(session_id)
        if not row:
            logger.warning("evaluation_runner: session missing", session_id=str(session_id))
            return

        tenant_id = row.tenant_id
        ev = await evaluations.get_by_session(session_id, tenant_id)
        if not ev:
            logger.warning("evaluation_runner: no evaluation row", session_id=str(session_id))
            return
        if ev.status not in (EvalStatus.PENDING, EvalStatus.PROCESSING):
            return

        if not settings.OPENAI_API_KEY:
            await evaluations.update(
                ev.id,
                tenant_id,
                {
                    "status": EvalStatus.FAILED,
                    "feedback_summary": "OPENAI_API_KEY is not configured; evaluation was not run.",
                    "completed_at": datetime.now(timezone.utc),
                },
            )
            await db.commit()
            return

        await evaluations.update(
            ev.id,
            tenant_id,
            {
                "status": EvalStatus.PROCESSING,
                "processing_started_at": datetime.now(timezone.utc),
            },
        )
        await db.commit()

    try:
        from openai import AsyncOpenAI
    except ImportError as e:  # pragma: no cover
        async with db_manager.session_factory() as db:
            sessions = SessionRepository(db)
            evaluations = EvaluationRepository(db)
            row = await sessions.get_by_id(session_id)
            if not row:
                return
            ev2 = await evaluations.get_by_session(session_id, row.tenant_id)
            if ev2:
                await evaluations.update(
                    ev2.id,
                    row.tenant_id,
                    {
                        "status": EvalStatus.FAILED,
                        "feedback_summary": f"OpenAI SDK missing: {e}",
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await db.commit()
        return

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )
    model = settings.OPENAI_CHAT_MODEL or "gpt-4o-mini"

    async with db_manager.session_factory() as db:
        sessions = SessionRepository(db)
        messages = MessageRepository(db)
        row = await sessions.get_by_id(session_id)
        if not row:
            return
        tenant_id = row.tenant_id
        snap = row.scenario_snapshot if isinstance(row.scenario_snapshot, dict) else {}
        msgs = await messages.list_for_session(session_id)
        transcript = _transcript_from_messages(msgs)
        rubric_txt = _rubric_block(snap)

    system = (
        "You are an expert evaluator for workplace simulations. "
        "Read the transcript and rubric. Respond with JSON only (no markdown) matching this shape:\n"
        '{"overall_score":0-100,"feedback_summary":"string","strengths":"string|null",'
        '"improvements":"string|null","scores":[{"rubric_item_id":"uuid","score":int,"rationale":"string|null"}]}\n'
        "Each rubric_item_id must match an id from the rubric list. Scores must be integers between 0 and max_score for that row."
    )
    user = f"### Transcript\n{transcript}\n\n### Rubric\n{rubric_txt}"

    try:
        resp = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        raw = (resp.choices[0].message.content or "").strip()
        payload = _LLMEvalPayload.model_validate(json.loads(raw))
    except Exception as e:
        logger.exception("evaluation_runner: OpenAI failed", session_id=str(session_id))
        async with db_manager.session_factory() as db:
            evaluations = EvaluationRepository(db)
            ev2 = await evaluations.get_by_session(session_id, tenant_id)
            if ev2:
                await evaluations.update(
                    ev2.id,
                    tenant_id,
                    {
                        "status": EvalStatus.FAILED,
                        "feedback_summary": f"Evaluation failed: {e!s}"[:2000],
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await db.commit()
        return

    rubric_items = snap.get("rubric") if isinstance(snap.get("rubric"), list) else []
    max_by_id: dict[str, int] = {}
    for item in rubric_items:
        if isinstance(item, dict) and item.get("id"):
            try:
                max_by_id[str(item["id"])] = int(item.get("max_score") or 5)
            except (TypeError, ValueError):
                max_by_id[str(item["id"])] = 5

    scores_out: list[EvalScoreCompleteItem] = []
    for s in payload.scores:
        try:
            rid = UUID(str(s.rubric_item_id))
        except ValueError:
            continue
        cap = max_by_id.get(str(rid), 100)
        sc = min(max(0, int(s.score)), cap)
        scores_out.append(EvalScoreCompleteItem(rubric_item_id=rid, score=sc, rationale=s.rationale))

    body = InternalEvalCompleteRequest(
        overall_score=min(100, max(0, payload.overall_score)),
        feedback_summary=payload.feedback_summary[:8000],
        strengths=(payload.strengths or None),
        improvements=(payload.improvements or None),
        highlights=[],
        scores=scores_out,
    )

    try:
        async with db_manager.session_factory() as db:
            svc = EvaluationService(db)
            ev3 = await svc.evaluations.get_by_session(session_id, tenant_id)
            if not ev3:
                return
            await svc.internal_complete(ev3.id, body)
    except Exception as e:
        logger.exception("evaluation_runner: persist failed", session_id=str(session_id))
        async with db_manager.session_factory() as db:
            evaluations = EvaluationRepository(db)
            sessions = SessionRepository(db)
            row = await sessions.get_by_id(session_id)
            if not row:
                return
            ev4 = await evaluations.get_by_session(session_id, row.tenant_id)
            if ev4:
                await evaluations.update(
                    ev4.id,
                    row.tenant_id,
                    {
                        "status": EvalStatus.FAILED,
                        "feedback_summary": f"Could not persist evaluation: {e!s}"[:2000],
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await db.commit()
