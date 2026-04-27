"""Scenario-aware prompt construction shared by text and LiveKit agents."""
from __future__ import annotations

from typing import Any


ROLE_LABELS = {
    "TECHNICAL_INTERVIEWER": "technical interviewer",
    "HR_RECRUITER": "HR recruiter",
    "PRODUCT_MANAGER": "product manager",
    "PEER_DEVELOPER": "peer developer",
    "CLIENT_STAKEHOLDER": "client stakeholder",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def system_prompt_from_snapshot(snapshot: dict[str, Any] | None) -> str:
    snap = snapshot or {}
    cfg = snap.get("config") if isinstance(snap.get("config"), dict) else {}
    persona = snap.get("persona") if isinstance(snap.get("persona"), dict) else {}

    title = _clean(snap.get("title")) or "Simulation"
    desc = _clean(snap.get("description"))
    agent_role = _clean(snap.get("agent_role")).upper()
    learner_role = _clean(cfg.get("learner_role"))
    persona_name = _clean(persona.get("name") or cfg.get("persona_name"))
    persona_title = _clean(persona.get("title") or cfg.get("persona_title") or cfg.get("persona_role"))
    persona_gender = _clean(persona.get("gender"))
    persona_traits = _clean(persona.get("personality"))
    persona_style = _clean(persona.get("communication_style"))
    persona_background = _clean(persona.get("background"))
    opening_message = _clean(cfg.get("opening_message"))
    success_criteria = _clean(cfg.get("success_criteria"))
    notes = _clean(cfg.get("config_notes"))
    custom_system = _clean(cfg.get("system_prompt"))

    role_label = ROLE_LABELS.get(agent_role, agent_role.replace("_", " ").lower() or "simulation partner")

    parts = [
        custom_system,
        f"You are Squinia's AI simulation partner for the scenario: {title}.",
        f"Scenario description: {desc}" if desc else "",
        f"You are playing: {persona_name}{(' - ' + persona_title) if persona_title else ''}." if persona_name else "",
        f"Persona presentation: {persona_gender.lower()}." if persona_gender else "",
        f"Persona personality: {persona_traits}" if persona_traits else "",
        f"Persona communication style: {persona_style}" if persona_style else "",
        f"Persona background: {persona_background}" if persona_background else "",
        f"Your functional role is: {role_label}.",
        f"The learner is playing: {learner_role}." if learner_role else "",
        f"Success criteria for the learner: {success_criteria}" if success_criteria else "",
        f"Organisation scenario notes and constraints: {notes}" if notes else "",
        "The learner has already read the scenario expectations before entering the room.",
        "Start the conversation in character. Do not ask the learner to repeat the scenario brief.",
        "Drive a realistic workplace or interview conversation with one clear prompt at a time.",
        "Adapt to what the learner says. Press for specifics, tradeoffs, risks, or next steps when the scenario calls for it.",
        "Stay concise and natural. Avoid coaching, scoring, or explaining the rubric during the simulation.",
        "When the learner clearly closes or the scenario is complete, close naturally in character and do not introduce a new topic.",
    ]
    if opening_message:
        parts.append(f"If this is the first turn, use this opening intent or wording: {opening_message}")
    return "\n".join(p for p in parts if p)


def compact_scenario_metadata(snapshot: dict[str, Any] | None, *, max_chars: int = 12000) -> dict[str, Any]:
    """Small metadata payload for LiveKit dispatch."""
    prompt = system_prompt_from_snapshot(snapshot)
    if len(prompt) > max_chars:
        prompt = prompt[: max_chars - 20].rstrip() + "\n[truncated]"
    snap = snapshot or {}
    cfg = snap.get("config") if isinstance(snap.get("config"), dict) else {}
    persona = snap.get("persona") if isinstance(snap.get("persona"), dict) else {}
    return {
        "scenario_title": _clean(snap.get("title")),
        "agent_role": _clean(snap.get("agent_role")),
        "persona_name": _clean(persona.get("name") or cfg.get("persona_name")),
        "persona_title": _clean(persona.get("title") or cfg.get("persona_title") or cfg.get("persona_role")),
        "persona_gender": _clean(persona.get("gender")),
        "persona_avatar_url": _clean(persona.get("avatar_url")),
        "voice_provider": _clean(persona.get("voice_provider")),
        "voice_id": _clean(persona.get("voice_id")),
        "opening_message": _clean(cfg.get("opening_message")),
        "scenario_prompt": prompt,
    }
