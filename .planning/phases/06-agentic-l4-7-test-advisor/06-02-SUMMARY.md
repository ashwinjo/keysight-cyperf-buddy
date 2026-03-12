---
phase: 06-agentic-l4-7-test-advisor
plan: "02"
subsystem: api
tags: [fastapi, gemini, httpx, pydantic, rapidfuzz, tenacity, docker, agent-service]

# Dependency graph
requires:
  - phase: 06-agentic-l4-7-test-advisor
    provides: GET /cyperf-applications/strikes endpoint returning distinct strike names

provides:
  - agent-service/ standalone FastAPI microservice (port 8001)
  - POST /api/l47/recommend endpoint returning top-3 ranked Cyperf profile recommendations
  - TTL-based in-memory profile cache (1h per bucket — apps/strikes)
  - Hybrid keyword + fuzzy ranking engine (rapidfuzz token_sort_ratio)
  - Gemini prompt-with-context rationale generation with template fallback
  - Async httpx backend client with tenacity retry (3 attempts, exp backoff)
  - Fail-fast startup validation for GEMINI_API_KEY
  - GET /health liveness probe

affects:
  - 06-agentic-l4-7-test-advisor (Plan 03 — portal UI integration consumes POST /api/l47/recommend)

# Tech tracking
tech-stack:
  added:
    - google-generativeai==0.7.0 (Gemini rationale generation via asyncio.to_thread)
    - tenacity==8.3.0 (retry logic for backend API client)
    - rapidfuzz==3.9.0 (fuzzy profile matching in ranking engine)
    - pydantic-settings==2.1.0 (AgentSettings with env file support)
    - httpx==0.26.0 (async HTTP client)
  patterns:
    - "Prompt-with-context pattern: fetch all candidates first, rank locally, ask Gemini for rationale on top-k only — deterministic data fetch, AI only for NL generation"
    - "TTL cache per bucket: _ProfileCache dataclass with is_valid() check; agent instantiated once at lifespan startup, cache persists in instance state between requests"
    - "asyncio.gather for concurrent bucket fetch on testing_focus=both — minimises cold-start latency"
    - "asyncio.to_thread for sync Gemini SDK calls — never blocks uvicorn event loop"
    - "Graceful degradation: backend unreachable returns empty recommendations + plain-language message, never HTTP 500"

key-files:
  created:
    - agent-service/main.py
    - agent-service/config.py
    - agent-service/models.py
    - agent-service/api_client.py
    - agent-service/ranking.py
    - agent-service/recommendation_agent.py
    - agent-service/requirements.txt
    - agent-service/Dockerfile
    - agent-service/.env.example
  modified: []

key-decisions:
  - "Prompt-with-context approach used instead of Gemini function-calling — eliminates async SDK setup complexity for single-phase delivery; Gemini handles only NL rationale, not data retrieval"
  - "Per-bucket TTL cache (apps / strikes independent) — avoids fetching 6000 records when only one bucket is needed; cache lives on agent instance (not Redis) since agent-service has no Redis dependency"
  - "Gemini rationale falls back to ranking.py template string — ensures recommendations always have rationale even if Gemini API quota exceeded or unavailable"
  - "gemini-2.0-flash model chosen — low latency, cost-efficient; temperature=0.3, max_output_tokens=150 for concise rationale"
  - "E741 ambiguous variable (l in for-loop) fixed via Rule 1 auto-fix — renamed to part for ruff compliance"

patterns-established:
  - "Agent-as-singleton pattern: RecommendationAgent instantiated once in FastAPI lifespan, stored in app.state.agent — one instance per process, cache shared across requests"
  - "Backend API bridge pattern: agent-service never accesses DB directly; all data comes via backend REST endpoints"

requirements-completed: [ADVISOR-01]

# Metrics
duration: 4min
completed: 2026-03-12
---

# Phase 06 Plan 02: L4-7 Test Advisor Agent Service Summary

**Standalone FastAPI agent-service (port 8001) with hybrid keyword+fuzzy ranking, TTL profile cache, and Gemini rationale generation powering POST /api/l47/recommend**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-12T04:05:11Z
- **Completed:** 2026-03-12T04:09:13Z
- **Tasks:** 2
- **Files modified:** 9 (all created)

