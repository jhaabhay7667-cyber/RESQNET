# RESQNET Project Audit

**Audit date:** 2026-11-18  
**Scope:** Existing frontend, backend, data model, algorithms, tests, configuration, and local runtime. This is Phase 0 only.

## Executive summary

RESQNET is a working local simulation application, not an operational emergency-response service. It has a React/Vite frontend, a FastAPI API, SQLAlchemy models, a SQLite development database, graph algorithms, and a small set of frontend/backend tests. The UI and backend explicitly label seed data and public SOS as simulated. The OpenStreetMap tile layer is real, but the displayed fleet, hospitals, incident locations, and road graph are synthetic New York data.

**Not ready for real-world emergency use or production deployment.** There is no authorized dispatch partner, verified hospital data feed, live fleet tracking provider, external notification service, production database migration history, or deployment configuration.

## Repository inventory

- `frontend/`: React 19, TypeScript, Vite, Tailwind CSS, React Router, React Leaflet, Recharts, Framer Motion, Lucide React, one Vitest UI test.
- `backend/`: FastAPI, SQLAlchemy 2, Pydantic 2, JWT, WebSockets, 12 ORM tables, two pytest modules, SQLite files, and a PostgreSQL driver.
- `docs/`: created by this Phase 0 audit.
- No repository-root README, Alembic configuration/migrations, Docker files, CI workflow, or production hosting configuration was present during inspection.
- The workspace does not appear to contain Git metadata, so a Git diff/status check was unavailable.

## Phase 0 findings and actions

| Finding | Evidence | Phase 0 outcome |
|---|---|---|
| Registration endpoint returned 404 in the browser when a stale process was serving `/api/auth/...` rather than `/api/v1/...`. | Vite proxy targets port 8000; the running API's OpenAPI document did not list the versioned routes. | Replaced the stale local API process with the current `backend/app/main.py`; `/api/v1/health` then returned 200 directly and through Vite. An empty registration body returned 422, confirming route matching and request validation. |
| Public registration could select the Administrator role. | `RegisterRequest` normalized admin aliases and the registration handler allowed all four roles. | Public registration now permits only Emergency Dispatcher, Field Operator, and Hospital Operator. A regression test verifies that the administrator role is rejected. |
| Demo logins failed because response validation rejected seeded `@resqnet.local` addresses. | `UserOut` used Pydantic `EmailStr` while seeded records use the reserved `.local` suffix. | `UserOut.email` is now a string; registration input still validates email addresses. Backend auth and API tests pass. |
| Priority queue test expectation contradicted its configured wait boost. | A priority-1 entry aged 100 seconds receives the full +5 boost and therefore outranks priority 5. | Updated the test to assert the implemented bounded-boost ordering. No queue algorithm behavior was changed. |

These are narrow stabilization corrections; no feature phase was started.

## Critical remaining blockers

1. **No production authorization or operating partner.** Public SOS only persists a request as `Pending Approval`; it does not contact an emergency service or dispatch organization.
2. **No production identity boundary.** Public account creation permits a user to self-assign dispatcher and field/hospital operator roles. Administrator signup is blocked, but production onboarding still needs invitation/verification controls and organization scoping.
3. **Seed configuration defaults are unsafe for production.** Schema auto-creation and synthetic seed data default to enabled. The example environment also enables seeding and includes a development JWT secret placeholder.
4. **No migrations.** Alembic is a dependency, but no Alembic configuration, environment, or versioned migration scripts were found. `create_all()` is not a safe schema upgrade strategy for an existing production database.
5. **No persistent / multi-worker realtime infrastructure.** WebSocket fan-out is in-process; events are not delivered across multiple API workers or retained as a message stream.
6. **No actual location/traffic/dispatch integrations.** Operator location is sent only on request and stored with `simulated=True`; the graph and resource inventory are seeded local data.
7. **No deployment hardening evidence.** There is no Docker Compose, production CORS configuration, TLS/secret deployment documentation, backup plan, monitoring, or verified cloud deployment.
8. **Privacy/compliance work remains.** No consent/retention policy, audit-log model, sensitive-data classification, data deletion process, or production threat review exists. Do not enter real patient information.

## Other notable issues

- Frontend access and refresh tokens are stored in `localStorage`.
- Public SOS request `contact` is accepted but not persisted in the `Emergency` model.
- Public SOS tracking is unauthenticated and exposes incident location/status by ID; cancellation requires a one-time token.
- The SOS rate limiter is process-local and IP-based; it is not shared across workers or instances.
- The websocket token is passed in the query string; connection fan-out is not role-filtered.
- Analytics are database-derived, but response-time metrics use dispatch creation-to-completion duration. That is not equivalent to call-received-to-arrival response time.
- Road routes and ETA use a synthetic graph and a fixed distance multiplier, not a live routing/traffic provider.
- Several frontend requests have error handling, but notifications are currently transient WebSocket messages rather than a fully integrated persistent inbox.

## Verification snapshot

- Backend: **20 passed**, one Starlette/httpx deprecation warning.
- Frontend: **1 test passed**.
- Frontend production build: passed; Vite reports a minified JavaScript chunk over 500 kB.
- Frontend lint: exited successfully with nine warnings.
- Runtime route check: API and Vite-proxied `/api/v1/health` returned 200; invalid empty registration request returned 422.

Detailed evidence and commands are in [TEST_REPORT.md](./TEST_REPORT.md). Endpoint inventory is in [API_REFERENCE.md](./API_REFERENCE.md). Proposed next steps are in [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md); work beyond Phase 0 is paused pending approval.
