"""TEXT simulation over HTTP — facilitator opens first, then one completion per user message (twin-style)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models.simulation.message import MessageRole
from app.repositories.simulation import MessageRepository, SessionRepository
from app.services.ai.scenario_prompt import system_prompt_from_snapshot

logger = get_logger(__name__)


async def complete_text_opening_turn(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    if not settings.OPENAI_API_KEY:
        raise AppError(
            status_code=503,
            code="OPENAI_NOT_CONFIGURED",
            message="OPENAI_API_KEY is not set; chat simulations are unavailable.",
        )
    try:
        from openai import AsyncOpenAI
    except ImportError as e:  # pragma: no cover
        raise AppError(status_code=500, code="OPENAI_SDK_MISSING", message=str(e)) from e

    # client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )
    model = settings.OPENAI_CHAT_MODEL or "gpt-4o-mini"

    sessions = SessionRepository(db)
    messages = MessageRepository(db)
    row = await sessions.get(session_id, tenant_id)
    if not row or row.user_id != user_id:
        raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")

    existing = await messages.list_for_session(session_id)
    first_assistant = next((m for m in existing if m.role == MessageRole.ASSISTANT), None)
    if first_assistant:
        return {
            "assistant_content": (first_assistant.content or "").strip() or "…",
            "assistant_turn": first_assistant.turn_number,
        }

    snap = row.scenario_snapshot if isinstance(row.scenario_snapshot, dict) else None
    base = system_prompt_from_snapshot(snap)
    opener_system = (
        base
        + "\n\nThe learner has just entered. You speak first: one in-character opening that fits the scenario. "
        "Be concise (about one short paragraph). Do not quote these instructions."
    )
    chat_messages: list[dict[str, str]] = [
        {"role": "system", "content": opener_system},
        {
            "role": "user",
            "content": "[Session start — produce only your opening line as the facilitator.]",
        },
    ]

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=chat_messages,
            stream=False,
            temperature=0.7,
            max_tokens=900,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.exception("OpenAI opening failed", session_id=str(session_id), error=str(e))
        raise AppError(
            status_code=502,
            code="OPENAI_ERROR",
            message=f"The assistant could not respond. Try again in a moment. ({str(e)})",
        ) from None

    raw = completion.choices[0].message.content if completion.choices else None
    full = (raw or "").strip() or "…"

    try:
        await messages.create(
            {
                "session_id": session_id,
                "role": MessageRole.ASSISTANT,
                "content": full,
                "content_type": "text",
                "meta": {"model": model, "kind": "opening"},
                "turn_number": 1,
            },
        )
        await sessions.update(session_id, row.tenant_id, {"turn_count": 1})
    except IntegrityError:
        await db.rollback()
        messages = MessageRepository(db)
        existing2 = await messages.list_for_session(session_id)
        winner = next((m for m in existing2 if m.role == MessageRole.ASSISTANT), None)
        if not winner:
            raise AppError(status_code=500, code="OPENING_RACE", message="Could not load opening message.") from None
        return {
            "assistant_content": (winner.content or "").strip() or "…",
            "assistant_turn": winner.turn_number,
        }

    return {"assistant_content": full, "assistant_turn": 1}


async def complete_text_chat_turn(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: UUID,
    user_id: UUID,
    user_text: str,
) -> dict[str, Any]:
    if not settings.OPENAI_API_KEY:
        raise AppError(
            status_code=503,
            code="OPENAI_NOT_CONFIGURED",
            message="OPENAI_API_KEY is not set; chat simulations are unavailable.",
        )
    try:
        from openai import AsyncOpenAI
    except ImportError as e:  # pragma: no cover
        raise AppError(status_code=500, code="OPENAI_SDK_MISSING", message=str(e)) from e

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )
    model = settings.OPENAI_CHAT_MODEL or "gpt-4o-mini"

    sessions = SessionRepository(db)
    messages = MessageRepository(db)
    row = await sessions.get(session_id, tenant_id)
    if not row or row.user_id != user_id:
        raise AppError(status_code=404, code="NOT_FOUND", message="Session not found")

    max_t = await messages.get_max_turn(session_id)
    user_turn = max_t + 1
    assistant_turn = max_t + 2
    snap = row.scenario_snapshot if isinstance(row.scenario_snapshot, dict) else None
    system_prompt = system_prompt_from_snapshot(snap)

    await messages.create(
        {
            "session_id": session_id,
            "role": MessageRole.USER,
            "content": user_text,
            "content_type": "text",
            "meta": {},
            "turn_number": user_turn,
        },
    )

    history = await messages.list_for_session(session_id)
    chat_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for m in history:
        if m.role == MessageRole.USER:
            chat_messages.append({"role": "user", "content": m.content})
        elif m.role == MessageRole.ASSISTANT:
            chat_messages.append({"role": "assistant", "content": m.content})

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=chat_messages,
            stream=False,
            temperature=0.7,
            max_tokens=2000,
        )
    except Exception:
        logger.exception("OpenAI chat failed", session_id=str(session_id))
        raise AppError(
            status_code=502,
            code="OPENAI_ERROR",
            message="The assistant could not respond. Try again in a moment.",
        ) from None

    raw_content = completion.choices[0].message.content if completion.choices else None
    full = (raw_content or "").strip() or "…"

    await messages.create(
        {
            "session_id": session_id,
            "role": MessageRole.ASSISTANT,
            "content": full,
            "content_type": "text",
            "meta": {"model": model},
            "turn_number": assistant_turn,
        },
    )
    await sessions.update(
        session_id,
        row.tenant_id,
        {"turn_count": assistant_turn},
    )

    return {
        "assistant_content": full,
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
    }
