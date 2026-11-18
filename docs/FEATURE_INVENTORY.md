# RESQNET Feature Inventory

**Status meanings:** **Implemented** means code exists, not that it is production-ready. **Verified** means a corresponding test or runtime check passed. **Incomplete** means only part of the stated workflow exists. **Absent** means no implementation was found.

## Frontend routes

Routes are declared in `frontend/src/App.tsx`; page implementations are primarily in `frontend/src/pages/Pages.tsx`.

| Route | Feature | Current status |
|---|---|---|
| `/` | Landing page | Implemented; clearly labels the platform as simulation-only. |
| `/login` | Login | Implemented; backend login is covered by API tests. |
| `/register` | Registration | Implemented; backend registration and role validation are covered by API tests. |
| `/sos` | Public SOS | Implemented for synthetic requests; browser geolocation is permission-based; no emergency service is contacted. |
| `/sos/track/:id` | SOS tracking/cancellation | Implemented for local records; manual refresh, not external responder tracking. |
| `/app/dashboard` | Command center | Implemented; metrics are loaded from the local database. |
| `/app/emergencies` | Emergency management | Implemented; list/create/status update and backend event history. |
| `/app/map` | Operations map | Implemented with React Leaflet and OpenStreetMap tiles; markers and road data are synthetic. Routing uses the local graph. |
| `/app/ambulances` | Fleet management | Implemented; local CRUD/status controls. |
| `/app/hospitals` | Hospital management | Implemented; local records and bed/ICU counts, not a verified live feed. |
| `/app/dispatch` | Dispatch center | Implemented; recommendation and authorized human approval in the local database. |
| `/app/analytics` | Analytics | Implemented for records in the local database; no export/report UI found. |
| `/app/dsa` | DSA laboratory | Implemented for backend Dijkstra/A*/BFS/DFS traces; not a free-form graph editor or heap/queue visualizer. |
| `/operator/ambulance` | Ambulance operator portal | Implemented; location sharing is user-initiated and stored as simulated. |
| `/operator/hospital` | Hospital operator portal | Implemented; local resource updates. |
| `/app/profile` | Profile | Read-only account details. |
| `/app/settings` | Settings | Theme and compact preference stored in browser local storage. |
| `*` | Not found | Implemented. |

The app shell includes navigation, search, responsive sidebar, transient notification display, user menu, and a WebSocket connection indicator. Route protection checks for any signed-in user; role-specific permissions are primarily enforced by the API, not by route guards.

## Backend capabilities

| Area | Current status | Evidence / limitation |
|---|---|---|
| Authentication | Implemented and tested | Password hashing, access/refresh JWTs, refresh rotation, logout, `/me`; no external identity provider. |
| Roles | Implemented with Phase 0 guard | API uses role dependencies. Public registration cannot create administrators after the Phase 0 fix, but it can self-assign other operator roles. |
| Emergency records | Implemented and tested | SQL-backed create/list/status and event history; records are synthetic/local. |
| Public SOS | Implemented and tested as a simulation | Validation, location, cancel-token hash, tracking/cancel, IP rate limit; no dispatch provider, SMS, or phone call. `contact` is not persisted. |
| Ambulances | Implemented and tested | CRUD, status, operator-reported location. Location records are marked simulated. |
| Hospitals | Implemented and tested | CRUD, bed/ICU fields, accepting status, graph-based recommendation; values are not live hospital inventory. |
| Dispatch | Implemented and tested | Recommendations, dispatcher approval, transaction attempt, unique active-vehicle index. No real fleet integration. |
| Routing | Implemented and tested | Dijkstra/A* over a local synthetic graph; constant distance-to-time multiplier; not live traffic routing. |
| Analytics | Implemented | Aggregates from database rows; response-time definition is dispatch creation-to-completion. |
| WebSockets | Implemented and tested for connection | Token-authenticated process-local broadcast; no cross-worker broker, durable event delivery, or role-filtered subscriptions. |
| AI assistant | Configurable interface exists | Returns 503 unless `AI_PROVIDER_URL` and `AI_API_KEY` are set; provider-specific response is passed through. No credentials/configuration are present. |
| DSA structures | Implemented and unit-tested | Graph algorithms, heap, emergency priority queue, trie, DSU, segment/Fenwick trees, LRU; API exposes graph algorithms, not all structures. |

## Data sources and simulation markers

- Seed data uses synthetic records and New York-area coordinates; demo vehicle, hospital, road, and incident records are not real.
- Default `DATABASE_URL` is a local SQLite file (`backend/resqnet.db`).
- OSM map tiles are fetched from the public tile endpoint, but they do not make incident, hospital, vehicle, or traffic data live.
- No externally sourced traffic, hospital bed availability, ambulance telemetry, SMS, email, push notification, or official alert feed was found.

## Not implemented

- Disaster registration/coordination, zones, shelters, rescue teams, relief camps, situation reports.
- Blood banks, inventory, donor consent/verification, volunteer registration/assignment.
- Voice reporting/navigation and verified Hindi/Bengali language workflows.
- Incident notes/attachments and file-upload validation pipeline.
- CSV/PDF export or reproducible research-experiment management.
- External notification delivery, official dispatch/112 integration, live hospital/ambulance integrations.
- Production migrations, infrastructure-as-code, deployment/operations runbooks, backups, monitoring, or CI.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for boundaries and [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for a proposed incremental sequence.
