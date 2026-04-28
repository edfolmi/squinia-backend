# Squinia Architecture

This document explains the technical architecture behind Squinia: the product boundary, system components, AI control flow, data model, deployment shape, and key trade-offs.

## Design Goals

Squinia is designed around five goals:

1. **Realistic practice:** learners should feel they are speaking to a real stakeholder, interviewer, manager, or customer.
2. **Organization control:** bootcamps and organizations should define scenarios, personas, rubrics, and expectations.
3. **Auditable feedback:** evaluations should reference the learner's actual transcript, not generic advice.
4. **Multimodal delivery:** the same scenario model should support chat, phone, and video simulation modes.
5. **Production path:** the system should run as a real multi-tenant web application with deployable frontend/backend services.

## High-Level Architecture

```text
                                     +----------------------+
                                     |  OpenRouter / OpenAI |
                                     |  chat, guard, eval   |
                                     +----------+-----------+
                                                |
                                                |
+-------------------------+        +------------v------------+        +-------------------+
| Next.js Frontend        |        | FastAPI Backend         |        | PostgreSQL        |
| Vercel                  +------->| AWS ECS + Load Balancer +------->| app data          |
| learner/org experience  |        | API + AI services       |        | sessions/evals    |
+-----------+-------------+        +------------+------------+        +-------------------+
            |                                   |
            |                                   |
            |                         +---------v---------+
            |                         | Redis-compatible  |
            |                         | cache             |
            |                         +-------------------+
            |
            |                         +-------------------+
            +------------------------>| LiveKit Cloud     |
                                      | voice/video rooms |
                                      +---------+---------+
                                                |
                                      +---------v---------+
                                      | Integrated agent  |
                                      | STT/LLM/TTS       |
                                      +-------------------+
```

## Frontend

The frontend is a Next.js application deployed on Vercel.

Primary responsibilities:

- Authentication and onboarding screens
- Learner scenario list and simulation launch flow
- Organization scenario, rubric, cohort, assignment, and persona management
- Chat simulation UI
- Phone and video simulation UI
- Report page with transcript, recording, score, examples, and improvements
- Client-side recording persistence for local playback

Important frontend design decisions:

- Phone/video use LiveKit for realtime media rather than custom WebRTC.
- Chat uses backend HTTP calls and renders a frontend-only type-on stream effect for a smoother UX.
- Scenario list and simulation screens surface persona avatar, name, and title so the learner knows who they are about to meet.
- Report pages prefer backend evaluation data and never show demo scorecards as real evaluation for persisted backend sessions.

## Backend

The backend is a FastAPI application deployed to AWS ECS behind an Application Load Balancer.

Primary responsibilities:

- Tenant, user, membership, and auth flows
- Scenario, rubric, cohort, assignment, and persona persistence
- Session lifecycle: start, live token, transcript ingest, end, abandon
- Text simulation chat completion
- Chat guardrail checks
- LiveKit room and participant token minting
- LiveKit agent dispatch
- Evaluation job orchestration and persistence
- Health checks and structured logging

Key service boundaries:

```text
API endpoints
  -> service layer
    -> repositories
      -> SQLAlchemy models

AI endpoints/jobs
  -> scenario prompt builder
  -> provider client
  -> parser/reviewer
  -> evaluation repository
```

## Core Domain Model

The important entities are:

- **Tenant:** organization boundary.
- **User:** learner, instructor, admin, or owner.
- **Cohort:** group of learners.
- **Scenario:** practice situation configured by an organization.
- **Agent Persona:** reusable AI character with avatar, name, title, gender, voice settings, personality, communication style, and background.
- **Rubric Item:** scoring dimension for a scenario.
- **Simulation Session:** one learner attempt.
- **Message:** transcript turn for chat/voice/video.
- **Evaluation:** overall result for a session.
- **Evaluation Score:** rubric-level score, rationale, summary, transcript example, and improvement guidance.

The session stores a snapshot of the scenario at start time. This is important because later edits to a scenario should not change the historical record of what the learner experienced.

## Simulation Flow

### 1. Scenario Setup

An organization creates:

- scenario title and description
- target role and difficulty
- expected learner behavior
- opening message
- feedback guidance
- rubric criteria
- optional reusable persona

The persona can include a configured voice provider and voice id. If no exact voice is selected, the voice worker falls back to gender-aware defaults.

### 2. Session Start

The learner starts a session:

```text
POST /api/v1/sessions
```

The backend validates access, loads the scenario and persona, freezes the scenario snapshot, and creates a session row.

### 3. Chat Simulation

Chat simulations run through HTTP request/response turns.

```text
Learner input
  -> OpenRouter LlamaGuard classification
  -> scenario prompt + transcript history
  -> OpenRouter chat model
  -> assistant reply persisted
  -> frontend type-on stream effect
```

The guardrail step blocks prompt injection, jailbreak attempts, instruction override attempts, and system prompt extraction requests before they reach the scenario agent.

Configurable models:

- `OPENROUTER_CHAT_MODEL`
- `OPENROUTER_GUARD_MODEL`

### 4. Phone and Video Simulation

Phone and video simulations use LiveKit Cloud.

```text
Frontend requests LiveKit token
  -> backend creates/ensures room
  -> backend dispatches agent
  -> browser joins LiveKit room
  -> integrated LiveKit worker joins as persona agent
  -> finalized transcript segments are ingested into backend
```

