from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.models.simulation.agent_persona import PersonaGender
from app.models.simulation.scenario import AgentRole, ScenarioDifficulty
from app.services.ai.scenario_prompt import compact_scenario_metadata, system_prompt_from_snapshot
from app.services.simulation.session import SessionService


def test_session_snapshot_embeds_reusable_persona_for_prompts_and_ui() -> None:
    persona_id = uuid4()
    scenario = SimpleNamespace(
        id=uuid4(),
        persona_id=persona_id,
        title="Production escalation call",
        description="Report a production incident to a team lead.",
        agent_role=AgentRole.PEER_DEVELOPER,
        difficulty=ScenarioDifficulty.ADVANCED,
        config={"feedback_guidance": "Focus on ownership and clarity."},
        persona=SimpleNamespace(
            id=persona_id,
            name="Julia Merrick",
            title="Technical team lead",
            gender=PersonaGender.FEMALE,
            avatar_url="https://example.com/julia.jpg",
            voice_provider="deepgram",
            voice_id="aura-athena-en",
            personality="Direct but fair.",
            communication_style="Concise and specific.",
            background="Leads incident response for the platform team.",
        ),
        rubric_items=[],
    )

    snapshot = SessionService(db=None)._snapshot_from_scenario(scenario)  # type: ignore[arg-type]

    assert snapshot["persona_id"] == str(persona_id)
    assert snapshot["persona"]["name"] == "Julia Merrick"
    assert snapshot["persona"]["voice_id"] == "aura-athena-en"
    assert snapshot["config"]["feedback_guidance"] == "Focus on ownership and clarity."


def test_prompt_metadata_prefers_reusable_persona_over_legacy_config() -> None:
    snapshot = {
        "title": "Stakeholder update",
        "agent_role": "CLIENT_STAKEHOLDER",
        "config": {
            "persona_name": "Legacy Name",
            "persona_title": "Legacy Title",
            "opening_message": "Give me the update.",
        },
        "persona": {
            "name": "Amara Blake",
            "title": "VP Customer Success",
            "gender": "FEMALE",
            "voice_provider": "deepgram",
            "voice_id": "aura-luna-en",
            "communication_style": "Warm, direct, and commercially aware.",
        },
    }

    prompt = system_prompt_from_snapshot(snapshot)
    metadata = compact_scenario_metadata(snapshot)

    assert "Amara Blake - VP Customer Success" in prompt
    assert "Legacy Name" not in prompt
    assert metadata["persona_name"] == "Amara Blake"
    assert metadata["voice_id"] == "aura-luna-en"
