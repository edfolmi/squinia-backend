from __future__ import annotations

from app.services.ai import observability


def test_model_usage_dict_normalizes_openai_chat_usage() -> None:
    class Usage:
        prompt_tokens = 12
        completion_tokens = 8
        total_tokens = 20

    class Completion:
        usage = Usage()

    assert observability.model_usage_dict(Completion()) == {
        "input_tokens": 12,
        "output_tokens": 8,
        "total_tokens": 20,
    }


def test_model_usage_dict_accepts_responses_style_usage() -> None:
    assert observability.model_usage_dict(
        {"input_tokens": 30, "output_tokens": 11, "total_tokens": 41}
    ) == {
        "input_tokens": 30,
        "output_tokens": 11,
        "total_tokens": 41,
    }


def test_openai_tracing_requires_feature_flag_and_api_key(monkeypatch) -> None:
    monkeypatch.setattr(observability.settings, "OPENAI_TRACING_ENABLED", True)
    monkeypatch.setattr(observability.settings, "OPENAI_API_KEY", "")

    assert observability.openai_tracing_enabled() is False

    monkeypatch.setattr(observability.settings, "OPENAI_API_KEY", "sk-test")

    assert observability.openai_tracing_enabled() is True
