# Squinia Backend

Squinia is an AI simulation platform for organisations, bootcamps, and training teams. It lets teams create realistic interview and workplace communication scenarios, invite learners, run chat/phone/video simulations, and generate evidence-based evaluations from the learner's actual transcript.

## Demo Walkthrough

[![Squinia platform walkthrough](docs/squinia-demo-thumbnail.png)](https://www.loom.com/share/70acd7b5b64044af948d4f1b6cf4be90)

Watch the demo walkthrough showing the platform flow and a live simulation practice session.

This repository contains the FastAPI backend.

- Live platform: https://squinia-frontend.vercel.app/
- Backend deployment: AWS ECS behind an application load balancer
- Frontend deployment: Vercel
- Frontend repository: `../squinia-frontend`

## Backend Responsibilities

- Authentication, session validation, and tenant-aware access control.
- Organisation, cohort, learner, assignment, scenario, rubric, and persona APIs.
- Reusable AI personas with avatar metadata, gender, title, traits, and voice preferences.
- Chat simulation orchestration, including prompt-injection and jailbreak screening.
- LiveKit token and dispatch support for phone/video simulations.
- Transcript ingestion and normalized conversation storage.
- Agentic evaluation generation with rubric-level feedback, exact learner examples, and improvement guidance.
- Production logging and structured error responses.

## Core AI Flows

### Simulation Agent

The simulation agent is instructed from the organisation's scenario, selected persona, learner role, success criteria, and optional feedback guidance. The agent starts the conversation in character, maintains the role-play, and closes naturally when the scenario is complete.

### Chat Guardrail

Chat simulation input passes through an OpenRouter-hosted LlamaGuard-style guard before the model response is generated. The goal is to reduce prompt injection, jailbreak attempts, and unsafe role-play breaks while preserving normal learner conversation.

### Voice And Video Agent

Phone and video simulations use LiveKit for real-time communication. The backend creates sessions and dispatches the configured LiveKit agent without changing recording behavior.

Voice selection is persona-aware:

- Female personas prefer female voices.
- Male personas prefer male voices.
- Provider fallback is supported across Deepgram, Cartesia, and OpenAI.

### Evaluation Agents

Completed transcripts are evaluated through an agentic pipeline. The evaluator:

- Scores each rubric criterion.
- Grounds "See example" in exact learner transcript quotes.
- Produces "Show improvement" guidance with concrete next-step phrasing.
- Summarizes strengths, weaknesses, and overall readiness.

## Tech Stack

- FastAPI
- SQLAlchemy async ORM
- Alembic migrations
- PostgreSQL
- Redis cache/session support
- LiveKit Agents
- OpenRouter-hosted LLMs
- OpenAI-compatible model calls
- Deepgram, Cartesia, Groq, and OpenAI provider fallbacks
- Pytest
- Docker and AWS ECS deployment assets

## Important Environment Variables

The exact production values should live in AWS Secrets Manager, ECS task definitions, or your deployment secret store. Do not commit `.env`, `.tfvars`, Terraform state, or provider credentials.

Common variables:

```bash
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
JWT_SECRET_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_CHAT_MODEL=...
OPENROUTER_GUARD_MODEL=...
OPENAI_API_KEY=...
OPENAI_EVALUATION_SCORING_MODEL=...
OPENAI_EVALUATION_EVIDENCE_MODEL=...
OPENAI_EVALUATION_REVIEW_MODEL=...
OPENAI_TRACING_ENABLED=true
OPENAI_TRACING_INCLUDE_SENSITIVE_DATA=false
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_AGENT_NAME=squinia-voice-agent
LIVEKIT_WORKER_PORT=0
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...
GROQ_API_KEY=...
```

`LIVEKIT_WORKER_PORT=0` is recommended for local development to avoid fixed-port conflicts when uvicorn reloads or a previous worker is still running.

## Local Development

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8888
```

Health check:

```text
http://127.0.0.1:8888/health
```

## Observability

- Health: `/health` is the load-balancer readiness signal.
- Logs: structured events cover auth, sessions, transcript ingestion, model calls, and evaluation jobs.
- Model calls: chat guard, chat response, and evaluation agents log model, provider, latency, status, and token counts when available.
- OpenAI tracing: enabled only for chat and evaluation model workflows. Sensitive model payloads stay off by default with `OPENAI_TRACING_INCLUDE_SENSITIVE_DATA=false`.
- LiveKit: call, room, participant, and agent telemetry remains in LiveKit Cloud; the backend does not duplicate that media-plane tracing.

## Tests

Run the full test suite:

```bash
uv run pytest -q
```

Focused tests that are especially useful for the recent AI and auth work:

```bash
uv run pytest tests/test_auth_service.py -q
uv run pytest tests/test_text_chat_guard.py -q
uv run pytest tests/test_livekit_voice_selection.py tests/test_agent_persona_prompting.py -q
uv run pytest tests/test_session_transcript_ingest.py -q
```

## Deployment

The backend is designed to run as a containerized FastAPI service on AWS ECS behind a load balancer.

Useful deployment files:

- `Dockerfile`
- `docs/DEPLOYMENT_AWS.md`
- `infra/terraform/`
- `.github/workflows/deploy-backend.yml`

Production deployment should include:

- ECS task definitions with environment-specific secrets.
- Load balancer health checks pointed at `/health`.
- Database migrations run before or during release.
- Separate production settings for CORS, cookies, tokens, and allowed origins.
- Cloud logs retained long enough for debugging and peer-review demonstration.

## Review Notes

The backend is intentionally split into API routes, services, repositories, models, schemas, AI services, and LiveKit agent code. That separation makes it easier to explain the capstone architecture and gives the project a credible path from prototype to production.

The most important remaining production upgrades are stronger end-to-end test automation, formal LLM evaluation baselines, richer observability for token usage and model latency, and deployment runbooks for incident response.
