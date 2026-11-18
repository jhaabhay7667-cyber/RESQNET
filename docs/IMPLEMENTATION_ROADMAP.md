# RESQNET Implementation Roadmap

This is a proposed, dependency-aware sequence based on the Phase 0 audit. **Only Phase 0 has been performed. Later phases are not started and require user approval.** The system must remain clearly labeled as a simulation until real integrations are authorized, configured, and validated.

## Phase 0 — Audit and stabilization (current)

**Status: Complete for the scoped local audit.**

- Inventory existing routes, models, algorithms, configuration, and tests.
- Fix invalid serialization of existing seeded `.local` email addresses.
- Prevent public self-registration as Administrator.
- Align the priority queue test expectation with the implemented bounded-aging behavior.
- Verify frontend build/test/lint, backend tests, API health, and Vite proxy.
- Create the six requested audit documents.

**Remaining before production:** role-onboarding policy, registration verification, migrations, production secrets/configuration, deployment operations, and independent security/privacy review remain open; passing local tests does not establish operational readiness.

## Phase 1 — Approve requirements and build production foundations

Start only after approval of the Phase 0 documents.

1. Select one pilot location and define the authorized operator organization, service-level expectations, and emergency escalation workflow.
2. Confirm privacy, consent, retention, incident access, and operational policies with the responsible organization.
3. Add Alembic configuration and reversible migrations; define backup/restore and safe deployment procedures.
4. Make production startup fail closed unless a strong secret, production database, safe CORS origins, and disabled demo seeding are explicitly configured.
5. Replace public role selection for operator roles with approved invitations/verification and organization scoping.
6. Add audit logging, structured logs, health/readiness checks, rate-limiter storage suitable for multiple instances, and automated CI.
7. Re-run the regression suite and perform a deployment smoke test before any data migration.

## Phase 2 — Partner-backed emergency workflow

- Integrate only the dispatch interfaces authorized by the selected emergency-response partner.
- Define acknowledgement, escalation, cancellation, retry, timeout, and failure behavior with the partner.
- Keep human dispatcher approval and transactionally safe ambulance assignment.
- Deliver explicit “request received by RESQNET” vs “accepted by partner” states; never report dispatch as successful without a verified acknowledgement.
- Conduct tabletop and controlled end-to-end testing with the partner before enabling public use.

## Phase 3 — Real data sources and live operations

- Integrate participating hospital resource feeds and establish freshness/ownership rules.
- Integrate authorized vehicle telemetry and consent/retention controls; distinguish operator-submitted from device-reported data.
- Select a routing/traffic provider or validate a maintained road graph, then test coverage and failure fallback.
- Use a shared event broker for multi-instance WebSocket delivery; add reconnect, replay/freshness, and authorization tests.
- Add approved notification providers only after credentials, consent, delivery, and failover are agreed.

## Phase 4 — Safety and user experience

- Implement low-bandwidth mobile SOS, accessible controls, explicit location consent, local emergency contact actions, and tested cancellation semantics.
- Add verified Hindi/Bengali content and human-reviewed AI suggestions only if configured.
- Add incident notes/uploads only with access control, encryption, malware checks, retention, and audit history.
- Add disaster, blood-bank, and volunteer modules as independently reviewed products; do not expose personal data without consent and verified operating workflows.

## Phase 5 — Research and analytics

- Define provenance, anonymization, retention, and reproducibility for all metrics.
- Correctly define response time (for example, report received to responder arrival) and record timestamp provenance.
- Add export/reporting only after privacy review and authorization.
- Separate simulated benchmark datasets from operational data.

## Phase 6 — Release readiness

- Complete threat modeling, privacy/security review, accessibility/responsive testing, concurrency and failure testing, backup restore test, and partner sign-off.
- Configure PostgreSQL, TLS, secret storage, deployment, monitoring/alerts, incident response, and disaster recovery.
- Verify all integration paths with test credentials/test endpoints and a controlled partner exercise.
- Publish limitations, support contacts, data policy, and operating procedures.

## Approval gate

Do not begin Phase 1 until the user reviews and approves [PROJECT_AUDIT.md](./PROJECT_AUDIT.md), [FEATURE_INVENTORY.md](./FEATURE_INVENTORY.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [API_REFERENCE.md](./API_REFERENCE.md), and [TEST_REPORT.md](./TEST_REPORT.md).
