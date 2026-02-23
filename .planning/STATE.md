# Project State: Cyperf CVE Tracker

**Last updated:** 2026-02-22
**Session:** Initial roadmap creation

---

## Project Reference

**Core value:** Enable security-focused Keysight customers to confidently identify which CVEs their Cyperf deployment can test, removing guesswork from vulnerability testing decisions.

**Stack:** FastAPI + Python 3.12 | React 18 + Vite + Tailwind + shadcn/ui | Redis 7 | PostgreSQL 15 (prod) / SQLite (dev) | cyperf-api-wrapper | nvdlib

**Repo:** /Users/ashwin.joshi/claudeExp

---

## Current Position

**Active Phase:** None (roadmap complete, no phase started)
**Active Plan:** None
**Status:** Ready to begin Phase 1

**Progress:**
```
Phase 1 [Project Setup + Infrastructure]     [ ] Not started
Phase 2 [Backend API + NVD Integration]      [ ] Not started
Phase 3 [Cyperf Integration + Sync Engine]   [ ] Not started
Phase 4 [Frontend UI]                        [ ] Not started
Phase 5 [Batch Processing + Export]          [ ] Not started

Overall: 0/5 phases complete
```

---

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| v1 requirements covered | 21/21 | 21/21 |
| Phases defined | 5 | 5 |
| Plans written | TBD | 0 |
| Tests passing | TBD | 0 |

---

## Accumulated Context

### Key Decisions (locked)

| Decision | Rationale |
|----------|-----------|
| FastAPI backend | Async-native; dual-API calls (NVD + Cyperf) benefit from async |
| React + Vite + Tailwind + shadcn/ui | Shodan dark aesthetic native; fast builds |
| Redis for NVD caching | NVD rate-limits are strict (50 req/30s); TTL=1h is appropriate |
| cyperf-api-wrapper | Mandatory; Keysight-maintained, reduces integration risk |
| Background sync for Cyperf | Cyperf call NEVER in request path; background job only |
| Secrets manager for Cyperf creds | No user-entered creds; secrets loaded at startup |
| SQLite dev / PostgreSQL prod | SQLite for local velocity; PostgreSQL for production concurrency |

### Architecture Invariants

- Cyperf is NEVER queried in the request path. Background sync job only.
- NVD rate-limit hits must be handled gracefully (serve stale cache, HTTP 200, no 500s).
- Cyperf downtime must not surface as application errors; stale data + warning banner is the UX.
- Credentials never appear in logs, error messages, or source control.
- All Cyperf API responses must be validated through Pydantic models before DB write.

### Phase Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Backend API + NVD)
        └── Phase 3 (Cyperf + Sync)
              └── Phase 4 (Frontend UI)
                    └── Phase 5 (Batch)
```

### Known Unknowns (must resolve before Phase 3)

- Does cyperf-api-wrapper expose a direct CVE list per Attack Profile, or must profile metadata be parsed?
- Response time for querying all Attack Profiles (1000+ profiles)?
- Python 3.12 compatibility of cyperf-api-wrapper?
- Cyperf Controller URL / credential format for dev environment?

### Risk Register

| Risk | Mitigation | Phase |
|------|-----------|-------|
| NVD rate-limit under load | Redis cache (TTL=1h) + circuit breaker | 2 |
| Cyperf unreachable during sync | Retain last-known DB state; log failure; no user impact | 3 |
| Credentials leaked in logs | Log only CVE IDs, never credential context; no-secrets pre-commit hook | 1 |
| Dark theme unreadable | WCAG AA check on palette before any UI work | 4 |
| cyperf-api-wrapper API unknown | Read wrapper source before Phase 3; contact Keysight if needed | 3 |

---

## Blockers

None currently.

---

## Todo (next actions)

1. Begin Phase 1: run `gsd:plan-phase 1` to generate execution plan
2. Verify Cyperf Controller credentials / endpoint are available before Phase 3

---

## Session Continuity

To resume this project from a cold start:

1. Read `.planning/ROADMAP.md` for phase structure and success criteria
2. Read `.planning/REQUIREMENTS.md` for full requirement list with traceability
3. Read `.planning/STATE.md` (this file) for current position and decisions
4. Run `gsd:plan-phase N` where N is the first incomplete phase

---

*State initialized: 2026-02-22*
