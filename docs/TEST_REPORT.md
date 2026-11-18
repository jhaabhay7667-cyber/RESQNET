# RESQNET Phase 0 Test Report

**Run date:** 2026-11-18  
**Scope:** Existing tests/build/lint and local route/proxy checks. No external service or production deployment was tested.

## Results

| Check | Result | Notes |
|---|---|---|
| Backend pytest | **20 passed** | Ran `backend/tests` using `backend/.venv`; tests used an isolated temporary working directory because the API fixture drops/recreates `resqnet-test.db`. One Starlette/httpx TestClient deprecation warning. |
| Frontend Vitest | **1 passed** | One `PublicSosPage` two-step-confirmation test. |
| Frontend TypeScript + Vite build | **Passed** | Vite emitted a warning that the minified JS chunk is ~1,069 kB, above 500 kB. |
| Frontend Oxlint | **Passed with warnings** | Nine warnings: two `react/only-export-components`, seven `react/set-state-in-effect`. |
| Backend health route | **Passed** | `GET http://127.0.0.1:8000/api/v1/health` returned 200. |
| Vite API proxy | **Passed** | `GET http://127.0.0.1:5173/api/v1/health` returned 200 with backend status. |
| Registration route matching | **Passed** | Empty JSON sent to `POST /api/v1/auth/register` returned 422 validation, not 404. Registration using a supported role and an `example.com` email is covered by backend tests. |

## Stabilization before/after

Initial backend test run: **8 failed, 11 passed**.

- Seven API test failures traced to `UserOut.email` applying strict `EmailStr` validation to seeded `@resqnet.local` accounts.
- One priority-queue test failure expected a priority-1 item with a full +5 wait boost to remain behind a priority-5 item, contrary to the implementation's priority-plus-bounded-boost ordering.
- Public registration also accepted Administrator through the registration schema/handler; a regression test was added and the public-role allowlist was narrowed.

After the Phase 0 changes: **20 passed**. See [PROJECT_AUDIT.md](./PROJECT_AUDIT.md) for the corresponding findings.

## Commands executed

Frontend, from `C:\Users\jhaa1\OneDrive\Desktop\RESQNET\frontend`:

```powershell
npm run build
npm test
npm run lint
```

Backend tests were run from a unique temporary directory with `PYTHONPATH` set to the project backend, so the test fixture's relative `resqnet-test.db` was outside the workspace. The temporary directory was removed after the run. The test fixture itself calls `drop_all()` and should not be run against a valued database.

## Coverage gaps

- Only one frontend test exists; it does not verify actual registration/login UI against a running API, route guards, authorization UX, layouts, error states, or browser geolocation.
- Backend tests cover core demo auth, public SOS lifecycle, local dispatch, graph routing, operator resource permissions, and a WebSocket handshake. They do not prove concurrency behavior against PostgreSQL, multi-worker WebSockets, delivery integrations, production migrations, provider outages, or deployment.
- No Alembic migration checks, PostgreSQL integration tests, security scanner, accessibility suite, browser end-to-end suite, or deployment smoke test was found/run.
- Passing local tests do not establish that RESQNET can contact or coordinate with emergency services.
