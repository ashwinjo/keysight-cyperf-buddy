# Roadmap: Cyperf CVE Tracker

**Project:** Cyperf CVE Tracker
**Created:** 2026-02-22
**Depth:** Standard (5 phases)
**v1 Requirements:** 21 total
**Coverage:** 21/21 (100%)

---

## Phases

- [x] **Phase 1: Project Setup + Infrastructure** - Scaffold project, configure secrets management, initialize database and Redis, establish dev tooling
- [ ] **Phase 2: Backend API + NVD Integration** - FastAPI service with NVD query layer, caching, search and browse endpoints, rate-limit resilience
- [x] **Phase 3: Cyperf Integration + Sync Engine** - Connect cyperf-api-wrapper, implement background sync scheduler, compute CVE testability intersection
- [x] **Phase 3.1: Cyperf CVE Ingestion Refactor** (INSERTED) - Rework Cyperf sync pipeline using ApplicationResourcesApi.get_resources_strikes(); ingest CVE→Strike JSON mappings into persistent DB for UI cross-reference
- [x] **Phase 4: Frontend UI** - React SPA with dark Shodan aesthetic, search/browse pages, testability badges, column sorting, navigation (completed 2026-02-23)
- [ ] **Phase 5: Batch Processing + Export** - Async batch CVE import, results display, CSV export

---

## Phase Details

### Phase 1: Project Setup + Infrastructure

**Goal**: Development environment is reproducible, secrets are managed securely, and the data layer (PostgreSQL/SQLite + Redis) is operational and schema-complete.

**Depends on**: Nothing (first phase)

**Requirements**: *(No v1 functional requirements live here; this phase is the foundation all others build on. SYNC-01 and SYNC-05 depend on Redis being available from this phase.)*

Note: Phase 1 is the prerequisite for all other phases. Redis and DB schema scaffolding done here unblocks Phase 2.

**Success Criteria** (what must be TRUE when this phase completes):
1. `docker compose up` starts the full stack (FastAPI, Redis, database) with no manual steps beyond copying `.env.example`
2. Cyperf credentials are loaded from environment/secrets manager at startup; the application refuses to start if they are missing, and they never appear in logs or source control
3. Database schema migrations apply cleanly on fresh install; all tables required for CVE data, testability mappings, and sync metadata exist
4. Redis is reachable from the API container; a health-check endpoint returns Redis status
5. Pre-commit hooks reject commits that contain `.env` files or hardcoded credential patterns

**Plans**: 1 plan
- [x] 01-PLAN.md — 7 tasks: Git setup, backend/frontend skeletons, Docker Compose, Alembic migrations, health checks, final verification

---

### Phase 2: Backend API + NVD Integration

**Goal**: Users can query CVE data via the API — by exact ID, by latest list, and with CVSS severity filters — with NVD responses cached in Redis to prevent rate-limit failures.

**Depends on**: Phase 1

**Requirements**: SEARCH-01, SEARCH-02, SEARCH-05, BROWSE-01, BROWSE-02, BROWSE-04, SYNC-01, SYNC-05

**Success Criteria** (what must be TRUE when this phase completes):
1. `GET /cve/search?id=CVE-2024-1234` returns CVE details including CVSS v3.1, CVSS v4.0 score, description, published date, and references for any valid CVE that exists in NVD
2. `GET /cve/latest` returns a paginated list of CVEs sorted by published date (newest first), with each row including CVE ID, CVSS score, and published date
3. `GET /cve/latest?severity=HIGH` correctly filters the response to only return CVEs at the requested CVSS severity band (LOW, MEDIUM, HIGH, CRITICAL)
4. A second identical request for the same CVE is served from Redis cache with response time under 100ms; NVD is not re-queried
5. When NVD returns a 429 rate-limit response, the API serves the last cached result for that CVE with HTTP 200 (no 500 errors exposed to clients)

**Plans**: TBD

---

### Phase 3: Cyperf Integration + Sync Engine

**Goal**: The system knows which CVEs Cyperf can test, keeps that knowledge fresh via a daily background sync, and degrades gracefully when Cyperf is unreachable.

**Depends on**: Phase 1, Phase 2

**Requirements**: SEARCH-03, SEARCH-04, SYNC-02, SYNC-03, SYNC-04

