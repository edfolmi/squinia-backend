"""Agentic scenario evaluation using the OpenAI Agents SDK over OpenRouter."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import db_manager
from app.models.simulation.evaluation import EvalStatus
from app.models.simulation.message import MessageRole
from app.repositories.simulation import EvaluationRepository, MessageRepository, SessionRepository
from app.services.ai.observability import (
    log_model_call,
    model_call_started_at,
    openai_trace_config,
    openai_tracing_enabled,
)
from app.schemas.simulation.requests import EvalScoreCompleteItem, InternalEvalCompleteRequest
from app.services.simulation.evaluation import EvaluationService

logger = get_logger(__name__)


class _TranscriptTurn(BaseModel):
    id: str
    role: str
    text: str
    offset_ms: int | None = None
    source_message_ids: list[str] = Field(default_factory=list)


class _RubricItem(BaseModel):
    id: str
    criterion: str
    description: str = ""
    max_score: int = 5


class _ScoreDraftItem(BaseModel):
    rubric_item_id: str
    score: int = Field(..., ge=0)
    summary: str


class _ScoreDraftPayload(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    feedback_summary: str
    strengths: str | None = None
    improvements: str | None = None
    scores: list[_ScoreDraftItem] = Field(default_factory=list)


class _EvidenceItem(BaseModel):
    rubric_item_id: str
    quote_turn_id: str | None = None
    example_quote: str
    improvement: str


class _EvidencePayload(BaseModel):
    items: list[_EvidenceItem] = Field(default_factory=list)


class _FinalScoreItem(BaseModel):
    rubric_item_id: str
    score: int = Field(..., ge=0)
    rationale: str
    summary: str
    quote_turn_id: str | None = None
    example_quote: str
    improvement: str


class _FinalEvalPayload(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    feedback_summary: str
    strengths: str | None = None
    improvements: str | None = None
    reviewer_notes: str | None = None
    scores: list[_FinalScoreItem] = Field(default_factory=list)


_SPACE_RE = re.compile(r"\s+")


def _clean_text(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())


def _normalized(value: str) -> str:
    return _SPACE_RE.sub(" ", value.strip()).lower()


def _join_turn_text(left: str, right: str) -> str:
    left = left.strip()
    right = right.strip()
    if not left:
        return right
    if not right:
        return left
    sep = " " if left.endswith((".", "!", "?", ":", ";", ",")) else ", "
    return f"{left}{sep}{right}"


def _message_offset_ms(message: Any) -> int | None:
    meta = getattr(message, "meta", None) or {}
    raw = meta.get("offset_ms") if isinstance(meta, dict) else None
    if isinstance(raw, int) and raw >= 0:
        return raw
    return None


def _transcript_turns_from_messages(messages: list[Any]) -> list[_TranscriptTurn]:
    turns: list[_TranscriptTurn] = []
    for message in messages:
        role = getattr(message.role, "value", message.role)
        if role not in (MessageRole.USER.value, MessageRole.ASSISTANT.value, "USER", "ASSISTANT"):
            continue
        text = _clean_text(getattr(message, "content", ""))
        if not text:
            continue
        message_id = str(getattr(message, "id", len(turns) + 1))
        role_str = "USER" if str(role) == "USER" else "ASSISTANT"
        if turns and turns[-1].role == role_str:
            prev = turns[-1]
            turns[-1] = _TranscriptTurn(
                id=prev.id,
                role=prev.role,
                text=_join_turn_text(prev.text, text),
                offset_ms=prev.offset_ms,
                source_message_ids=[*prev.source_message_ids, message_id],
            )
            continue
        turns.append(
            _TranscriptTurn(
                id=f"turn-{len(turns) + 1}",
                role=role_str,
                text=text,
                offset_ms=_message_offset_ms(message),
                source_message_ids=[message_id],
            )
        )
    return turns


def _transcript_block(turns: list[_TranscriptTurn]) -> str:
    if not turns:
        return "(no transcript)"
    return "\n".join(f"{turn.id} | {turn.role}: {turn.text}" for turn in turns)


def _quote_bank(turns: list[_TranscriptTurn]) -> str:
    learner_turns = [t for t in turns if t.role == "USER"]
    if not learner_turns:
        return "(no learner turns)"
    return "\n".join(f"{t.id}: {t.text}" for t in learner_turns)


def _rubric_items(snapshot: dict[str, Any] | None) -> list[_RubricItem]:
    snap = snapshot or {}
    raw_items = snap.get("rubric") if isinstance(snap.get("rubric"), list) else []
    out: list[_RubricItem] = []
    for item in raw_items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        try:
            max_score = int(item.get("max_score") or 5)
        except (TypeError, ValueError):
            max_score = 5
        out.append(
            _RubricItem(
                id=str(item["id"]),
                criterion=_clean_text(item.get("criterion") or "Criterion"),
                description=_clean_text(item.get("description") or ""),
                max_score=max(1, max_score),
            )
        )
    return out


def _rubric_block(items: list[_RubricItem]) -> str:
    if not items:
        return "(no rubric - provide overall feedback only)"
    return "\n".join(
        f"- id={item.id} | {item.criterion} | max_score={item.max_score} | {item.description}"
        for item in items
    )


def _scenario_block(snapshot: dict[str, Any] | None) -> str:
    snap = snapshot or {}
    cfg = snap.get("config") if isinstance(snap.get("config"), dict) else {}
    persona = snap.get("persona") if isinstance(snap.get("persona"), dict) else {}
    parts = [
        f"Title: {_clean_text(snap.get('title'))}",
        f"Description: {_clean_text(snap.get('description'))}",
        f"Agent role: {_clean_text(snap.get('agent_role'))}",
        f"Agent persona: {_clean_text(persona.get('name'))} - {_clean_text(persona.get('title'))}",
        f"Learner role: {_clean_text(cfg.get('learner_role'))}",
        f"Scenario notes: {_clean_text(cfg.get('config_notes'))}",
        f"Success criteria: {_clean_text(cfg.get('success_criteria'))}",
        f"Feedback guidance from the scenario author: {_clean_text(cfg.get('feedback_guidance'))}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


async def _run_agent(
    agent: Any,
    text: str,
    *,
    workflow: str,
    model: str,
    session_id: UUID,
    stage: str,
) -> Any:
    from agents import RunConfig, Runner

    started_at = model_call_started_at()
    run_config = RunConfig(
        workflow_name=workflow,
        group_id=str(session_id),
        tracing=openai_trace_config(),
        tracing_disabled=not openai_tracing_enabled(),
        trace_include_sensitive_data=settings.OPENAI_TRACING_INCLUDE_SENSITIVE_DATA,
        trace_metadata={
            "surface": "evaluation",
            "stage": stage,
            "session_id": str(session_id),
        },
    )
    try:
        result = await Runner.run(agent, input=text, run_config=run_config)
    except Exception as exc:
        log_model_call(
            logger,
            workflow=workflow,
            model=model,
            provider="openrouter",
            status="error",
            started_at=started_at,
            session_id=str(session_id),
            error=f"{type(exc).__name__}: {exc}",
            extra={"stage": stage, "agent": getattr(agent, "name", None)},
        )
        raise

    log_model_call(
        logger,
        workflow=workflow,
        model=model,
        provider="openrouter",
        status="success",
        started_at=started_at,
        session_id=str(session_id),
        usage_source=getattr(result.context_wrapper, "usage", None),
        extra={"stage": stage, "agent": getattr(agent, "name", None)},
    )
    return result.final_output


async def _agentic_evaluate(
    *,
    client: Any,
    scoring_model_name: str,
    evidence_model_name: str,
    review_model_name: str,
    snapshot: dict[str, Any],
    turns: list[_TranscriptTurn],
    rubric: list[_RubricItem],
    session_id: UUID,
) -> _FinalEvalPayload:
    from agents import Agent, OpenAIChatCompletionsModel, set_tracing_disabled

    try:
        from agents.tracing import set_tracing_export_api_key
    except ImportError:  # pragma: no cover - older SDKs
        set_tracing_export_api_key = None

    set_tracing_disabled(not openai_tracing_enabled())
    if openai_tracing_enabled() and set_tracing_export_api_key is not None:
        set_tracing_export_api_key(settings.OPENAI_API_KEY)
    scoring_model = OpenAIChatCompletionsModel(model=scoring_model_name, openai_client=client)
    evidence_model = OpenAIChatCompletionsModel(model=evidence_model_name, openai_client=client)
    review_model = OpenAIChatCompletionsModel(model=review_model_name, openai_client=client)

    shared_context = (
        "### Scenario\n"
        f"{_scenario_block(snapshot)}\n\n"
        "### Transcript\n"
        f"{_transcript_block(turns)}\n\n"
        "### Learner quote bank\n"
        f"{_quote_bank(turns)}\n\n"
        "### Rubric\n"
        f"{_rubric_block(rubric)}"
    )

    scoring_agent = Agent(
        name="Rubric scoring evaluator",
        model=scoring_model,
        output_type=_ScoreDraftPayload,
        instructions=(
            "You score completed Squinia workplace simulations. Grade only what is evidenced in the transcript. "
            "Use every rubric id exactly once. Scores must be integers within each rubric max_score. "
            "Write concise, customer-facing summaries."
        ),
    )
    evidence_agent = Agent(
        name="Evidence and improvement evaluator",
        model=evidence_model,
        output_type=_EvidencePayload,
        instructions=(
            "You identify exact learner evidence and specific coaching improvements. For each rubric id, choose "
            "one example_quote copied verbatim from the learner quote bank only. Do not quote the agent. "
            "The improvement should tell the learner what to do or what better wording could sound like next time."
        ),
    )
    reviewer_agent = Agent(
        name="Evaluation quality reviewer",
        model=review_model,
        output_type=_FinalEvalPayload,
        instructions=(
            "You are the final quality-control evaluator. Merge the scoring draft and evidence draft. "
            "Reject invented evidence. Every example_quote must be copied exactly from a USER turn in the quote bank. "
            "Every rubric id must match the rubric. Keep feedback direct, fair, and useful for a learner trying to improve."
        ),
    )

    scoring = await _run_agent(
        scoring_agent,
        shared_context,
        workflow="squinia.evaluation.scoring",
        model=scoring_model_name,
        session_id=session_id,
        stage="scoring",
    )
    evidence = await _run_agent(
        evidence_agent,
        shared_context,
        workflow="squinia.evaluation.evidence",
        model=evidence_model_name,
        session_id=session_id,
        stage="evidence",
    )
    review_input = (
        f"{shared_context}\n\n"
        "### Scoring draft\n"
        f"{scoring.model_dump_json()}\n\n"
        "### Evidence draft\n"
        f"{evidence.model_dump_json()}"
    )
    return await _run_agent(
        reviewer_agent,
        review_input,
        workflow="squinia.evaluation.review",
        model=review_model_name,
        session_id=session_id,
        stage="review",
    )


def _validated_quote(item: _FinalScoreItem, turns: list[_TranscriptTurn]) -> str:
    learner_turns = [t for t in turns if t.role == "USER"]
    quote = _clean_text(item.example_quote).strip('"')
    if quote:
        quote_norm = _normalized(quote)
        if any(quote_norm and quote_norm in _normalized(t.text) for t in learner_turns):
            return quote

    if item.quote_turn_id:
        chosen = next((t for t in learner_turns if t.id == item.quote_turn_id), None)
        if chosen:
            return chosen.text[:1200]

    return learner_turns[0].text[:1200] if learner_turns else ""


def _scores_to_complete_items(
    payload: _FinalEvalPayload,
    rubric: list[_RubricItem],
    turns: list[_TranscriptTurn],
) -> list[EvalScoreCompleteItem]:
    max_by_id = {item.id: item.max_score for item in rubric}
    by_id = {item.rubric_item_id: item for item in payload.scores}
    out: list[EvalScoreCompleteItem] = []
    for rubric_item in rubric:
        item = by_id.get(rubric_item.id)
        if not item:
            continue
        try:
            rid = UUID(str(item.rubric_item_id))
        except ValueError:
            continue
        cap = max_by_id.get(str(rid), rubric_item.max_score)
        score = min(max(0, int(item.score)), cap)
        summary = _clean_text(item.summary)[:4000]
        rationale = _clean_text(item.rationale or item.summary)[:4000]
        improvement = _clean_text(item.improvement)[:4000]
        quote = _validated_quote(item, turns)[:4000]
        out.append(
            EvalScoreCompleteItem(
                rubric_item_id=rid,
                score=score,
                rationale=rationale,
                summary=summary,
                example_quote=quote or None,
                improvement=improvement or None,
            )
        )
    return out


async def _mark_failed(session_id: UUID, message: str) -> None:
    async with db_manager.session_factory() as db:
        sessions = SessionRepository(db)
        evaluations = EvaluationRepository(db)
        row = await sessions.get_by_id(session_id)
        if not row:
            return
        ev = await evaluations.get_by_session(session_id, row.tenant_id)
        if ev:
            await evaluations.update(
                ev.id,
                row.tenant_id,
                {
                    "status": EvalStatus.FAILED,
                    "feedback_summary": message[:2000],
                    "completed_at": datetime.now(timezone.utc),
                },
            )
            await db.commit()


async def run_openai_evaluation_job(session_id: UUID) -> None:
    """Called after session end; fills evaluation scores or marks FAILED."""
    logger.info("evaluation_job_status", session_id=str(session_id), status="started")
    async with db_manager.session_factory() as db:
        sessions = SessionRepository(db)
        evaluations = EvaluationRepository(db)

        row = await sessions.get_by_id(session_id)
        if not row:
            logger.warning("evaluation_runner: session missing", session_id=str(session_id))
            logger.warning("evaluation_job_status", session_id=str(session_id), status="skipped", reason="session_missing")
            return

        tenant_id = row.tenant_id
        ev = await evaluations.get_by_session(session_id, tenant_id)
        if not ev:
            logger.warning("evaluation_runner: no evaluation row", session_id=str(session_id))
            logger.warning("evaluation_job_status", session_id=str(session_id), status="skipped", reason="evaluation_missing")
            return
        if ev.status not in (EvalStatus.PENDING, EvalStatus.PROCESSING):
            logger.info(
                "evaluation_job_status",
                session_id=str(session_id),
                status="skipped",
                reason="already_terminal",
                evaluation_status=getattr(ev.status, "value", str(ev.status)),
            )
            return

        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            await evaluations.update(
                ev.id,
                tenant_id,
                {
                    "status": EvalStatus.FAILED,
                    "feedback_summary": "OPENROUTER_API_KEY is not configured; evaluation was not run.",
                    "completed_at": datetime.now(timezone.utc),
                },
            )
            await db.commit()
            logger.warning(
                "evaluation_job_status",
                session_id=str(session_id),
                status="failed",
                reason="model_api_key_missing",
            )
            return

        logger.info("evaluation_job_status", session_id=str(session_id), status="processing")
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
        await _mark_failed(session_id, f"OpenAI SDK missing: {e}")
        return

    try:
        async with db_manager.session_factory() as db:
            sessions = SessionRepository(db)
            messages = MessageRepository(db)
            row = await sessions.get_by_id(session_id)
            if not row:
                return
            tenant_id = row.tenant_id
            snap = row.scenario_snapshot if isinstance(row.scenario_snapshot, dict) else {}
            msgs = await messages.list_for_session(session_id)
            turns = _transcript_turns_from_messages(msgs)
            rubric = _rubric_items(snap)

        client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY)
        default_model = settings.OPENAI_CHAT_MODEL or "gpt-4o-mini"
        payload = await _agentic_evaluate(
            client=client,
            scoring_model_name=settings.OPENAI_EVALUATION_SCORING_MODEL or default_model,
            evidence_model_name=settings.OPENAI_EVALUATION_EVIDENCE_MODEL or default_model,
            review_model_name=settings.OPENAI_EVALUATION_REVIEW_MODEL or default_model,
            snapshot=snap,
            turns=turns,
            rubric=rubric,
            session_id=session_id,
        )
    except ImportError as e:
        logger.exception("evaluation_runner: Agents SDK missing", session_id=str(session_id))
        logger.warning(
            "evaluation_job_status",
            session_id=str(session_id),
            status="failed",
            reason="agents_sdk_missing",
        )
        await _mark_failed(session_id, f"OpenAI Agents SDK missing: {e}")
        return
    except Exception as e:
        logger.exception("evaluation_runner: agentic evaluation failed", session_id=str(session_id))
        logger.warning(
            "evaluation_job_status",
            session_id=str(session_id),
            status="failed",
            reason="agentic_evaluation_failed",
        )
        await _mark_failed(session_id, f"Evaluation failed: {e!s}")
        return

    body = InternalEvalCompleteRequest(
        overall_score=min(100, max(0, payload.overall_score)),
        feedback_summary=_clean_text(payload.feedback_summary)[:8000],
        strengths=(_clean_text(payload.strengths) or None) if payload.strengths else None,
        improvements=(_clean_text(payload.improvements) or None) if payload.improvements else None,
        highlights=[
            {
                "kind": "agentic_evaluation_review",
                "note": _clean_text(payload.reviewer_notes)[:2000],
                "transcript_turns": len(turns),
            }
        ],
        scores=_scores_to_complete_items(payload, rubric, turns),
    )

    try:
        async with db_manager.session_factory() as db:
            svc = EvaluationService(db)
            ev3 = await svc.evaluations.get_by_session(session_id, tenant_id)
            if not ev3:
                return
            await svc.internal_complete(ev3.id, body)
            logger.info(
                "evaluation_job_status",
                session_id=str(session_id),
                status="completed",
                overall_score=body.overall_score,
                score_count=len(body.scores),
            )
    except Exception as e:
        logger.exception("evaluation_runner: persist failed", session_id=str(session_id))
        logger.warning(
            "evaluation_job_status",
            session_id=str(session_id),
            status="failed",
            reason="persist_failed",
        )
        await _mark_failed(session_id, f"Could not persist evaluation: {e!s}")
