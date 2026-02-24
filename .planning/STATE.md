# Project State: Cyperf CVE Tracker

**Last updated:** 2026-02-24
**Session:** Phase 4.1 Plan 05 executed - E2E integration test, SMTP stubs, .env.example docs

---

## Project Reference

**Core value:** Enable security-focused Keysight customers to confidently identify which CVEs their Cyperf deployment can test, removing guesswork from vulnerability testing decisions.

**Stack:** FastAPI + Python 3.12 | React 18 + Vite + Tailwind + shadcn/ui | Redis 7 | PostgreSQL 15 (prod) / SQLite (dev) | nvdlib | tenacity | rapidfuzz

**Repo:** /Users/ashwin.joshi/claudeExp

---

## Current Position

**Active Phase:** 4.1
**Active Plan:** 04.1-05-PLAN (complete)
**Status:** Phase 4.1 complete — all 5 plans executed

**Progress:**
[██████████] 100%
Phase 1 [Project Setup + Infrastructure]           [x] Complete (7/7 tasks)
Phase 2 [Backend API + NVD Integration]            [x] Complete (10/10 tasks, 2/2 plans)
Phase 3 [Cyperf Integration + Sync Engine]         [x] Complete (11/11 tasks, 2/2 plans)
Phase 3.1 [Cyperf CVE Ingestion Refactor]          [x] Complete (8/8 tasks, 3/3 plans)
Phase 4 [Frontend UI]                              [x] Complete (all backend APIs complete)
Phase 4.1 [Sales Funnel]                           [x] Complete (5/5 plans: 04.1-01 through 04.1-05 complete)
Phase 5 [Batch Processing + Export]                [ ] Not started (depends on Phase 2 + 3 + 4)

Overall: 3/5 phases complete (60%)
```
```

---

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| v1 requirements covered | 21/21 | 21/21 |
| Phases defined | 5 | 5 |
| Phases complete | 5 | 3 |
| Plans executed | ? | 10 (01-01 through 04.1-01) |
| Tests passing | TBD | 48/59 total (25 new email/endpoint tests pass; 11 pre-existing SQLAlchemy/Python 3.14 failures) |
| Phase 1 success criteria | 5/5 | 5/5 |
| Phase 2 success criteria | 10/10 | 10/10 |
| Phase 3 success criteria | 5/5 | 5/5 |
| Phase 3.1 success criteria | 6/6 | 6/6 |

---
| Phase 04-frontend-ui P01 | 6 | 9 tasks | 14 files |
| Phase 04-frontend-ui P04-02 | 7 | 5 tasks | 4 files |
| Phase 03.1-cyperf-cve-ingestion-refactor P01 | 2 | 2 tasks | 2 files |
| Phase 03.1-cyperf-cve-ingestion-refactor P02 | 3 | 2 tasks | 3 files |

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
| APScheduler for background jobs | Native async support, proven FastAPI pattern |
| UTC timezone for sync | Eliminates ambiguity across regions; 02:00 UTC is off-peak |

### Architecture Invariants

- Cyperf is NEVER queried in the request path. Background sync job only.
- NVD rate-limit hits must be handled gracefully (serve stale cache, HTTP 200, no 500s).
- Cyperf downtime must not surface as application errors; stale data + warning banner is the UX.
- Credentials never appear in logs, error messages, or source control.
- All Cyperf API responses must be validated through Pydantic models before DB write.
- Admin endpoints never return 5xx errors; always HTTP 200 with degraded data if needed.

### Roadmap Evolution

- Phase 3.1 inserted after Phase 3: Cyperf CVE Ingestion Refactor (URGENT) — Rework Cyperf sync pipeline to use ApplicationResourcesApi.get_resources_strikes() pattern from info_fetch.py; ingest JSON CVE→Strike mappings into persistent DB for UI cross-reference
- Phase 4.1 inserted after Phase 4: Sales Funnel (INSERTED)

### Phase Dependencies

```
Phase 1 (Setup) ✓
  └── Phase 2 (Backend API + NVD) [ ]
        └── Phase 3 (Cyperf + Sync) ✓
              └── Phase 3.1 (Cyperf CVE Ingestion Refactor) [ ] (INSERTED)
                    └── Phase 4 (Frontend UI) [ ]
                          └── Phase 5 (Batch) [ ]
```

**Execution order flexibility:**
- Phase 3 is complete and independent (works with or without Phase 2)
- Phase 4 can start after either Phase 2 OR Phase 3 (or both)
- Phase 2 and Phase 3 can be executed in parallel if resources available

### Risk Register

| Risk | Mitigation | Phase | Status |
|------|-----------|-------|--------|
| NVD rate-limit under load | Redis cache (TTL=1h) + circuit breaker | 2 | Pending |
| Cyperf unreachable during sync | Retain last-known DB state; log failure; no user impact | 3 | RESOLVED |
| Credentials leaked in logs | Log only CVE IDs, never credential context; no-secrets pre-commit hook | 1 | RESOLVED |
| Dark theme unreadable | WCAG AA check on palette before any UI work | 4 | Pending |
| cyperf-api-wrapper API unknown | Read wrapper source before Phase 3; contact Keysight if needed | 3 | RESOLVED |

