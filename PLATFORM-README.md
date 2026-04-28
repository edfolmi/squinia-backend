# Squinia

Squinia is an AI simulation platform for organizations, bootcamps, and training teams that want learners to practice real workplace conversations before they face them in production environments.

Live platform: https://squinia-frontend.vercel.app/

The platform lets an organization create interview, escalation, stakeholder, leadership, or soft-skills scenarios; assign reusable AI personas; run practice through chat, phone, or video; capture transcripts; and generate rubric-based feedback with exact examples from the learner's conversation.

## Why Squinia Exists

Most professional communication training is passive: learners read advice, watch examples, or receive feedback after real mistakes. Squinia turns that into an active practice loop.

The learner enters a realistic scenario, speaks with an AI persona that behaves according to the organization's setup, and receives feedback that identifies strengths, weaknesses, transcript evidence, and concrete improvement suggestions.

The core problem is not simply "chat with an AI." The goal is to help learners become more professional by repeatedly practicing the moments where communication quality matters: reporting production issues, handling customers, explaining technical trade-offs, interviewing, giving updates, and responding under pressure.

## Product Scope

Squinia focuses on three roles:

- Organizations and bootcamps create scenarios, personas, cohorts, assignments, and rubrics.
- Learners practice scenarios through text chat, phone-style calls, or video calls.
- Evaluator agents score the session and return actionable feedback.

The MVP deliberately prioritizes a high-quality simulation and evaluation loop over broad LMS features. That trade-off keeps the product focused on practice quality, transcript capture, and feedback usefulness.

## Key Features

- Multi-tenant organization accounts
- Cohorts, assignments, scenarios, and rubric setup
- Reusable AI personas with name, title, gender, voice provider, voice id, personality, communication style, background, and avatar
- Chat simulations with prompt-injection and jailbreak guardrails
- Phone and video simulations through LiveKit
- Persona-aware voice selection for Deepgram, Cartesia, and OpenAI TTS
- Scenario-specific AI behavior and opening messages
- Transcript capture for chat, phone, and video sessions
- Agentic evaluation pipeline with rubric scores, transcript evidence, and improvement guidance
- Learner report pages with recording playback, transcript, score, examples, and recommendations
- Backend deployment on AWS ECS behind a load balancer
- Frontend deployment on Vercel

## System Overview

```text
Learner / Organization UI
        |
        v
Next.js Frontend on Vercel
        |
        v
FastAPI Backend on AWS ECS behind an Application Load Balancer
        |
        +--> PostgreSQL for tenants, users, scenarios, personas, sessions, transcripts, evaluations
        +--> Redis for cache/session-adjacent runtime support
        +--> OpenRouter/OpenAI for chat, guardrails, and evaluation
        +--> LiveKit Cloud for phone and video rooms
        +--> Deepgram / Cartesia / OpenAI for voice and transcription providers
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full technical design.

## Repository Layout

```text
Squinia/
  squinia-frontend/   Next.js application deployed on Vercel
  squinia-backend/    FastAPI API, AI services, persistence, deployment assets
  README.md           Product and capstone overview
  ARCHITECTURE.md     System architecture and AI pipeline
```

## Main User Flow

1. Organization creates or selects an AI persona.
2. Organization creates a scenario with expectations, opening message, evaluation guidance, and rubric criteria.
3. Learner starts a chat, phone, or video simulation.
4. The AI persona opens the session in character and follows the scenario.
5. Squinia stores the transcript and relevant session metadata.
6. Evaluation agents score the learner against the rubric.
7. Learner reviews a report with score, transcript, examples, and improvement guidance.

## AI Design

Squinia uses AI in three main places:

- **Simulation agent:** acts as the scenario persona and keeps the conversation realistic.
- **Guardrail agent:** checks chat input for prompt injection or jailbreak behavior before it reaches the simulation agent.
- **Evaluation agents:** analyze transcripts, produce rubric scores, identify examples, recommend improvements, and review quality.

This separation keeps role-play, safety, and assessment responsibilities independent and easier to test.

## Production Deployment

Current deployment:

- Frontend: Vercel
- Backend: AWS ECS
- Traffic: AWS load balancer in front of the backend service
- Realtime voice/video: LiveKit Cloud
- Database: PostgreSQL
- Cache: Redis-compatible service

Backend deployment notes are documented in `squinia-backend/DEPLOYMENT_AWS.md`.

## Local Development

Frontend:

```bash
cd squinia-frontend
npm install
npm run dev
```

Backend:

```bash
cd squinia-backend
uv sync
alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8888
```

Common environment variables:

- `NEXT_PUBLIC_API_BASE`
- `OPENROUTER_API_KEY`
- `OPENROUTER_CHAT_MODEL`
- `OPENROUTER_GUARD_MODEL`
- `OPENAI_API_KEY`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `DEEPGRAM_API_KEY`
- `CARTESIA_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`

## Testing

Backend focused tests:

```bash
cd squinia-backend
uv run pytest -q
```

Frontend checks:

```bash
cd squinia-frontend
npm run build
npm run lint
```

The most important test coverage today is around authentication, transcript ingestion, persona prompt metadata, LiveKit voice selection, and chat guardrails. The next priority is broader frontend tests for scenario cards, chat streaming UX, and report rendering.

## Demo Script

Recommended peer-review demo:

1. Show the organization dashboard.
2. Create or select a reusable persona with avatar and voice configuration.
3. Create a scenario with opening message, learner expectations, evaluation guidance, and rubric criteria.
4. Start a learner simulation.
5. Show the AI persona opening the conversation.
6. Complete a short interaction.
7. Open the report page and walk through transcript evidence, score, examples, and improvement guidance.
8. Explain how the backend stores the session and how evaluator agents produce feedback.

## Known Trade-Offs

- The MVP emphasizes simulation and evaluation quality over broad LMS administration.
- Realtime voice/video uses LiveKit Cloud rather than building custom media infrastructure.
- Chat responses are returned from the backend as complete messages, while the frontend renders a type-on streaming effect for UX polish.
- Some analytics and instructor surfaces still use sample data and should be wired fully before a large production rollout.
- Full observability can be improved with model latency, token usage, evaluator quality metrics, traces, and alerting.

## What Makes Squinia Different

Squinia is not a generic AI chatbot. It is a structured professional practice environment:

- Organizations define the scenario and evaluation expectations.
- Personas make practice feel realistic and reusable.
- Transcripts make feedback auditable.
- Evaluation agents tie feedback to exact learner behavior.
- Learners leave with a clear view of what to repeat, what to change, and how to improve.
