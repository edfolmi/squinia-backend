# CLAUDE.md / AGENT.md

## Squinia — Engineering Execution Guide

---

# 1. ENGINEERING PRINCIPLES

### 1.1 Build Philosophy

* Build **feature-by-feature (vertical slices)**, not layers in isolation
* Every feature must be **usable end-to-end** before moving on
* Prioritize **working systems over theoretical completeness**

### 1.2 Modularity Rules

* Max file size: **~600 lines** (hard limit unless justified)
* Prefer **many small modules** over few large ones
* Enforce **clear boundaries** between:

  * API layer
  * Business logic (services)
  * Domain models
  * Infrastructure (DB, queues, AI providers)

### 1.3 Design Principles

* Prefer **composition over inheritance**
* Avoid **global state and hidden dependencies**
* Every module must have **one clear responsibility**
* All logic must be **testable in isolation**

### 1.4 System Thinking

* Design for:

  * **Scalability (multi-tenant, async workloads)**
  * **Observability (logs, metrics)**
  * **Replaceability (LLM providers, STT/TTS engines)**

---

# 2. PROJECT STRUCTURE (SOURCE OF TRUTH)

## 2.1 Backend (FastAPI)

```
backend/
│
├── app/
│   ├── api/                  # HTTP layer (routes/controllers)
│   ├── core/                 # config, settings, security
│   ├── domain/               # business entities (pure logic)
│   ├── services/             # use-cases (orchestrates domain)
│   ├── agents/               # AI agents (simulation, evaluation)
│   ├── prompts/              # versioned prompt templates
│   ├── memory/               # user/session memory logic
│   ├── simulations/          # simulation engine
│   ├── evaluations/          # scoring + feedback engine
│   ├── assignments/          # tasks, quizzes, workflows
│   ├── db/                   # ORM models + repositories
│   ├── schemas/              # request/response schemas
│   ├── workers/              # async jobs (Celery/queues)
│   ├── realtime/             # WebSocket handlers
│   └── utils/                # helpers (strictly generic)
│
├── tests/
├── scripts/
└── main.py
```

### Rules

* `api/` NEVER contains business logic
* `services/` orchestrates everything
* `domain/` contains pure logic only (no DB/HTTP)
* `agents/` are isolated, pluggable AI modules

---

## 2.2 Frontend (Next.js / React)

```
frontend/
│
├── app/                     # Next.js app router
├── components/              # reusable UI components
├── features/                # feature-based modules
│   ├── simulation/
│   ├── evaluation/
│   ├── dashboard/
│   └── assignments/
│
├── hooks/                   # custom React hooks
├── services/                # API client layer
├── state/                   # global state (Zustand/Redux)
├── styles/                  # design system
├── lib/                     # utilities
└── types/
```

### Rules

* Use **feature-based structure**, not type-based chaos
* UI components must be **dumb/presentational where possible**
* Business logic lives in **hooks/services**, not components

---

## 2.3 AI Layer (Critical)

```
agents/
│
├── simulation/
├── evaluation/
├── orchestration/
└── base/
```

```
prompts/
│
├── simulation/
├── evaluation/
└── versions/
```

### Rules

* Prompts are **NOT embedded in code**
* Every prompt must be:

  * Versioned
  * Reusable
  * Testable

---

# 3. DEVELOPMENT WORKFLOW

### 3.1 Golden Rule

> Build ONE feature completely before starting another.

### 3.2 Feature Definition

Each feature must include:

* Backend logic (service + domain)
* API endpoint
* Frontend UI
* Working flow (user → system → result)

### 3.3 Execution Steps

1. Define feature scope (strictly minimal)
2. Build backend (domain → service → API)
3. Connect frontend UI
4. Validate full flow
5. Commit

### 3.4 Definition of Done

A feature is complete only if:

* Fully functional end-to-end
* No broken flows
* No placeholder logic (unless explicitly allowed)
* Can be demoed

---

# 4. FEATURE DEVELOPMENT RULES

* NEVER build multiple features in parallel
* ALWAYS connect:

  ```
  UI → API → Service → Domain → Response
  ```
* Avoid mock logic unless:

  * External dependency unavailable
