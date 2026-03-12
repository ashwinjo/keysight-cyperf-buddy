---
phase: 07-frontend-l4-7-test-advisor-ui-tab-to-submit-test-scenarios-and-display-agent-recommendations
plan: 01
subsystem: ui
tags: [react, typescript, vite, nginx, proxy, react-query, axios]

# Dependency graph
requires:
  - phase: 06-agentic-l4-7-test-advisor
    provides: Agent service on port 8001 with POST /api/l47/recommend endpoint
provides:
  - Vite dev proxy routing /api/l47/* to port 8001 (no path stripping)
  - Nginx production proxy for /api/l47/ to agent container
  - TypeScript contract types L47ScenarioRequest, L47Recommendation, L47RecommendationResponse
  - useGetL47Recommendations mutation hook with 422 error normalization
affects:
  - 07-02 (UI component for L4-7 Test Advisor tab — consumes hook and types from this plan)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "More-specific proxy entry before generic catch-all (Vite proxy ordering, nginx location ordering)"
    - "Direct URL in hook (no API_BASE strip) for agent service to preserve /api/l47 prefix"
    - "Identical 422 error normalization pattern across all mutation hooks"

key-files:
  created: []
  modified:
    - frontend/vite.config.ts
    - nginx.conf
    - frontend/src/hooks/useAPI.ts

key-decisions:
  - "No rewrite on /api/l47 Vite proxy — agent expects full path /api/l47/recommend; stripping would 404"
  - "Hook uses '/api/l47/recommend' directly, not API_BASE constant — API_BASE would route to port 8000 (main backend)"
  - "proxy_pass http://agent:8001/api/l47/ with trailing slash on both sides in nginx — preserves path without stripping /api/l47 prefix"

patterns-established:
  - "Proxy ordering pattern: more-specific entries (e.g. /api/l47) must precede generic entries (/api) in both Vite and nginx"

requirements-completed:
  - L47-UI-01
  - L47-UI-02

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 7 Plan 01: L4-7 Test Advisor Proxy and API Hook Summary

**Vite dev proxy and nginx production config wired to route /api/l47/* to the Phase 6 agent service (port 8001), with TypeScript types and React Query mutation hook exported from useAPI.ts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T05:40:28Z
- **Completed:** 2026-03-12T05:41:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `/api/l47` proxy entry before `/api` in vite.config.ts — agent receives requests at port 8001 with path intact
- Added `location /api/l47/` block before `location /api/` in nginx.conf — production routing to `agent:8001` with path preserved
- Exported `L47ScenarioRequest`, `L47Recommendation`, `L47RecommendationResponse` TypeScript interfaces from useAPI.ts
- Exported `useGetL47Recommendations` mutation hook with same 422 error normalization pattern as AshRAI hook

## Task Commits

Each task was committed atomically:

1. **Task 1: Add /api/l47 proxy entries to vite.config.ts and nginx.conf** - `6e11cc8` (feat)
2. **Task 2: Add L47 types and useGetL47Recommendations hook to useAPI.ts** - `25afe9f` (feat)

## Files Created/Modified
- `frontend/vite.config.ts` - Added `/api/l47` proxy entry (port 8001, no rewrite) before `/api` entry
- `nginx.conf` - Added `location /api/l47/` block (proxies to `http://agent:8001/api/l47/`) before `location /api/`
- `frontend/src/hooks/useAPI.ts` - Added L47 interfaces and `useGetL47Recommendations` mutation hook

## Decisions Made
- No rewrite on Vite `/api/l47` proxy — agent's route is registered as `/api/l47/recommend`; stripping the prefix would yield `/l47/recommend` which does not exist
- Hook hardcodes `'/api/l47/recommend'` instead of using `${API_BASE}/l47/recommend` — `API_BASE = '/api'` routes through the rewriting proxy to port 8000, not the agent on port 8001
- nginx `proxy_pass http://agent:8001/api/l47/` with trailing slashes on both URI and target preserves the full `/api/l47/` prefix downstream

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None — both files modified cleanly. TypeScript compilation produced zero errors (no pre-existing errors either).

## User Setup Required
None - no external service configuration required. The agent service must be running on port 8001 (started via docker compose) for requests to reach it, but no new environment variables or secrets are needed for this plan.

## Next Phase Readiness
- Proxy routing layer complete — UI component (plan 07-02) can now import `useGetL47Recommendations`, `L47ScenarioRequest`, and `L47RecommendationResponse` from `useAPI.ts` and call the agent directly
- Agent must be running (`docker compose ps` shows `cyperf_agent_l47` healthy) for dev-mode requests to reach port 8001

---
*Phase: 07-frontend-l4-7-test-advisor-ui-tab-to-submit-test-scenarios-and-display-agent-recommendations*
*Completed: 2026-03-12*