**Success Criteria** (what must be TRUE when this phase completes):
1. A daily background job runs automatically, connects to the Cyperf Controller via `cyperf-api-wrapper`, fetches all Attack Profiles, extracts associated CVE IDs, and persists the testability mapping to the database
2. `GET /cve/search?id=CVE-2024-1234` response includes a `testable` boolean field and an `attack_profile` field populated from the most recent Cyperf sync
3. The sync job records its completion timestamp; `GET /admin/sync-status` returns the last successful sync time in ISO 8601 format
4. When the Cyperf Controller is unreachable during a scheduled sync, the job logs the failure and retains the previous sync's data without corrupting the database; no user-facing error occurs
5. An environment variable controls the sync interval; the sync can also be triggered manually via `POST /admin/sync-cyperf` for development/testing purposes

**Plans**: 2 plans
- [x] 03-01-PLAN.md — Cyperf API integration + scheduler setup (APScheduler, CyperfService, job initialization)
- [x] 03-02-PLAN.md — Sync logic + graceful degradation + admin endpoints (perform_sync, error handling, GET/POST /admin endpoints, search integration)

---

### Phase 3.1: Cyperf CVE Ingestion Refactor (INSERTED)

**Goal**: Rework the Cyperf sync pipeline to use `ApplicationResourcesApi.get_resources_strikes()` from info_fetch.py pattern, ensuring reliable CVE→Attack Profile mappings are persisted to the database and available for UI cross-reference queries.

**Depends on**: Phase 3

**Requirements**: SEARCH-03, SEARCH-04, SYNC-02, SYNC-03, SYNC-04 (refines existing Phase 3 requirements)

**Success Criteria** (what must be TRUE when this phase completes):
1. CVE data fetching uses `ApplicationResourcesApi.get_resources_strikes()` API (from info_fetch.py pattern) instead of current Phase 3 approach
2. All CVE→Strike/Attack Profile mappings are extracted from Cyperf response and stored in a structured database table
3. The sync process generates and stores a JSON file of CVE→Strike mappings as an intermediate artifact
4. UI search queries (`GET /cve/search?id=CVE-2024-1234`) correctly return testability and Attack Profile info from the new schema
5. Existing Phase 3 tests pass with the refactored ingestion logic (no regression)
6. The refactored sync handles partial/malformed Cyperf responses gracefully (same degradation patterns as Phase 3)

**Plans**: 3 plans
- [x] 03.1-01-PLAN.md — DB model + Alembic migration for cverf_cve_strike_mappings table
- [x] 03.1-02-PLAN.md — Refactor cyperf_service.py (ApplicationResourcesApi) + sync_service.py (full-replace + JSON artifact)
- [x] 03.1-03-PLAN.md — Update cve_service.py/routes/cve.py (attack_profiles array) + admin.py + test suite

### Phase 4: Frontend UI

**Goal**: Users can navigate the application, search for CVEs, browse the latest CVE list with filters, and see testability status — all within a dark-themed, accessible interface.

**Depends on**: Phase 2, Phase 3

**Requirements**: UI-01, UI-02, UI-03, UI-04, BROWSE-03, SYNC-03, SYNC-04