## Accomplishments

- Built complete `agent-service/` standalone FastAPI microservice from scratch — 9 files, zero pre-existing code
- Implemented hybrid ranking engine combining keyword intersection score (0.6 weight) and rapidfuzz token_sort_ratio (0.4 weight) for deterministic, low-latency profile selection
- Integrated Gemini 2.0 Flash for per-recommendation rationale generation using prompt-with-context pattern, with template fallback on API failure
- TTL-based in-memory cache (1h per bucket) prevents redundant backend fetches; `asyncio.gather` warms both buckets concurrently on cold start for `testing_focus=both`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create agent-service scaffold** - `9d7c45c` (feat)
2. **Task 2: Build api_client, ranking, recommendation_agent, and main FastAPI app** - `a6e62b2` (feat)

## Files Created/Modified

- `agent-service/config.py` - AgentSettings with fail-fast GEMINI_API_KEY validation at startup
- `agent-service/models.py` - L47ScenarioRequest, Recommendation, L47RecommendationResponse Pydantic v2 models
- `agent-service/requirements.txt` - Pinned dependencies (google-generativeai, httpx, tenacity, rapidfuzz)
- `agent-service/Dockerfile` - Python 3.12-slim, non-root appuser, port 8001
- `agent-service/.env.example` - GEMINI_API_KEY and BACKEND_API_URL documentation
- `agent-service/api_client.py` - BackendAPIClient with async httpx + tenacity 3-attempt retry
- `agent-service/ranking.py` - rank_profiles_hybrid: keyword + fuzzy scoring, RankedProfile NamedTuple
- `agent-service/recommendation_agent.py` - RecommendationAgent: cache, fetching, Gemini rationale, fallback
- `agent-service/main.py` - FastAPI app: lifespan, RequestValidationError handler, /api/l47/recommend, /health

## Decisions Made

- **Prompt-with-context over function-calling:** Gemini function-calling would require async SDK scaffolding; prompt-with-context pattern delivers same quality rationale with simpler, more reliable implementation for single-phase delivery
- **Per-bucket TTL cache on agent instance:** Agent is a singleton in FastAPI app.state; cache persists between requests; separate buckets for apps/strikes means `app_performance` requests never pay cost of fetching 2000 strikes
- **gemini-2.0-flash at temperature=0.3:** Low latency + low cost; temperature 0.3 biases toward factual, specific rationale over creative variance; max_output_tokens=150 enforces conciseness
- **Graceful degradation on all failure paths:** backend unreachable, Gemini quota exceeded, unexpected exception — all return HTTP 200 with empty recommendations and plain-language message, never 500

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed E741 ambiguous variable name in main.py**
- **Found during:** Task 2 (commit pre-commit hook)
- **Issue:** Variable named `l` in validation error handler for-loop triggered ruff E741 (ambiguous variable name resembles digit 1)
- **Fix:** Renamed `l` to `part` in `str(l) for l in error.get("loc", [])` expression
- **Files modified:** agent-service/main.py
- **Verification:** ruff passes cleanly, file committed
- **Committed in:** a6e62b2

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Trivial rename for linting compliance. No behavioral change.

## Issues Encountered

None beyond the E741 linting fix above.

## User Setup Required

**External service requires manual configuration.**

To run the agent service, users must:

1. Obtain a Gemini API key from https://aistudio.google.com/app/apikey
2. Create `agent-service/.env` with `GEMINI_API_KEY=<key>`
3. Set `BACKEND_API_URL=http://localhost:8000` for local development outside Docker

## Next Phase Readiness

- `agent-service/` is fully self-contained and buildable via `docker build agent-service/`
- `POST /api/l47/recommend` is ready to consume once GEMINI_API_KEY is configured
- Plan 03 (portal UI integration) can now build the React frontend that calls this endpoint
- Infrastructure note: agent-service runs on port 8001; docker-compose.yml needs updating in Plan 03 to add the agent-service container

---
*Phase: 06-agentic-l4-7-test-advisor*
*Completed: 2026-03-12*
