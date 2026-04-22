# Dashboard wire-up (frontend ↔ backend)

Auth and onboarding already call the API. Org and learner dashboards can move off mocks using existing v1 routes listed in OpenAPI.

## `GET /api/v1/auth/me` (shell + routing)

Returns the standard envelope with `data` containing:

- **`user`** — same core fields as before, plus **`onboarding`** (object) and **`onboarding_completed_at`** (ISO string or null).
- **`memberships`** — active org rows, each with `tenant_id`, `tenant_name`, `tenant_slug`, `org_role`, `joined_at` (ordered like the default-tenant JWT rule).
- **`default_tenant_id`** / **`default_org_role`** — from the first membership (matches access-token default tenant embedding).

Use this (not JWT parsing alone) to choose learner vs org shell routes.

## `GET /api/v1/tenants/{tenant_id}`

Minimal tenant read (`id`, `name`, `slug`, `plan`, `is_active`) when the user has an active membership in that tenant. Use for org display name in the shell if needed.

## `POST /api/v1/auth/invites`

Mint a membership invite for the **JWT `tenant_id`** context. Caller must be **ORG_OWNER** or **ORG_ADMIN**.

Body: `email`, optional `role` (`STUDENT` default; may be `INSTRUCTOR`), optional `expires_in_days` (default 14).

Response includes **`token`**, **`invite_url`**, and metadata. Email is sent when `EMAIL_PROVIDER` is configured.

## Simulation sessions

`POST /api/v1/sessions` accepts **`SimulationSessionStartRequest`**: `scenario_id` (required), optional `cohort_id`, optional `mode` (default `TEXT`). `tenant_id` comes from the token, not the body. Prefer creating the session on the server before opening the sim UI.