**Success Criteria** (what must be TRUE when this phase completes):
1. The application renders in a dark theme (background #0D1117 or equivalent Shodan-scale dark gray, monospace/semi-mono font for CVE IDs) and passes WCAG AA contrast checks for all body text
2. A persistent navigation bar links to Search, Browse, and Batch pages; the active page is visually indicated; navigation works via browser back/forward buttons without full page reloads
3. Every data table (search results, browse list) supports ascending/descending sort on CVE ID, CVSS score, and published date columns by clicking the column header
4. The "Can be Tested" badge renders as a solid green pill for testable CVEs and a muted gray pill for non-testable CVEs; the badge is visible without scrolling on each result row
5. A status bar on every page displays "Data last updated: X hours ago" reflecting the last successful Cyperf sync; if Cyperf data is stale (>25h), a warning banner appears at the top of the page
6. The browse page has a toggle/filter control labeled "Testable with Cyperf" that, when activated, hides non-testable CVEs from the results table

**Plans**: 2 plans
- [ ] 04-01-PLAN.md — Shared components + navigation + status indicators (DataTable, Badge, Navigation, StatusBar, StaleDataWarning, API hooks, types)
- [ ] 04-02-PLAN.md — Search page + Browse page + filtering (SearchPage, BrowsePage, SearchForm, TestableFilter)

---

### Phase 04.1: Sales Funnel (INSERTED)

**Goal:** Capture sales leads via contact form submissions triggered from CVE detail views. Backend sends email notifications to the sales team. Frontend provides the contact form modal and confirmation UX.
**Depends on:** Phase 4
**Plans:** 5 plans

Plans:
- [x] 04.1-01-PLAN.md — Backend email service: SMTP config, email_service.py, POST /contact/submit endpoint (complete 2026-02-24)
- [ ] 04.1-02-PLAN.md
- [ ] 04.1-03-PLAN.md
- [ ] 04.1-04-PLAN.md
- [ ] 04.1-05-PLAN.md

### Phase 5: Batch Processing + Export

**Goal**: Users can submit a list of CVE IDs, have them processed asynchronously in the background, view results in a structured table, and download a CSV report.

**Depends on**: Phase 2, Phase 3, Phase 4

**Requirements**: BATCH-01, BATCH-02, BATCH-03, BATCH-04

**Success Criteria** (what must be TRUE when this phase completes):
1. A user can paste a newline-separated or comma-separated list of CVE IDs into a text area on the Batch page and submit it; the UI immediately acknowledges submission and shows a progress indicator without blocking
2. Each submitted CVE ID is individually resolved against NVD (with cache) and the Cyperf testability database; results appear in the results table as they complete (or all at once on completion) without requiring a page refresh
3. The batch results table displays one row per CVE with columns: CVE ID, CVSS score, Testability status ("Can be Tested" / "Not Testable"), and Attack Profile name (or blank if not testable)
4. A "Download CSV" button exports the batch results table as a `.csv` file with headers `cve_id,cvss_score,testable,attack_profile`; the file downloads immediately without a server round-trip delay

**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Setup + Infrastructure | 1/1 | Complete | 2026-02-23 |
| 2. Backend API + NVD Integration | 0/? | Not started | - |
| 3. Cyperf Integration + Sync Engine | 2/2 | Complete | 2026-02-23 |
| 4. Frontend UI | 2/2 | Complete | 2026-02-23 |
| 4.1 Sales Funnel | 1/5 | In Progress | - |
| 5. Batch Processing + Export | 0/? | Not started | - |

---

## Coverage Map

| Requirement | Phase | Description |
|-------------|-------|-------------|
| SEARCH-01 | Phase 2 | Search CVE by exact ID |
| SEARCH-02 | Phase 2 | Search results include full CVE details |
| SEARCH-03 | Phase 3 | "Can be Tested" badge sourced from Cyperf sync |
| SEARCH-04 | Phase 3 | Attack Profile name displayed on search result |
| SEARCH-05 | Phase 2 | Filter search results by CVSS severity |
| BROWSE-01 | Phase 2 | Paginated latest CVE table |
| BROWSE-02 | Phase 2 | Latest CVEs sorted by published date (newest first) |
| BROWSE-03 | Phase 4 | Filter browse by testability status (UI control) |
| BROWSE-04 | Phase 2 | Browse row shows CVE ID, CVSS, date, testability |
| BATCH-01 | Phase 5 | Paste or import list of CVE IDs |
| BATCH-02 | Phase 5 | Batch processes asynchronously |
| BATCH-03 | Phase 5 | Batch results in table (CVE ID, CVSS, testable, profile) |
| BATCH-04 | Phase 5 | Export batch results as CSV |
| UI-01 | Phase 4 | Dark theme, WCAG AA contrast |
| UI-02 | Phase 4 | Tables support column sorting |
| UI-03 | Phase 4 | Navigation to Search, Browse, Batch pages |
| UI-04 | Phase 4 | "Can be Tested" badge visually prominent |
| SYNC-01 | Phase 2 | NVD API response cached in Redis |
| SYNC-02 | Phase 3 | Daily background sync from Cyperf Controller |
| SYNC-03 | Phase 4 | Last sync timestamp displayed on UI |
| SYNC-04 | Phase 4 | Stale Cyperf data served with warning banner |
| SYNC-05 | Phase 2 | NVD rate-limit → serve cached result, no 500 error |

**Coverage: 21/21 v1 requirements mapped. No orphans.**

---

*Roadmap created: 2026-02-22*
*Last updated: 2026-02-23 after Phase 4 planning*
*Phase 1 execution: 2026-02-23*
*Phase 3 execution: 2026-02-23*
*Phase 4 plans created: 2026-02-23*