The LiveKit worker uses:

- Deepgram and OpenAI fallback STT
- Groq and OpenAI fallback LLM
- Deepgram, Cartesia, and OpenAI fallback TTS
- persona gender and voice id metadata for voice selection

Turn detection is optional because LiveKit's local model assets must be downloaded. If those assets are unavailable, the worker disables turn detection gracefully rather than crashing the simulation.

### 5. Evaluation

When a session ends, the backend creates or reuses an evaluation row and runs an evaluation job.

```text
Session transcript
  -> rubric/scenario/persona context
  -> scoring model
  -> evidence extraction
  -> review model
  -> persisted Evaluation + EvaluationScore rows
  -> frontend report page
```

The evaluator is expected to produce:

- overall score
- feedback summary
- rubric-level scores
- rationale
- exact learner quote where possible
- improvement guidance

The frontend report page uses backend evaluation data when available. If evaluation is still processing, it shows a pending state instead of demo feedback.

## Prompting Strategy

Squinia uses prompt separation:

- **Scenario prompt:** defines role, setting, learner objective, persona behavior, opening line, and constraints.
- **Guard prompt:** classifies learner input for jailbreak and prompt-injection risk.
- **Evaluation prompt:** scores the transcript against rubric items and scenario expectations.
- **Review prompt:** checks evaluator quality and improves consistency.

Prompt trade-offs:

- The scenario prompt must keep the agent natural, not overly scripted.
- Evaluation prompts must be structured enough to persist reliably.
- Guard prompts must block instruction attacks without blocking normal learner mistakes.
- The platform stores scenario snapshots so prompts are reproducible for completed sessions.

## Model and Provider Strategy

Squinia supports provider fallbacks to reduce brittleness:

- Chat and guardrail models run through OpenRouter.
- Evaluation can use multiple configured OpenAI/OpenRouter-compatible models.
- Voice STT/TTS uses provider fallbacks.
- Persona voice can be exact (`voice_id`) or inferred from gender defaults.

This gives the product flexibility while keeping the application code organized around a stable internal domain model.

## Deployment Architecture

Current deployment:

- Frontend: Vercel at https://squinia-frontend.vercel.app/
- Backend: AWS ECS
- Ingress: AWS Application Load Balancer
- Database: PostgreSQL
- Cache: Redis-compatible service
- Realtime: LiveKit Cloud
- AI providers: OpenRouter/OpenAI, Deepgram, Cartesia, Groq

Backend deployment assets include:

- Dockerfile
- AWS deployment guide
- Terraform infrastructure
- GitHub Actions workflow for ECS deployment

## Error Handling and Resilience

Implemented resilience patterns:

- Structured `AppError` responses for API failures
- Structured backend logging
- OpenRouter guard failure handling
- LiveKit worker process manager and `/health` status
- Redis failure does not prevent app boot
- Evaluation status endpoint supports pending/processing states
- Voice provider fallbacks
- Chat model configuration via environment variables
- LiveKit turn detector disabled gracefully when local model files are missing

Areas to improve:

- Add model-call latency and token usage logs.
- Add tracing across session start, transcript ingest, evaluation job, and report fetch.
- Add alerts for failed evaluations and LiveKit worker crashes.
- Add a dashboard for evaluation latency, completion rate, and blocked prompt-injection attempts.

## Testing Strategy

Existing focused backend tests cover:

- auth service behavior
- session transcript ingestion
- agent persona prompt metadata
- LiveKit voice selection
- text chat guardrail classification

Existing frontend testing is lighter and should be expanded.

Recommended next tests:

- scenario card persona rendering
- chat frontend type-on stream behavior
- report page backend evaluation rendering
- expired-auth redirect flow
- session lifecycle integration test from start to evaluation
- model-output parser tests with malformed output

## Security Considerations

Important controls:

- tenant-scoped data access
- JWT-based authentication
- rate limiting middleware
- prompt-injection guard for text chat
- no frontend access to provider API keys
- backend-only LiveKit token minting
- Secrets Manager for production backend secrets

Important remaining hardening:

- confirm all `.env`, Terraform state, and `terraform.tfvars` files are ignored and never committed
- add CI secret scanning
- add production security headers on frontend
- add stricter CORS values for production domains
- add audit logs for admin actions such as persona, scenario, and assignment changes

## Known Trade-Offs

- The MVP uses third-party realtime media through LiveKit instead of owning WebRTC infrastructure.
- Frontend chat streaming is a UX effect, not backend token streaming. This keeps backend chat simple and easier to guard.
- Some analytics and instructor views still use sample data and should be wired fully before broad launch.
- Evaluation is asynchronous, so report pages need a pending state.
- Optional LiveKit turn detection requires local model assets; the worker can run without it.

## Peer Review Talking Points

If asked to explain technical depth, focus on:

- multi-tenant training workflow
- scenario snapshots for reproducible AI behavior
- reusable persona system
- guardrail-before-agent control flow
- LiveKit integration for voice/video
- transcript-driven evaluation
- rubric-level feedback with exact learner examples

If asked about what remains, be direct:

- improve frontend test coverage
- replace remaining sample analytics data
- add model observability and alerts
- expand CI/CD coverage
- tighten production security and audit logging
