# Research Summary

**Project:** Cyperf CVE Tracker
**Researched:** 2026-02-22
**Research Completeness:** 100% (Stack, Features, Architecture, Pitfalls)

---

## Key Findings

### Stack (Technology Choices)

**Recommended approach:** Python FastAPI backend + React frontend with Tailwind + shadcn/ui

- **Backend:** FastAPI (async-native, perfect for dual-API calls), Python 3.12+, Pydantic 2.x
- **Frontend:** React 18 + Vite (fast builds), Tailwind 3.4 + shadcn/ui (Shodan-dark aesthetic native), TanStack Query (server state)
- **Data:** SQLite (dev), PostgreSQL 15+ (production)
- **Cache:** Redis 7 (NVD rate-limit buffer, TTL-based caching)
- **Integrations:**
  - NVD: `nvdlib` 0.7.x (handles API 2.0, pagination, rate limits)
  - Cyperf: Official `cyperf-api-wrapper` from GitHub (handles auth, session management)

**Critical decision:** Use official Keysight wrapper for Cyperf, not DIY HTTP calls. This is a mandatory, non-negotiable integration point.

---

### Features (User Value)

**v1 MVP (Must Have for Launch):**
1. Search CVE by number → View full details (CVSS, description, references)
2. "Can be Tested" badge (intersection of NVD + Cyperf)
3. Browse latest CVEs with testability filter
4. Batch import/check (paste 10+ CVEs, get results)
5. Dark Shodan-like UI (Tailwind + shadcn/ui)
6. Export results (CSV)

**Table Stakes (users expect):** Search, details view, testability indicator, dark theme

**Differentiators:** Batch operations, Cyperf-specific Attack Profile details, deep integration with ONE tool vs. shallow with many

**Out of Scope (defer to v2+):** User authentication, email alerts, multiple Cyperf Controllers, real-time CVE sync, mobile app

---

### Architecture (System Design)

**Core pattern:** Request → Check Cache (Redis/DB) → Query APIs if miss → Return results

