"""Seed realistic reusable personas and scenarios for a tenant.

Usage:
    uv run python scripts/seed_personas_and_scenarios.py
    uv run python scripts/seed_personas_and_scenarios.py --tenant-id <uuid> --created-by <user_uuid>
    uv run python scripts/seed_personas_and_scenarios.py --refresh-rubrics

The script is intentionally idempotent by persona name and scenario title within
the tenant. It updates seed-owned fields, creates missing rubrics, and can
refresh rubrics when requested.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.models.auth.membership import Membership, OrgRole
from app.models.simulation.agent_persona import AgentPersona, PersonaGender
from app.models.simulation.scenario import AgentRole, Scenario, ScenarioDifficulty, ScenarioStatus
from app.models.simulation.scenario_rubric_item import ScenarioRubricItem


@dataclass(frozen=True)
class PersonaSeed:
    key: str
    name: str
    title: str
    gender: PersonaGender
    voice_id: str
    personality: str
    communication_style: str
    background: str
    is_default: bool = False


@dataclass(frozen=True)
class RubricSeed:
    criterion: str
    description: str
    weight: int


@dataclass(frozen=True)
class ScenarioSeed:
    key: str
    title: str
    description: str
    persona_key: str
    agent_role: AgentRole
    difficulty: ScenarioDifficulty
    session_mode: str
    estimated_minutes: int
    learner_role: str
    opening_message: str
    success_criteria: str
    feedback_guidance: str
    config_notes: str
    rubric: list[RubricSeed]


PERSONAS: list[PersonaSeed] = [
    PersonaSeed(
        key="julia",
        name="Julia Merrick",
        title="Technical Team Lead",
        gender=PersonaGender.FEMALE,
        voice_id="aura-athena-en",
        personality="Direct, fair, calm under pressure, and focused on practical next steps.",
        communication_style="Concise and realistic. Asks one follow-up at a time and presses for specifics.",
        background=(
            "Julia leads a backend engineering team responsible for a production SaaS platform. "
            "She cares about user impact, rollback plans, testing, monitoring, and stakeholder updates."
        ),
        is_default=True,
    ),
    PersonaSeed(
        key="marcus",
        name="Marcus Reed",
        title="Senior Recruiter",
        gender=PersonaGender.MALE,
        voice_id="aura-orion-en",
        personality="Warm, observant, and politely persistent when answers are vague.",
        communication_style="Conversational and structured. Gives candidates space, then asks for concrete examples.",
        background=(
            "Marcus recruits for competitive software and AI roles. He listens for motivation, clarity, "
            "self-awareness, and whether the candidate can explain career decisions professionally."
        ),
    ),
    PersonaSeed(
        key="amara",
        name="Amara Blake",
        title="VP Customer Success",
        gender=PersonaGender.FEMALE,
        voice_id="aura-luna-en",
        personality="Commercially aware, calm, protective of customers, and direct about business risk.",
        communication_style="Executive, concise, and outcome-focused. Pushes for customer impact and next steps.",
        background=(
            "Amara owns strategic customer relationships. She expects clear escalation handling, empathy, "
            "business context, and credible commitments."
        ),
    ),
    PersonaSeed(
        key="priya",
        name="Priya Nair",
        title="Product Manager",
        gender=PersonaGender.FEMALE,
        voice_id="aura-asteria-en",
        personality="Curious, analytical, and protective of product priorities.",
        communication_style="Asks sharp clarifying questions about goals, trade-offs, users, and metrics.",
        background=(
            "Priya manages roadmap decisions for an AI product. She evaluates whether teammates can balance "
            "speed, quality, user value, and stakeholder alignment."
        ),
    ),
    PersonaSeed(
        key="david",
        name="David Okafor",
        title="Enterprise Client Stakeholder",
        gender=PersonaGender.MALE,
        voice_id="aura-arcas-en",
        personality="Professional, time-conscious, skeptical when answers are too technical or unclear.",
        communication_style="Business-first. Requests plain English explanations, timelines, and risk ownership.",
        background=(
            "David represents an enterprise client affected by product reliability and delivery commitments. "
            "He wants reassurance, transparency, and a practical recovery plan."
        ),
    ),
]


SCENARIOS: list[ScenarioSeed] = [
    ScenarioSeed(
        key="prod_bug_update",
        title="AI Engineer Reports Production Bug to Technical Lead",
        description=(
            "The learner joins an urgent call after a production bug affected users. They must explain "
            "what happened, communicate impact, describe the fix, and agree on next steps."
        ),
        persona_key="julia",
        agent_role=AgentRole.PEER_DEVELOPER,
        difficulty=ScenarioDifficulty.INTERMEDIATE,
        session_mode="VIDEO",
        estimated_minutes=8,
        learner_role="AI Engineer responsible for the affected production feature",
        opening_message=(
            "Hey, thanks for jumping on this quickly. I saw the incident report, but I need a clear update "
            "from you. What happened, who is affected, and what are we doing about it?"
        ),
        success_criteria=(
            "A strong learner explains the issue clearly, states user impact, takes ownership, avoids blame, "
            "describes the immediate fix, mentions testing or rollback, and gives a realistic timeline."
        ),
        feedback_guidance=(
            "Pay close attention to ownership, structure, user impact, rollback planning, timeline clarity, "
            "and whether the learner explains trade-offs without hiding behind jargon."
        ),
        config_notes=(
            "Julia should behave like a busy technical lead during a live incident. Ask about testing, rollback, "
            "monitoring, stakeholder communication, and whether similar edge cases may exist elsewhere."
        ),
        rubric=[
            RubricSeed("Ownership and accountability", "Takes responsibility, avoids blame, and communicates a clear plan.", 20),
            RubricSeed("Clarity of explanation", "Explains the bug, cause, and current status in understandable language.", 20),
            RubricSeed("User impact awareness", "Identifies who was affected, severity, and customer or business risk.", 20),
            RubricSeed("Risk and rollback thinking", "Mentions testing, rollback, monitoring, edge cases, or safeguards.", 20),
            RubricSeed("Professional presence", "Stays calm, concise, respectful, and responsive under pressure.", 20),
        ],
    ),
    ScenarioSeed(
        key="career_gap_recruiter",
        title="Candidate Explains Career Gap to Recruiter",
        description=(
            "The learner is in a recruiter screen and must explain a career gap or transition in a confident, "
            "honest, concise way while keeping the conversation focused on readiness for the role."
        ),
        persona_key="marcus",
        agent_role=AgentRole.HR_RECRUITER,
        difficulty=ScenarioDifficulty.BEGINNER,
        session_mode="VOICE",
        estimated_minutes=7,
        learner_role="Job candidate interviewing for an AI engineering role",
        opening_message=(
            "Thanks for making time today. I noticed a gap in your recent experience, and I would like to "
            "understand that before we talk more about the role. Can you walk me through it?"
        ),
        success_criteria=(
            "A strong learner answers honestly, avoids oversharing, reframes the gap around growth, connects "
            "back to the target role, and sounds confident without being defensive."
        ),
        feedback_guidance=(
            "Evaluate self-awareness, concise storytelling, confidence, relevance to the role, and whether the "
            "learner avoids defensive or vague explanations."
        ),
        config_notes=(
            "Marcus should be supportive but should probe if the learner is too vague, apologetic, or gives an "
            "answer that does not connect back to readiness for the role."
        ),
        rubric=[
            RubricSeed("Honest framing", "Explains the gap truthfully without sounding evasive or defensive.", 20),
            RubricSeed("Relevance to role", "Connects the explanation back to current readiness and job fit.", 20),
            RubricSeed("Confidence and tone", "Maintains calm, professional confidence.", 20),
            RubricSeed("Conciseness", "Keeps the answer focused and avoids unnecessary personal detail.", 20),
            RubricSeed("Growth narrative", "Shows learning, progress, or intentional preparation during the transition.", 20),
        ],
    ),
    ScenarioSeed(
        key="customer_escalation",
        title="Customer Escalation After Missed AI Delivery",
        description=(
            "The learner must respond to an upset customer stakeholder after an AI feature delivery slipped. "
            "They need to acknowledge the concern, explain the path forward, and rebuild confidence."
        ),
        persona_key="amara",
        agent_role=AgentRole.CLIENT_STAKEHOLDER,
        difficulty=ScenarioDifficulty.ADVANCED,
        session_mode="VIDEO",
        estimated_minutes=10,
        learner_role="Technical project owner speaking with a customer stakeholder",
        opening_message=(
            "I am going to be direct. We planned around this AI feature being ready this week, and now my team "
            "is hearing it has slipped. What exactly happened, and why should I trust the new plan?"
        ),
        success_criteria=(
            "A strong learner acknowledges impact, avoids excuses, gives a clear reason, proposes a concrete "
            "recovery plan, and sets expectations without overpromising."
        ),
        feedback_guidance=(
            "Focus on empathy, executive clarity, customer impact, repair of trust, specificity of the recovery "
            "plan, and whether the learner avoids technical over-explaining."
        ),
        config_notes=(
            "Amara should represent an important customer. She should press on trust, timeline, impact, and what "
            "will be different this time. Keep the tone professional, not hostile."
        ),
        rubric=[
            RubricSeed("Empathy and acknowledgement", "Recognizes customer impact before explaining internally.", 20),
            RubricSeed("Plain-English clarity", "Explains the delay without hiding behind technical detail.", 20),
            RubricSeed("Recovery plan", "Provides concrete next steps, owners, and timeline.", 20),
            RubricSeed("Trust repair", "Shows accountability and explains how recurrence will be reduced.", 20),
            RubricSeed("Expectation management", "Avoids overpromising and handles uncertainty professionally.", 20),
        ],
    ),
    ScenarioSeed(
        key="product_tradeoff",
        title="Engineer Negotiates AI Feature Scope With Product Manager",
        description=(
            "The learner must explain implementation trade-offs for an AI feature and negotiate a smaller, safer "
            "scope without sounding obstructive."
        ),
        persona_key="priya",
        agent_role=AgentRole.PRODUCT_MANAGER,
        difficulty=ScenarioDifficulty.INTERMEDIATE,
        session_mode="CHAT",
        estimated_minutes=8,
        learner_role="Engineer partnering with product on an AI feature release",
        opening_message=(
            "I want us to ship this feature in the next sprint, but engineering flagged some concerns. What is "
            "actually risky here, and what version can we safely release?"
        ),
        success_criteria=(
            "A strong learner explains trade-offs clearly, proposes an MVP, ties decisions to user value, and "
            "offers a path to iterate instead of simply saying no."
        ),
        feedback_guidance=(
            "Evaluate trade-off communication, ability to propose options, user-value framing, collaboration, "
            "and whether the learner avoids sounding dismissive or overly technical."
        ),
        config_notes=(
            "Priya should push for user value and timeline. Ask about what can ship now, what must wait, how risk "
            "will be measured, and what success metric matters."
        ),
        rubric=[
            RubricSeed("Trade-off explanation", "Explains technical risk in product-relevant terms.", 20),
            RubricSeed("Option generation", "Offers practical alternatives instead of only blocking.", 20),
            RubricSeed("User-value framing", "Connects recommendations to users and product outcomes.", 20),
            RubricSeed("Collaboration", "Maintains partnership and avoids defensive language.", 20),
            RubricSeed("Next-step clarity", "Defines decision, owner, metric, or follow-up plan.", 20),
        ],
    ),
    ScenarioSeed(
        key="client_status_update",
        title="Plain-English AI Project Status Update to Client",
        description=(
            "The learner must give a client stakeholder a clear status update on an AI project, including progress, "
            "risks, blockers, and next milestones without using unnecessary jargon."
        ),
        persona_key="david",
        agent_role=AgentRole.CLIENT_STAKEHOLDER,
        difficulty=ScenarioDifficulty.INTERMEDIATE,
        session_mode="VOICE",
        estimated_minutes=7,
        learner_role="AI consultant giving a project update to an enterprise client",
        opening_message=(
            "Thanks for joining. I need a simple status update today: where are we, what is at risk, and what "
            "should I tell my leadership team?"
        ),
        success_criteria=(
            "A strong learner gives a structured update, uses plain English, identifies risks honestly, explains "
            "next steps, and gives the stakeholder language they can reuse."
        ),
        feedback_guidance=(
            "Evaluate structure, plain-English communication, business relevance, risk transparency, and whether "
            "the learner gives useful next steps rather than vague reassurance."
        ),
        config_notes=(
            "David should ask for clarity when the learner uses jargon. Press for dates, owners, risk severity, "
            "and what leadership should know."
        ),
        rubric=[
            RubricSeed("Structured update", "Covers progress, risks, blockers, and next milestones clearly.", 20),
            RubricSeed("Plain English", "Avoids unnecessary jargon and explains AI concepts simply.", 20),
            RubricSeed("Business relevance", "Connects technical progress to stakeholder priorities.", 20),
            RubricSeed("Risk transparency", "Names risks honestly without causing panic.", 20),
            RubricSeed("Actionable next steps", "Provides dates, owners, or decisions needed.", 20),
        ],
    ),
]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed Squinia personas and scenarios for a tenant.")
    parser.add_argument("--tenant-id", type=UUID, default=None, help="Tenant UUID to seed into.")
    parser.add_argument("--created-by", type=UUID, default=None, help="User UUID to use as creator.")
    parser.add_argument("--draft", action="store_true", help="Create/update scenarios as DRAFT instead of PUBLISHED.")
    parser.add_argument("--refresh-rubrics", action="store_true", help="Replace existing rubric items for seeded scenarios.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be seeded without writing.")
    return parser


async def _resolve_actor(db, tenant_id: UUID | None, created_by: UUID | None) -> tuple[UUID, UUID]:
    if tenant_id and created_by:
        return tenant_id, created_by

    roles = (OrgRole.ORG_OWNER, OrgRole.ORG_ADMIN, OrgRole.INSTRUCTOR)
    stmt = (
        select(Membership)
        .where(Membership.deleted_at.is_(None), Membership.is_active.is_(True), Membership.role.in_(roles))
        .order_by(
            Membership.role.asc(),
            Membership.joined_at.asc(),
        )
        .limit(1)
    )
    if tenant_id:
        stmt = stmt.where(Membership.tenant_id == tenant_id)
    if created_by:
        stmt = stmt.where(Membership.user_id == created_by)

    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()
    if not membership:
        raise RuntimeError(
            "Could not find an active org owner/admin/instructor membership. "
            "Pass --tenant-id and --created-by explicitly."
        )
    return membership.tenant_id, membership.user_id


async def _upsert_persona(db, tenant_id: UUID, created_by: UUID, seed: PersonaSeed, *, dry_run: bool) -> AgentPersona | None:
    stmt = select(AgentPersona).where(
        AgentPersona.tenant_id == tenant_id,
        AgentPersona.name == seed.name,
        AgentPersona.deleted_at.is_(None),
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    payload = {
        "title": seed.title,
        "gender": seed.gender,
        "avatar_url": None,
        "voice_provider": "deepgram",
        "voice_id": seed.voice_id,
        "personality": seed.personality,
        "communication_style": seed.communication_style,
        "background": seed.background,
        "is_default": seed.is_default,
        "meta": {"seed_key": seed.key},
    }
    if dry_run:
        print(f"[dry-run] {'update' if existing else 'create'} persona: {seed.name}")
        return existing
    if seed.is_default:
        await db.execute(
            update(AgentPersona)
            .where(AgentPersona.tenant_id == tenant_id, AgentPersona.deleted_at.is_(None))
            .values(is_default=False)
        )
    if existing:
        await db.execute(update(AgentPersona).where(AgentPersona.id == existing.id).values(**payload))
        await db.flush()
        return (await db.execute(select(AgentPersona).where(AgentPersona.id == existing.id))).scalar_one()
    row = AgentPersona(tenant_id=tenant_id, created_by=created_by, name=seed.name, **payload)
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


def _scenario_config(seed: ScenarioSeed) -> dict[str, Any]:
    return {
        "learner_role": seed.learner_role,
        "opening_message": seed.opening_message,
        "success_criteria": seed.success_criteria,
        "feedback_guidance": seed.feedback_guidance,
        "config_notes": seed.config_notes,
        "session_mode": seed.session_mode,
        "seed_key": seed.key,
    }


async def _replace_rubric(db, scenario_id: UUID, rubric: list[RubricSeed]) -> None:
    await db.execute(delete(ScenarioRubricItem).where(ScenarioRubricItem.scenario_id == scenario_id))
    for index, item in enumerate(rubric):
        db.add(
            ScenarioRubricItem(
                scenario_id=scenario_id,
                criterion=item.criterion,
                description=item.description,
                max_score=item.weight,
                weight=item.weight,
                sort_order=index,
            )
        )
    await db.flush()


async def _upsert_scenario(
    db,
    tenant_id: UUID,
    created_by: UUID,
    seed: ScenarioSeed,
    persona_by_key: dict[str, AgentPersona],
    *,
    published: bool,
    refresh_rubrics: bool,
    dry_run: bool,
) -> None:
    persona = persona_by_key[seed.persona_key]
    existing = (
        await db.execute(
            select(Scenario).where(
                Scenario.tenant_id == tenant_id,
                Scenario.title == seed.title,
                Scenario.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    status = ScenarioStatus.PUBLISHED if published else ScenarioStatus.DRAFT
    payload = {
        "description": seed.description,
        "persona_id": persona.id,
        "agent_role": seed.agent_role,
        "difficulty": seed.difficulty,
        "status": status,
        "config": _scenario_config(seed),
        "estimated_minutes": seed.estimated_minutes,
        "is_template": False,
    }
    if dry_run:
        print(f"[dry-run] {'update' if existing else 'create'} scenario: {seed.title}")
        print(f"[dry-run] attach persona: {persona.name}; rubric items: {len(seed.rubric)}")
        return
    if existing:
        await db.execute(update(Scenario).where(Scenario.id == existing.id).values(**payload))
        scenario_id = existing.id
    else:
        row = Scenario(tenant_id=tenant_id, created_by=created_by, title=seed.title, **payload)
        db.add(row)
        await db.flush()
        scenario_id = row.id

    count = (
        await db.execute(
            select(func.count()).select_from(ScenarioRubricItem).where(ScenarioRubricItem.scenario_id == scenario_id)
        )
    ).scalar_one()
    if refresh_rubrics or int(count or 0) == 0:
        await _replace_rubric(db, scenario_id, seed.rubric)


async def main() -> None:
    args = _parser().parse_args()
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        tenant_id, created_by = await _resolve_actor(db, args.tenant_id, args.created_by)
        print(f"Seeding tenant={tenant_id} created_by={created_by}")
        persona_by_key: dict[str, AgentPersona] = {}
        for seed in PERSONAS:
            persona = await _upsert_persona(db, tenant_id, created_by, seed, dry_run=args.dry_run)
            if persona is not None:
                persona_by_key[seed.key] = persona
        if args.dry_run:
            persona_by_key = {
                seed.key: AgentPersona(id=UUID(int=i + 1), tenant_id=tenant_id, created_by=created_by, name=seed.name)
                for i, seed in enumerate(PERSONAS)
            }
        for seed in SCENARIOS:
            await _upsert_scenario(
                db,
                tenant_id,
                created_by,
                seed,
                persona_by_key,
                published=not args.draft,
                refresh_rubrics=args.refresh_rubrics,
                dry_run=args.dry_run,
            )
        if args.dry_run:
            await db.rollback()
            print("Dry run complete. No changes written.")
        else:
            await db.commit()
            print(f"Seeded {len(PERSONAS)} personas and {len(SCENARIOS)} scenarios.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