* Replace mocks immediately after validation

---

# 5. CODE QUALITY STANDARDS

### 5.1 File Rules

* Max ~600 lines
* Split aggressively when approaching limit

### 5.2 Function Rules

* Max ~50 lines per function
* Must do ONE thing

### 5.3 Naming

* Use explicit names:

  * `simulateInterviewSession()`
  * NOT `processData()`

### 5.4 Structure

* Avoid deep nesting (>3 levels)
* Use early returns
* Use clear typing (Pydantic / TypeScript)

---

# 6. AI AGENT ARCHITECTURE RULES

### 6.1 Agent Design

Each agent must be:

* Stateless (except injected memory)
* Config-driven
* Replaceable

### 6.2 Types of Agents

* Simulation Agent (conversation)
* Evaluation Agent (scoring)
* Orchestrator Agent (multi-agent routing)

### 6.3 Prompt Rules

* Stored in `/prompts`
* Versioned (`v1`, `v2`, etc.)
* No inline prompt strings in services

### 6.4 Memory Rules

* Session memory (short-term)
* User memory (long-term)
* Must be injectable, not global

### 6.5 LLM Abstraction

* Never tie logic to one provider
* Use adapter pattern:

  ```
  OpenAIAdapter
  GroqAdapter
  LocalLLMAdapter
  ```

---

# 7. UI/UX DESIGN SYSTEM (CRITICAL)

### 7.1 Design Philosophy

* Calm, premium, human-centered
* Avoid “AI gimmick UI”
* No neon gradients, no sci-fi aesthetics

### 7.2 Visual Style

* Colors:

  * Soft blues
  * Neutral grays
  * Subtle accent color
* Typography:

  * Clear hierarchy (Heading → Subheading → Body)
* Spacing:

  * Generous whitespace

### 7.3 Layout Principles

* Dashboard-first design
* Clear visual hierarchy
* Minimal cognitive load

### 7.4 Components

* Reusable
* Consistent spacing & sizing
* No ad-hoc styling

### 7.5 Interaction Philosophy

* Fast feedback (no laggy UI)
* Subtle animations only
* Focus on clarity over flashiness

---

# 8. STATE MANAGEMENT & DATA FLOW

### 8.1 Frontend State

* Use **Zustand or Redux Toolkit**
* Separate:

  * UI state
  * Server state

### 8.2 API Communication

* Centralized API layer (`services/`)
* No direct fetch calls inside components

### 8.3 Real-Time

* WebSockets for:

  * Live simulations
  * Streaming responses
* Fallback to polling if needed

---

# 9. TESTING & VALIDATION

### 9.1 Minimum Requirements

Each feature must:

* Work end-to-end
* Handle basic edge cases

### 9.2 Backend

* Unit tests for services
* Integration tests for APIs

### 9.3 Frontend

* Component sanity checks
* Basic interaction tests

---

# 10. COMMIT STRATEGY

### 10.1 Rules

* One feature = one commit (or small set)
* No partial commits

### 10.2 Format

```
feat(simulation): add basic chat-based interview flow

- backend simulation service
- API endpoint
- frontend chat UI
- end-to-end working flow
```

### 10.3 Requirements

* Must be runnable after each commit
* No broken builds

---

# 11. WHAT TO AVOID (ANTI-PATTERNS)

### Absolute NOs:

* Giant monolithic files
* Mixing UI + business logic
* Hardcoding prompts inside services
* Tight coupling between modules
* Premature optimization
* Building features ahead of need

### Common Failures:

* “Let’s just add this quickly” → leads to tech debt
* Skipping end-to-end validation
* Over-engineering early stages

---

# 12. EXECUTION MINDSET

* Build like a **production system from Day 1**

* Every line of code should be:

  * Maintainable
  * Replaceable
  * Scalable

* Think in systems, not scripts

* Optimize for:

  * Speed of iteration
  * Long-term clarity

---

# FINAL DIRECTIVE

This codebase must evolve into a **category-defining AI platform**, not a prototype.

Every decision must pass this test:

> “Will this scale to 100,000+ users and a multi-team engineering org?”

If not — redesign it.

---
