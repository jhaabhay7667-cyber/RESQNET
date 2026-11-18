# RESQNET API Reference

**Base path:** `/api/v1`  
**Authentication:** `Authorization: Bearer <access-token>` unless marked public.  
**Interactive docs:** FastAPI serves `/docs`, `/openapi.json`, and `/redoc` when the backend is running.

This is an inventory of implemented routes, not a production service-level guarantee. Most data is synthetic/local. Public SOS does not notify an emergency organization.

## Health

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/health` | Public | Returns API status/environment. |
| GET | `/api/v1/health/ready` | Public | Executes a DB `SELECT 1`; returns readiness/database status. |
| GET | `/api/health` | Public, legacy | Compatibility health endpoint outside version prefix. |

## Authentication and users

| Method | Path | Access | Behavior |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public | Creates an account and token pair. Public roles: Emergency Dispatcher, Field Operator, Hospital Operator. Administrator is not a public role. |
| POST | `/api/v1/auth/login` | Public | Verifies username/password and returns token pair/user. |
| POST | `/api/v1/auth/refresh` | Refresh token | Rotates a persisted refresh token. |
| POST | `/api/v1/auth/logout` | Authenticated | Revokes the submitted refresh token. |
| GET | `/api/v1/auth/me` | Authenticated | Returns current user. |
| GET | `/api/v1/auth/users` | Administrator | Lists users. |
| PATCH | `/api/v1/auth/users/{user_id}/active?is_active=true` | Administrator | Enables/disables a user. |

## Emergencies and public SOS

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/emergencies` | Authenticated | Lists emergency rows ordered by calculated priority. |
| POST | `/api/v1/emergencies` | Administrator, Emergency Dispatcher | Creates a local emergency and event record. |
| PATCH | `/api/v1/emergencies/{emergency_id}` | Administrator, Emergency Dispatcher | Changes status with assignment/status constraints. |
| POST | `/api/v1/public/sos` | Public; process-local IP limit | Creates a `Pending Approval` simulated request and cancellation token. No SMS, phone call, or dispatch integration. |
| GET | `/api/v1/public/sos/{emergency_id}` | Public | Returns limited status/location information by ID. |
| POST | `/api/v1/public/sos/{emergency_id}/cancel` | Public cancellation token | Cancels a still-open SOS with its one-time token. |

## Ambulances and hospitals

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/ambulances` | Authenticated | Lists local fleet records. |
| POST | `/api/v1/ambulances` | Administrator, Emergency Dispatcher | Creates a fleet record. |
| PATCH | `/api/v1/ambulances/{ambulance_id}` | Administrator, Emergency Dispatcher | Updates the full ambulance input model. |
| PATCH | `/api/v1/ambulances/{ambulance_id}/location` | Administrator/dispatcher, or assigned Field Operator | Saves an operator-triggered location update; record is marked simulated. |
| GET | `/api/v1/hospitals` | Authenticated | Lists local hospital records. |
| POST | `/api/v1/hospitals` | Administrator, Emergency Dispatcher | Creates a hospital record. |
| PATCH | `/api/v1/hospitals/{hospital_id}/resources` | Administrator/dispatcher, or assigned Hospital Operator | Updates available beds and acceptance flag; also updates the `beds` resource record. |
| GET | `/api/v1/hospitals/recommend?latitude={lat}&longitude={lon}` | Authenticated | Recommends accepting hospitals with beds using the local road graph. |

## Dispatch, routing, and algorithms

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/dispatch` | Administrator, Emergency Dispatcher, Field Operator | Lists local dispatch records. |
| GET | `/api/v1/dispatch/recommend/{emergency_id}` | Administrator, Emergency Dispatcher | Returns a local vehicle recommendation. |
| POST | `/api/v1/dispatch/{emergency_id}/approve` | Administrator, Emergency Dispatcher | Creates a local dispatch after approval; no external ambulance is contacted. |
| GET | `/api/v1/routing/roads` | Authenticated | Lists graph roads. |
| POST | `/api/v1/routing/route` | Authenticated operator role | Runs Dijkstra/A* on the configured local graph; optional blocked roads apply to that request. |
| POST | `/api/v1/dsa/run` | Authenticated operator role | Runs Dijkstra/A*/BFS/DFS and stores trace/measurements. |
| POST | `/api/v1/dsa/benchmark` | Authenticated operator role | Runs Dijkstra and A* locally and stores results. |
| GET | `/api/v1/dsa/runs` | Administrator, Emergency Dispatcher | Lists recent runs. |

## Analytics, notifications, assistant, realtime

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/v1/analytics/dashboard` | Authenticated | Returns dashboard aggregates. |
| GET | `/api/v1/analytics` | Authenticated | Returns daily/weekly/monthly/category/hotspot/utilization aggregates. |
| GET | `/api/v1/analytics/events` | Administrator, Emergency Dispatcher | Lists recent emergency events. |
| GET | `/api/v1/notifications` | Authenticated | Lists global (`user_id` null) and user notifications. |
| PATCH | `/api/v1/notifications/{notification_id}/read` | Authenticated | Marks a visible notification read. |
| POST | `/api/v1/assistant/suggest` | Administrator, Emergency Dispatcher | Calls configured AI endpoint; returns 503 when provider URL/key are absent. Provider response is not normalized. |
| WebSocket | `/api/v1/ws/updates?token={access-token}` | Access token | Authenticates then sends process-local broadcasts. Query-string tokens and single-process fan-out require production redesign. |

## Implementation notes

- Request/response schemas are in `backend/app/schemas.py`; router code is in `backend/app/api/`.
- Typical validation errors are 422, missing resources 404, permission failures 401/403, and conflicts 409.
- Routing and travel-time estimates are based on synthetic graph weights and a fixed multiplier, not live road traffic.
- Rate limiting and WebSocket fan-out are process-local.
- The current API is not an official emergency-services interface.