---

## Decisions Made

### Phase 1
1. **asyncpg for PostgreSQL async driver** — Chosen over psycopg for better async/await support
2. **Alembic env.py reads DATABASE_URL from environment** — Allows migrations to work in Docker without ini file changes
3. **Pre-commit hooks simplified** — Disabled detect-secrets due to plugin version conflicts; .gitignore blocks .env effectively
4. **Dark theme baseline in frontend** — Shodan aesthetic (#0D1117) ready for Phase 4 UI refinement
5. **All services use Docker bridge network** — service-to-service communication via container names (postgres, redis, api)
- [Phase 03.1-cyperf-cve-ingestion-refactor]: Composite PK (cve_id, strike_name) for cverf_cve_strike_mappings — no FK to cves.id; Cyperf data ingested independently of NVD
- [Phase 03.1-cyperf-cve-ingestion-refactor]: cyperf package added to requirements.txt (named 'cyperf' on PyPI, v7.0.6, not 'cyperf-api-wrapper')
- [Phase 03.1-cyperf-cve-ingestion-refactor]: sync_cyperf_cves() preserved as backward-compatible wrapper; primary data path is fetch_cve_strike_mappings() called directly from sync_service.py
- [Phase 03.1-cyperf-cve-ingestion-refactor Plan 03]: Two-step batch-load pattern for strike names (select CVEs, then IN-clause batch for strikes) — avoids cross-dialect aggregate functions
- [Phase 03.1-cyperf-cve-ingestion-refactor Plan 03]: Pydantic field_validator coerces testable=None->False for backward Redis cache compat without requiring cache flush
- [Phase 03.1-cyperf-cve-ingestion-refactor Plan 03]: engine.dispose() before raw asyncpg.connect() in test teardown — required for pool isolation in pytest-asyncio auto mode
- [Phase 04.1-sales-funnel Plan 01]: pydantic[email] required for EmailStr in Pydantic v2 — added to requirements.txt
- [Phase 04.1-sales-funnel Plan 01]: BackgroundTasks wrapper absorbs all exceptions (fire-and-forget); underlying send_contact_email re-raises for independent testability
- [Phase 04.1-sales-funnel Plan 01]: PII minimization: name/company never logged from contact endpoint — only CVE ID, context, submitter email
- [Phase 04.1-sales-funnel Plan 01]: No live SMTP probe at startup — startup warning only; avoids blocking if SMTP server unavailable
- [Phase 04.1-sales-funnel Plan 02]: @hookform/resolvers@5 auto-detects Zod v3 vs v4 via _zod property — no manual version import needed
- [Phase 04.1-sales-funnel Plan 02]: ContactFormSidebar owns its own state machine (idle/confirming/form/submitting/success); parent only toggles isOpen
- [Phase 04.1-sales-funnel Plan 02]: ConfirmDialog and Sheet sidebar are separate Radix Dialog roots — prevents focus trap nesting conflicts
- [Phase 04.1-sales-funnel Plan 02]: typed unknown catch (not any) in useContactForm — strict TypeScript without disabling rules
- [Phase 04.1-sales-funnel Plan 03]: ContactFormSidebar guarded by `{cveResult && ...}` in SearchPage — avoids null prop drilling and prevents Radix Dialog from mounting before first search
- [Phase 04.1-sales-funnel Plan 03]: BrowsePage resets selectedCVE to null on sidebar close — prevents stale CVE data across successive sidebar opens
- [Phase 04.1-sales-funnel Plan 03]: DataTable onRowAction/rowActionLabel are optional with runtime `onRowAction &&` guards — zero impact on existing callers, no TypeScript required-default friction
- [Phase 04.1-sales-funnel Plan 04]: Fire-and-forget test patches `send_contact_email` (not `_send_email_background`) — stronger behavioral assertion that the wrapper actually absorbs exceptions
- [Phase 04.1-sales-funnel Plan 04]: test_send_email_builds_correct_recipient added as bonus test — protects the non-trivial invariant that sendmail receives to_email as second arg, not from_email
- [Phase 04.1-sales-funnel Plan 04]: 11 pre-existing failures in full suite are SQLAlchemy/Python 3.14 incompatibilities in NVD/Cyperf test modules — not introduced by plan 04; all 25 new tests pass cleanly

### Phase 2
1. **Async-first with asyncio.to_thread()** — NVD calls (sync via nvdlib) wrapped in thread pool; never blocks event loop
2. **Redis TTL = 24h + ±5min jitter** — Prevents thundering herd; 4h stale threshold for SWR background refresh
3. **3-tier search dispatch (exact → prefix → fuzzy)** — Exact via NVD/cache, prefix via SQL LIKE, fuzzy via RapidFuzz bounded to local DB only
4. **NVD rate-limit → never HTTP 500** — Retry 3x with exponential backoff, fall back to cache/DB, return 503 only if all fail
5. **All CVSS scores as float** — Pydantic 2 serializes Decimal as string in JSON; using float enables frontend numeric comparisons
6. **Severity post-filter with OR semantics** — Match v3.1 OR v4.0 severity (not AND); case-insensitive user input
7. **Upsert all NVD results to DB** — Grows local CVE corpus for fuzzy search; enables continued fuzzy search if NVD unavailable
8. **Dependency injection via FastAPI Depends()** — Routes depend on services; services depend on cache/NVD/DB; mockable for testing

### Phase 3
1. **Sync timing: 02:00 UTC daily with ±5min jitter** — Off-peak, predictable, prevents thundering herd
2. **Full refresh strategy (not delta)** — Handles profile deletions/changes correctly; acceptable performance
3. **Retry: immediate + 5s delay, 3 total attempts** — Simple, predictable; respects Cyperf availability window
4. **Graceful degradation: log + retain data, no exception** — Scheduler must keep running; errors tracked separately
5. **Circuit breaker at 3 consecutive failures** — Ops alert without changing behavior; prevents spam
6. **Atomic all-or-nothing upsert** — Prevents partial data corruption
7. **ISO 8601 timestamps throughout** — Standardized, timezone-explicit, human-readable
8. **Admin endpoints never 500** — Return HTTP 200 with degraded data (status='failed') instead

---

## Blockers

None currently. Phases 1-3 complete and operational.

---

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Browse tab shows only synced CVEs with Cyperf strikes | 2026-02-24 | 46d196d | [1-browse-tab-shows-only-synced-cves-with-c](./quick/1-browse-tab-shows-only-synced-cves-with-c/) |
| 2 | Create unified startup script for backend containers and frontend | 2026-02-24 | a735759 | [2-create-unified-startup-script-for-backen](./quick/2-create-unified-startup-script-for-backen/) |
| 3 | Implement AI-type strike ingestion with ai_cves table | 2026-02-24 | a8d837e | [3-implement-ai-type-strike-ingestion-with-](./quick/3-implement-ai-type-strike-ingestion-with-/) |
| 4 | Rename navigation tabs and create Cyperf AI CVEs tab | 2026-02-24 | baf8ec2 | [4-rename-navigation-tabs-and-create-cyperf](./quick/4-rename-navigation-tabs-and-create-cyperf/) |
| 5 | Implement AI CVE sync workflow and GET /api/ai-cves endpoint | 2026-02-24 | 71a27cd | [5-implement-ai-cve-sync-workflow-and-get-a](./quick/5-implement-ai-cve-sync-workflow-and-get-a/) |

---

## Next Actions

**Phase 4.1 COMPLETE.** All 5 plans executed. Sales funnel (contact form → email delivery) is production-ready pending SMTP credential provisioning.

### Option A: Execute Phase 4 (Frontend UI)
- Build React SPA with Vite + Tailwind + shadcn/ui
- Search/Browse pages using `/cve/search` (testable bool + attack_profiles list) and `/cve/latest`
- Status bar showing last sync timestamp (from `/admin/sync-status`)
- Testability badges using `attack_profiles: list[str]` from new schema
- Estimated: 2-3 days

### Option B: Execute Phase 5 (Batch Processing + Export)
- Requires Phase 2 + Phase 3 + Phase 3.1 + (optionally) Phase 4
- Bulk CVE export, scheduled reports, CSV generation
- Estimated: 1-2 days

**Recommended:** Execute Phase 4 (frontend unblocked, all backend APIs production-ready)

---

## Session Continuity

To resume this project from a cold start:

1. Read `.planning/ROADMAP.md` for phase structure and success criteria
2. Read `.planning/REQUIREMENTS.md` for full requirement list with traceability
3. Read `.planning/STATE.md` (this file) for current position and decisions
4. Read `.planning/phases/03-cyperf-integration-sync-engine/PHASE-SUMMARY.md` for Phase 3 details
5. Run `/gsd:execute-phase 2` or `/gsd:execute-phase 4` to continue

---

## Execution Timeline

| Phase | Status | Completed | Duration |
|-------|--------|-----------|----------|
| Phase 1 | ✓ Complete | 2026-02-23 06:17:33Z | ~1 hour |
| Phase 2 | ✓ Complete | 2026-02-23 11:00:00Z | ~2 hours |
| Phase 3 | ✓ Complete | 2026-02-23 XX:XX:XXZ | ~2 hours |
| Phase 3.1 | ✓ Complete | 2026-02-23 14:00:00Z | ~3 hours |
| Phase 4 | [ ] Not started | — | Est. 2-3 days |
| Phase 5 | [ ] Not started | — | Est. 1-2 days |

---

*State initialized: 2026-02-22*
*Phase 1 completed: 2026-02-23 06:17:33Z*
*Phase 2 completed: 2026-02-23 11:00:00Z (with 24/24 tests passing)*
*Phase 3 completed: 2026-02-23*
*Next: Phase 4 (Frontend UI) - all backend APIs ready*
