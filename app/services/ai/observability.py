"""Observability helpers for model calls.

These helpers intentionally avoid logging prompts, transcripts, or model outputs.
Production traces should expose timing, model, status, and token counts without
leaking learner conversation content.
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.core.config import settings

T = TypeVar("T")


def model_call_started_at() -> float:
    return time.perf_counter()


def latency_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))


def openai_tracing_enabled() -> bool:
    return bool(settings.OPENAI_TRACING_ENABLED and (settings.OPENAI_API_KEY or "").strip())


def openai_trace_config() -> dict[str, str] | None:
    if not openai_tracing_enabled():
        return None
    return {"api_key": settings.OPENAI_API_KEY.strip()}


def model_usage_dict(source: Any) -> dict[str, int | None]:
    usage = getattr(source, "usage", source)
    if usage is None:
        return {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }

    input_tokens = _int_attr(usage, "input_tokens")
    output_tokens = _int_attr(usage, "output_tokens")
    total_tokens = _int_attr(usage, "total_tokens")

    prompt_tokens = _int_attr(usage, "prompt_tokens")
    completion_tokens = _int_attr(usage, "completion_tokens")

    if input_tokens is None:
        input_tokens = prompt_tokens
    if output_tokens is None:
        output_tokens = completion_tokens
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def trace_usage_dict(source: Any) -> dict[str, int] | None:
    usage = model_usage_dict(source)
    out: dict[str, int] = {}
    if usage["input_tokens"] is not None:
        out["input_tokens"] = int(usage["input_tokens"])
    if usage["output_tokens"] is not None:
        out["output_tokens"] = int(usage["output_tokens"])
    return out or None


def log_model_call(
    logger: Any,
    *,
    workflow: str,
    model: str,
    provider: str,
    status: str,
    started_at: float,
    session_id: str | None = None,
    usage_source: Any = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    usage = model_usage_dict(usage_source)
    payload: dict[str, Any] = {
        "workflow": workflow,
        "model": model,
        "provider": provider,
        "status": status,
        "latency_ms": latency_ms(started_at),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
    }
    if session_id:
        payload["session_id"] = session_id
    if error:
        payload["error"] = error[:500]
    if extra:
        payload.update(extra)

    if status == "success":
        logger.info("model_call", **payload)
    else:
        logger.warning("model_call", **payload)


async def traced_chat_completion(
    call: Callable[[], Awaitable[T]],
    *,
    workflow: str,
    model: str,
    provider: str,
    model_config: dict[str, Any],
    logger: Any,
    session_id: str | None = None,
    trace_metadata: dict[str, Any] | None = None,
) -> T:
    started_at = model_call_started_at()
    span = None
    try:
        if openai_tracing_enabled():
            try:
                from agents.tracing import generation_span, trace
            except ImportError:
                result = await call()
            else:
                with trace(
                    workflow,
                    group_id=session_id,
                    metadata=trace_metadata,
                    tracing=openai_trace_config(),
                ):
                    with generation_span(
                        model=model,
                        model_config=model_config,
                    ) as span:
                        result = await call()
                        span.span_data.usage = trace_usage_dict(result)
        else:
            result = await call()

        log_model_call(
            logger,
            workflow=workflow,
            model=model,
            provider=provider,
            status="success",
            started_at=started_at,
            session_id=session_id,
            usage_source=result,
        )
        return result
    except Exception as exc:
        if span is not None:
            span.set_error({"message": type(exc).__name__, "data": {"workflow": workflow}})
        log_model_call(
            logger,
            workflow=workflow,
            model=model,
            provider=provider,
            status="error",
            started_at=started_at,
            session_id=session_id,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise


def _int_attr(source: Any, name: str) -> int | None:
    if isinstance(source, dict):
        value = source.get(name)
    else:
        value = getattr(source, name, None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
