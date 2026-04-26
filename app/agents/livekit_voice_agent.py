"""LiveKit voice worker managed from within the backend codebase."""
from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, RoomInputOptions, WorkerOptions, cli
from livekit.plugins import deepgram, noise_cancellation, openai, silero, groq

load_dotenv()


logger = logging.getLogger("app.agents.livekit_voice_agent")


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

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        # llm=openai.LLM(model="gpt-4.1-mini"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        # tts=openai.TTS(model="gpt-4o-mini-tts", voice="alloy"),
        tts=deepgram.TTS(model="aura-asteria-en"),
        vad=silero.VAD.load(),
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
        )
    )


if __name__ == "__main__":
    main()