**Key components:**
- Frontend SPA (React): Async state via TanStack Query, UI state via Zustand
- FastAPI routes: `/cve/search`, `/cve/latest`, `/cve/batch-check`, `/admin/sync-cyperf`
- NVD service: Query nvdlib, cache in Redis (TTL=1h, NVD doesn't change fast)
- Cyperf service: Background job syncs daily via cyperf-api-wrapper, stores in DB
- Intersection logic: `compute_testability() = cve_id in cyperf_supported_cves`

**Rate limiting strategy:** NVD API is strict (50 req/30s with key). Implement:
1. Redis queue for burst traffic
2. Cache aggressively (1h TTL)
3. Circuit breaker (serve stale if rate-limited)
4. Load test before launch

**Cyperf unavailability strategy:** Background sync only (not on-request). Graceful degradation:
- If Cyperf down: serve cached state + warning banner "Cyperf data is X hours old"
- No 500 errors to users; application degrades gracefully

---

### Pitfalls (What Can Go Wrong)

**Critical pitfalls to prevent:**

1. **NVD Rate Limiting Surprise** → Get API key immediately, implement Redis queue, cache aggressively (Phase 2)
2. **Cyperf Credentials Exposed** → Use secrets manager, NEVER commit .env, rotate credentials regularly (Phase 1)
3. **Cyperf Unreachability Breaks App** → Background sync only, cache last-known state, serve stale with warning (Phase 3)
4. **Data Staleness Not Communicated** → Show "Last updated X hours ago" on every page, admin button for manual refresh (Phase 2)
5. **Dark Theme Unreadable** → Use Shodan's actual palette (muted grays + high contrast), WCAG AA compliance check (Phase 1)

**Performance traps:**
- Unbounded NVD queries → Always paginate, limit to 2000
- Cyperf call in request path → Background sync only
- Single-threaded SQLite in prod → PostgreSQL + connection pooling

**Security issues:**
- Credentials in error logs → Log only CVE ID, not full details
- No HTTPS for Cyperf → TLS verification mandatory
- Untrusted Cyperf responses → Validate with Pydantic models

---

## Implementation Roadmap (Draft)

Based on research, project should have phases like:

| Phase | Goal | Tech | Risks to Mitigate |
|-------|------|------|-------------------|
| 1 | Setup + Auth Infrastructure | Python env, secrets manager, git hooks | Credentials leaking; .env committed |
| 2 | Backend API + NVD Integration | FastAPI, nvdlib, Redis, SQLite | Rate limiting; unbounded queries |
| 3 | Cyperf Integration + Sync | cyperf-api-wrapper, APScheduler, background jobs | Cyperf downtime; stale data |
| 4 | Frontend UI | React, Tailwind, shadcn/ui, dark theme | Contrast/accessibility; theme consistency |
| 5 | Testing + Optimization | pytest, load testing, caching tuning | Performance under load; reliability |
| 6 | Deployment Preparation | Docker, CI/CD, PostgreSQL migration | Production infrastructure readiness |

---

## Known Unknowns

**Cyperf-specific details (MEDIUM confidence, require verification):**
- Does cyperf-api-wrapper expose a direct method to list CVEs per Attack Profile, or must we parse profile metadata?
- What's the response time for querying ALL Attack Profiles (1000+ profiles)?
- How should we handle Cyperf Controller failover / secondary instances?
- Python 3.12 compatibility of cyperf-api-wrapper (verify at implementation)

**Recommendations:**
- Read cyperf-api-wrapper GitHub repo + documentation before Phase 3
- Contact Keysight support with integration questions
- Plan integration testing with actual Keysight test environment, not mock

---

## Success Metrics for Research

- [x] Stack chosen and justified
- [x] Tech stack aligns with Shodan aesthetic (dark native in Tailwind + shadcn/ui)
- [x] Features scoped for MVP vs. v2+ clearly delineated
- [x] Architecture supports graceful degradation (Cyperf downtime, NVD rate limiting)
- [x] Pitfalls documented with prevention strategies
- [x] Roadmap structure clear (phase breakdown, risk mitigation)
- [x] Implementation team has clear "what to build, how to build, what to avoid"

---

## Recommended Next Steps

1. **Read the research files in detail:**
   - STACK.md → Technology decisions
   - FEATURES.md → User value + prioritization
   - ARCHITECTURE.md → System design + data flow
   - PITFALLS.md → Prevention + recovery strategies

2. **Verify Cyperf integration details** (contact Keysight if needed):
   - Does cyperf-api-wrapper expose CVE list API?
   - Response time for 1000+ profiles?
   - Python 3.12 compatibility?

3. **Proceed to REQUIREMENTS.md** (next phase):
   - Map features to testable requirements (REQ-IDs)
   - Define v1 scope + v2 deferral
   - Create traceability matrix

4. **Move to roadmap creation:**
   - Phases derived from requirements
   - Success criteria for each phase
   - Risk mitigation mapped to phases

---

## Confidence Levels by Area

| Area | Confidence | Notes |
|------|-----------|-------|
| Stack (FastAPI, React, Tailwind) | HIGH | Production-standard patterns, well-established 2025 |
| NVD API Integration | HIGH | Public API well-documented, nvdlib mature |
| Rate Limiting Strategy | HIGH | Standard caching + queue patterns |
| Cyperf Integration | MEDIUM | Official wrapper exists; internal details require verification |
| Dark Theme UX | MEDIUM | Shodan aesthetic achievable with Tailwind; accessibility testing needed |
| Architecture Patterns | HIGH | Service layers, background jobs, graceful degradation standard |
| Pitfalls & Prevention | MEDIUM-HIGH | NVD/API integration pitfalls well-known; Cyperf-specific gotchas TBD |
| Performance at Scale | MEDIUM | Not yet load-tested; bottleneck analysis is theoretical |

---

*Research Summary for: Cyperf CVE Tracker*
*Completed: 2026-02-22*
*Status: Ready for Requirements Definition*
