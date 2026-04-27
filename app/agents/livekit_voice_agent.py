"""LiveKit voice worker managed from within the backend codebase."""
from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, RoomInputOptions, WorkerOptions, cli, stt, llm, tts
from livekit.plugins import deepgram, noise_cancellation, openai, silero, groq, cartesia
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv()


logger = logging.getLogger("app.agents.livekit_voice_agent")

DEEPGRAM_VOICES = {
    "MALE": "aura-orion-en",
    "FEMALE": "aura-asteria-en",
    "UNSPECIFIED": "aura-asteria-en",
}

OPENAI_VOICES = {
    "MALE": "onyx",
    "FEMALE": "nova",
    "UNSPECIFIED": "alloy",
}

DEFAULT_CARTESIA_VOICE_ID = "79d424b3-f6f3-4299-87a1-5d9c0e25526f"


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _clean_metadata_value(metadata: dict, key: str) -> str:
    return str(metadata.get(key) or "").strip()


def _persona_gender(metadata: dict) -> str:
    gender = _clean_metadata_value(metadata, "persona_gender").upper()
    return gender if gender in {"MALE", "FEMALE"} else "UNSPECIFIED"


def _voice_provider(metadata: dict) -> str:
    provider = _clean_metadata_value(metadata, "voice_provider").lower()
    return provider if provider in {"deepgram", "cartesia", "openai"} else "deepgram"


def _deepgram_voice(metadata: dict) -> str:
    if _voice_provider(metadata) == "deepgram":
        voice_id = _clean_metadata_value(metadata, "voice_id")
        if voice_id:
            return voice_id
    return DEEPGRAM_VOICES[_persona_gender(metadata)]


def _openai_voice(metadata: dict) -> str:
    if _voice_provider(metadata) == "openai":
        voice_id = _clean_metadata_value(metadata, "voice_id")
        if voice_id:
            return voice_id
    gender = _persona_gender(metadata)
    return os.getenv(f"OPENAI_TTS_VOICE_{gender}", OPENAI_VOICES[gender]).strip() or OPENAI_VOICES[gender]


def _cartesia_voice(metadata: dict) -> str | None:
    if _voice_provider(metadata) == "cartesia":
        voice_id = _clean_metadata_value(metadata, "voice_id")
        if voice_id:
            return voice_id
    gender = _persona_gender(metadata)
    env_voice = os.getenv(f"CARTESIA_TTS_VOICE_{gender}_ID", "").strip()
    if env_voice:
        return env_voice
    if gender == "MALE":
        return None
    return os.getenv("CARTESIA_TTS_VOICE_DEFAULT_ID", DEFAULT_CARTESIA_VOICE_ID).strip() or DEFAULT_CARTESIA_VOICE_ID


def _tts_voice_specs(metadata: dict) -> list[tuple[str, str]]:
    preferred = _voice_provider(metadata)
    providers = [preferred] + [p for p in ("deepgram", "cartesia", "openai") if p != preferred]
    specs: list[tuple[str, str]] = []
    for provider in providers:
        if provider == "deepgram":
            specs.append(("deepgram", _deepgram_voice(metadata)))
        elif provider == "cartesia":
            voice = _cartesia_voice(metadata)
            if voice:
                specs.append(("cartesia", voice))
        elif provider == "openai":
            specs.append(("openai", _openai_voice(metadata)))
    return specs


def _tts_adapters_from_metadata(metadata: dict) -> list[tts.TTS]:
    adapters: list[tts.TTS] = []
    for provider, voice in _tts_voice_specs(metadata):
        if provider == "deepgram":
            adapters.append(deepgram.TTS(model=voice))
        elif provider == "cartesia":
            adapters.append(cartesia.TTS(model="sonic-3", voice=voice))
        elif provider == "openai":
            adapters.append(openai.TTS(model="gpt-4o-mini-tts", voice=voice))
    return adapters


def _turn_detection_model() -> object | None:
    if not _env_flag("LIVEKIT_TURN_DETECTION_ENABLED"):
        return None
    try:
        return MultilingualModel()
    except Exception:
        logger.warning(
            "LiveKit turn detection disabled because model assets are unavailable",
            exc_info=True,
        )
        return None


def _worker_port() -> int:
    raw = os.getenv("LIVEKIT_WORKER_PORT", "0").strip()
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid LIVEKIT_WORKER_PORT value %r; using ephemeral port", raw)
        return 0


class SimulationVoiceAgent(Agent):
    def __init__(self, instructions: str) -> None:
        super().__init__(
            instructions=instructions,
        )


async def entrypoint(ctx: JobContext) -> None:
    logger.info("LiveKit job received for room=%s", ctx.room.name)
    await ctx.connect()
    metadata_raw = getattr(ctx.job, "metadata", "") or ""
    try:
        metadata = json.loads(metadata_raw) if metadata_raw else {}
    except json.JSONDecodeError:
        metadata = {}
    participant_identity = str(metadata.get("participant_identity") or "").strip() or None
    if participant_identity:
        await ctx.wait_for_participant(identity=participant_identity)
    
    vad = silero.VAD.load()
    session = AgentSession(
        stt=stt.FallbackAdapter(
            [
                deepgram.STT(model="nova-3"),
                stt.StreamAdapter(stt=openai.STT(model="gpt-4o-transcribe"), vad=vad)
            ]
        ),
        # llm=openai.LLM(model="gpt-4.1-mini"),
        llm=llm.FallbackAdapter(
            [
                groq.LLM(model="llama-3.3-70b-versatile"),
                openai.LLM(model="gpt-4o-mini")
            ]
        ),
        # tts=openai.TTS(model="gpt-4o-mini-tts", voice="alloy"),
        tts=tts.FallbackAdapter(
            _tts_adapters_from_metadata(metadata)
        ),
        vad=vad,
        turn_detection=_turn_detection_model(),
        preemptive_generation=True,
    )

    scenario_prompt = str(metadata.get("scenario_prompt") or "").strip()
    instructions = scenario_prompt or (
        "You are Squinia's live simulation partner. Lead realistic interview and workplace "
        "communication practice. Speak first when the room opens, stay concise, and keep the "
        "simulation natural."
    )

    await session.start(
        agent=SimulationVoiceAgent(instructions),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
            participant_identity=participant_identity,
        ),
    )
    logger.info("Voice agent session started for room=%s participant=%s", ctx.room.name, participant_identity)
    opening_message = str(metadata.get("opening_message") or "").strip()
    scenario_title = str(metadata.get("scenario_title") or "").strip()
    if not opening_message:
        opening_message = (
            f"Thanks for joining. Let's begin {scenario_title}."
            if scenario_title
            else "Thanks for joining. Let's begin the simulation."
        )
    opening = session.say(opening_message, allow_interruptions=False)
    await opening
    logger.info("Voice agent opening line played for room=%s", ctx.room.name)
    logger.info("Voice agent joined room=%s", ctx.room.name)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    agent_name = os.getenv("LIVEKIT_AGENT_NAME", "squinia-voice-agent")
    logger.info("Starting integrated LiveKit worker for agent_name=%s", agent_name)
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=agent_name,
            port=_worker_port(),
        )
    )


if __name__ == "__main__":
    main()
