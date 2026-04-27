from __future__ import annotations

import app.agents.livekit_voice_agent as voice_agent
from app.agents.livekit_voice_agent import _tts_voice_specs


def test_openai_tts_voice_uses_gender_default() -> None:
    specs = _tts_voice_specs(
        {
            "voice_provider": "openai",
            "persona_gender": "FEMALE",
        }
    )

    assert specs[0] == ("openai", "nova")
    assert ("deepgram", "aura-asteria-en") in specs


def test_openai_tts_voice_id_overrides_gender_default() -> None:
    specs = _tts_voice_specs(
        {
            "voice_provider": "openai",
            "persona_gender": "MALE",
            "voice_id": "echo",
        }
    )

    assert specs[0] == ("openai", "echo")


def test_cartesia_tts_uses_persona_voice_id_first() -> None:
    specs = _tts_voice_specs(
        {
            "voice_provider": "cartesia",
            "persona_gender": "MALE",
            "voice_id": "cartesia-male-voice-id",
        }
    )

    assert specs[0] == ("cartesia", "cartesia-male-voice-id")
    assert ("openai", "onyx") in specs


def test_cartesia_male_without_config_skips_to_gendered_openai_fallback(monkeypatch) -> None:
    monkeypatch.delenv("CARTESIA_TTS_VOICE_MALE_ID", raising=False)

    specs = _tts_voice_specs(
        {
            "voice_provider": "cartesia",
            "persona_gender": "MALE",
        }
    )

    assert specs[0] == ("deepgram", "aura-orion-en")
    assert ("openai", "onyx") in specs


def test_cartesia_gender_can_be_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CARTESIA_TTS_VOICE_FEMALE_ID", "cartesia-female-default")

    specs = _tts_voice_specs(
        {
            "voice_provider": "cartesia",
            "persona_gender": "FEMALE",
        }
    )

    assert specs[0] == ("cartesia", "cartesia-female-default")


def test_turn_detection_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("LIVEKIT_TURN_DETECTION_ENABLED", raising=False)

    assert voice_agent._turn_detection_model() is None


def test_turn_detection_missing_assets_do_not_crash_worker(monkeypatch) -> None:
    class MissingModel:
        def __init__(self) -> None:
            raise RuntimeError("missing model files")

    monkeypatch.setenv("LIVEKIT_TURN_DETECTION_ENABLED", "true")
    monkeypatch.setattr(voice_agent, "MultilingualModel", MissingModel)

    assert voice_agent._turn_detection_model() is None


def test_worker_uses_ephemeral_port_by_default(monkeypatch) -> None:
    monkeypatch.delenv("LIVEKIT_WORKER_PORT", raising=False)

    assert voice_agent._worker_port() == 0
