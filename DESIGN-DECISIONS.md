# Squinia Infrastructure Design Decisions

## Goal

Deploy the Squinia production MVP quickly, safely, and cheaply.

The design favors:

- Simple operations
- Low monthly cost
- Fast CI/CD
- Secure secret handling
- Enough production safety for an MVP

## High-Level Architecture

```text
Vercel Frontend
  -> Cloudflare DNS
  -> AWS Application Load Balancer
  -> ECS Fargate Backend
  -> Lightsail PostgreSQL
  -> Upstash Redis
  -> LiveKit Cloud
  -> AI provider APIs
```

## AI Fairness: Session Scenario Snapshots

When a learner starts a simulation, the backend stores a copy of the scenario on the session.

Stored in the snapshot:

- Scenario title and description
- Agent role
- Learner role and scenario config
- Selected persona
- Persona voice metadata
- Rubric items and max scores

Why:

- Keeps the learner's experience tied to the exact scenario version they started
- Prevents admin edits from changing active sessions
- Makes evaluation fair and repeatable
- Preserves the prompt and rubric context used for scoring

Example:

```text
Admin edits scenario while learners are in progress
  -> Existing sessions keep their original snapshot
  -> Existing transcripts are scored against the original rubric
  -> New sessions use the updated scenario
```

Tradeoff:

- A fixed snapshot can become outdated if the admin fixes a mistake during an active session

Why we accept it:

- Fairness matters more than live mutation
- Learners should not be graded against a rubric they never experienced
- Historical reports need stable context

Implementation:

- `SessionService._snapshot_from_scenario(...)` builds the snapshot
- `scenario_snapshot` is stored on the session row
- Chat, LiveKit metadata, and evaluation use the session snapshot

## Phone/Video Simulation: LiveKit Agent Orchestration

Phone and video simulations use LiveKit Cloud for realtime media.

The backend does not run WebRTC itself.

Backend responsibilities:

- Create or reuse the LiveKit room
- Issue short-lived participant tokens
- Dispatch the configured LiveKit agent
- Pass scenario and persona metadata to the agent
- Ingest finalized transcript segments
- Close the room when the session ends

LiveKit agent responsibilities:

- Join the learner's room
- Speak first using the scenario opening
- Stay in character using the scenario prompt
- Listen and respond in realtime
- Use speech-to-text, LLM, and text-to-speech providers
- Fall back between providers when possible

Persona-aware voice design:

- Persona gender and voice metadata are sent to the agent
- Female personas prefer female voices
- Male personas prefer male voices
- A configured `voice_id` overrides the default voice
- Deepgram, Cartesia, and OpenAI are used as TTS fallback options

Why:

- Realtime voice/video is hard to operate reliably inside the API server
- LiveKit gives better WebRTC reliability than custom media handling
- The FastAPI backend stays focused on product state, auth, tokens, transcripts, and evaluation
- Voice/video sessions still use the same scenario snapshot as chat sessions
- Persona voice behavior makes simulations feel less generic

Example:

```text
Learner starts a video simulation
  -> Backend creates Squinia session
  -> Backend snapshots the scenario
  -> Backend dispatches LiveKit agent with scenario/persona metadata
  -> Learner joins LiveKit room
  -> Agent role-plays in realtime
  -> Transcript segments are saved for evaluation
```

Tradeoff:

- The system depends on LiveKit and external speech/model providers
- Local development needs more moving pieces than text chat

Why we accept it:

- Realistic practice needs realtime conversation, interruptions, and voice presence
- Managed media infrastructure is safer for an MVP than building WebRTC from scratch
- Provider fallback reduces the risk of one speech or model provider blocking the session

Implementation:

- `SessionService.issue_livekit_token(...)` creates room access and dispatches the agent
- `compact_scenario_metadata(...)` prepares scenario/persona metadata for LiveKit
- `livekit_voice_agent.py` runs the realtime simulation agent
- `SessionService.ingest_live_transcript(...)` persists final transcript segments

## Frontend: Vercel

We use Vercel for the Next.js frontend.

Why:

- Easy GitHub-based deployment
- Fast frontend hosting
- Built-in HTTPS
- Good preview deployment support
- No server management

## DNS: Cloudflare

We use Cloudflare for DNS.

Why:

- Domain is already managed there
- Easy CNAME records
- Works well with AWS ALB and Vercel
- Can add proxy/WAF features later

## Backend Runtime: ECS Fargate

We use AWS ECS Fargate for the FastAPI backend.

Why:

- Runs normal Docker containers
- No EC2 server management
- Supports long-running backend services
- Supports HTTP and WebSocket-compatible traffic
- Works well with background worker processes like the LiveKit agent

Why not Lambda:

- The backend is a long-running API service
- Voice/agent workloads are not a great fit for short-lived functions

Why not Kubernetes/EKS:

- Too much operational overhead for an MVP

Why not App Runner:

- ECS gives more control over networking, task roles, execution, and deployment behavior

## Containerization: Docker

The backend is packaged as a Docker image.

Why:

- Same runtime in CI and production
- Easy deployment to ECS
- Dependencies are locked with `uv.lock`
- Container runs as a non-root user

The app runs with:

```text
uvicorn app.main:app
```

Container port:

```text
8000
```

## Load Balancer: AWS ALB

We use an Application Load Balancer in front of ECS.

Why:

- Public entry point for the API
- Handles HTTPS
- Routes traffic to ECS tasks
- Supports WebSocket upgrades
- Provides health checks

Health check endpoint:

```text
/health
```

## HTTPS: ACM + ALB

We use AWS Certificate Manager for the API certificate.

Why:

- Required for browser calls from the HTTPS Vercel frontend
- Avoids mixed-content errors
- Keeps TLS termination managed by AWS

Production API format:

```text
https://api.squinia.com
```

## Database: Lightsail PostgreSQL

We use AWS Lightsail PostgreSQL for the MVP database.

Why:

- Cheaper and simpler than RDS
- Managed PostgreSQL
- Good enough for early production MVP
- Easy to connect from ECS using public endpoint + SSL

Current MVP tradeoff:

- Database is publicly accessible

Mitigation:

- Strong password
- SSL connection string
- Secrets stored in AWS Secrets Manager

Future improvement:

- Move to RDS in private subnets when scale/security needs grow

## Redis: Upstash

We use Upstash Redis.

Why:

- Already created
- Serverless/simple Redis
- No Redis server to manage
- Works well for cache and rate limiting

Connection should use TLS:

```text
rediss://...
```

## Voice and Realtime: LiveKit Cloud

We use LiveKit Cloud for realtime voice/video.

Why:

- Avoids running our own media server
- Better reliability for WebRTC
- Faster MVP delivery
- Backend can issue tokens and dispatch agents

The backend:

- Creates/uses LiveKit rooms
- Issues participant tokens
- Dispatches the configured voice agent
- Runs the integrated LiveKit worker inside ECS

## Secrets: AWS Secrets Manager

Secrets are stored in AWS Secrets Manager.

Why:

- Secrets are not hardcoded in code
- Secrets are not stored in Docker images
- Secrets are not stored in GitHub Actions logs
- ECS can inject them securely at runtime
- Values can be updated without rebuilding the image
- Access can be controlled with IAM

Examples:

```text
SECRET_KEY
DATABASE_URL
REDIS_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
OPENAI_API_KEY
DEEPGRAM_API_KEY
```

Terraform creates the secret placeholders.

The real values are added separately.

## CI/CD: GitHub Actions

GitHub Actions deploys the backend.

Flow:

```text
Push to main
  -> Build Docker image
  -> Push image to ECR
  -> Register ECS task definition
  -> Update ECS service
```

Why:

- Simple Git-based deploy flow
- No manual Docker push
- Repeatable production deployments
- Easy rollback path through ECS task definitions

## Container Registry: ECR

We use Amazon ECR for backend Docker images.

Why:

- Native AWS container registry
- ECS can pull from it directly
- Works cleanly with IAM
- Supports image scanning

## Logs: CloudWatch

Backend logs go to CloudWatch Logs.

Why:

- Central place for ECS logs
- Useful for startup failures
- Useful for LiveKit worker debugging
- Easy to inspect task restarts

Log group:

```text
/ecs/squinia-prod-backend
```

## Networking

Current MVP network:

- Public ALB
- Public ECS tasks
- Public Lightsail PostgreSQL
- Outbound internet access from ECS

Why:

- Simple
- Cheap
- No NAT gateway cost
- Fast to deploy

Security group rules:

- ALB accepts HTTP/HTTPS from the internet
- ECS accepts traffic only from the ALB
- ECS can make outbound calls to DB, Redis, LiveKit, and AI APIs

Future improvement:

- Private ECS subnets
- NAT gateway or VPC endpoints
- RDS in private subnets

## Infrastructure as Code: Terraform

We use Terraform for AWS infrastructure.

Why:

- Repeatable setup
- Easier to review infra changes
- Reduces manual console drift
- Can later create staging/dev environments from the same code

Terraform manages:

- ECR
- ECS
- ALB
- IAM
- CloudWatch Logs
- Lightsail PostgreSQL
- Security groups
- Secrets Manager placeholders

## Current Environment Strategy

Current setup:

```text
main branch -> production
```

Why:

- Fastest path for MVP submission
- Keeps deployment simple
- Reduces last-minute environment complexity

Planned later:

```text
develop branch -> staging
main branch -> production
```

## Future Improvements

Planned improvements:

- Add staging environment
- Add automated DB migrations in CI/CD
- Move PostgreSQL to RDS
- Put ECS and database in private subnets
- Add autoscaling
- Add CloudWatch alarms
- Add WAF or Cloudflare protection rules
- Add backup/restore runbook
- Add production deployment approvals

## Summary

This design is intentionally simple.

It gives Squinia:

- A working production backend
- HTTPS API access
- Secure secret handling
- CI/CD deployment
- Managed database
- Managed Redis
- Managed voice infrastructure

It avoids heavy infrastructure until the product needs it.
