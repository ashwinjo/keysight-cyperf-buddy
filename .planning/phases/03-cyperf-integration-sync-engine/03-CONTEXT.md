# Phase 3: Cyperf Integration + Sync Engine - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning
**Decision Model:** Claude's Discretion (all areas)

---

<domain>
## Phase Boundary

Connect to the Cyperf Controller via the official `cyperf-api-wrapper`, sync Attack Profile CVE mappings daily in the background, store testability data in the database, and degrade gracefully when Cyperf is unreachable.

**Scope:** CVE-to-Attack-Profile mapping only. Individual profile detail pages are Phase 4+. Cyperf credential rotation is ops/security phase.

</domain>

---

<decisions>
## Implementation Decisions

### Sync Scheduling & Frequency

- **Schedule:** Daily background job at **02:00 UTC** (off-peak, predictable)
- **Interval:** Every 24 hours (NVD doesn't change CVEs frequently; once daily is standard)
- **Jitter:** +/- 5 minutes random jitter to avoid thundering herd in multi-instance deployments
- **Failure handling:**
  - Failed sync does NOT block subsequent syncs
  - On network failure: retry once immediately, then wait 5 minutes, then retry once more
  - If both retries fail: log error, skip this cycle, wait for next scheduled sync (24h later)
  - No exponential backoff; simple fixed retry keeps ops simple
- **Trigger:** Manual `POST /admin/sync-cyperf` endpoint allows immediate sync for testing/emergency use
- **Environment variable:** `CYPERF_SYNC_INTERVAL_HOURS` (default: 24) for ops to tune without redeployment

### CVE Extraction from Cyperf Profiles

- **Data model:** Query ALL Attack Profiles from Cyperf Controller, extract CVE IDs from each profile metadata
- **Caching strategy:** **Full refresh on every sync** (not delta)
  - Reason: Cyperf profiles can be updated, deleted, or have CVE associations changed. Full refresh is simpler than tracking deltas and handles all mutations correctly
  - Performance: If 1000+ profiles take >5min to fetch, still acceptable (runs at 02:00 UTC)
  - Batching: Fetch profiles with pagination if Cyperf supports it; if not, fetch all in one call
- **Storage:** Insert/upsert into `cyperf_supported_cves` table (CVE ID → Attack Profile name mapping)
  - Use `ON CONFLICT UPDATE` to handle profile changes idempotently
  - Index on cve_id for Phase 2 search queries
- **Handling large profile lists:** No special handling needed; standard database bulk insert patterns suffice for 10k+ CVEs
- **Profile name storage:** Store the Attack Profile NAME (human-readable, shown to users) not just ID

### Graceful Degradation

- **When Cyperf is unreachable during sync:**
  - Log the error (ops can set up alerts)
  - Retain the previous sync's data in `cyperf_supported_cves` table (DO NOT delete old mappings)
  - Mark the sync attempt as failed in `sync_metadata` table
  - No user-facing error; API continues to serve previous data
- **User visibility:**
  - Frontend shows "Data last updated: X hours ago" (from `sync_metadata.last_successful_sync`)
  - If sync is >25 hours old, show warning banner: "Cyperf data is outdated; some testability badges may be inaccurate"
  - No dramatic alerts; just quiet indicator that data is stale
- **Retry duration:** Simple 5-min retry (see Sync Scheduling) then wait for next cycle. Don't continuously retry — respect Cyperf's availability window
- **Circuit breaker:** If 3 consecutive syncs fail, emit operational alert (not user-visible). Don't change behavior; continue serving stale data and trying next scheduled sync

### Sync Status & Monitoring

- **Status endpoint:** `GET /admin/sync-status` returns:
  ```json
  {
    "last_successful_sync": "2026-02-23T02:15:34Z",
    "last_attempted_sync": "2026-02-23T02:15:34Z",
    "sync_status": "success|failed",
    "cverf_profiles_synced": 1247,
    "cverf_cves_extracted": 8934,
    "error_message": null,
    "next_scheduled_sync": "2026-02-24T02:00:00Z"
  }
  ```
- **Logging:**
  - Log at INFO level: sync started, sync completed, CVE count extracted
  - Log at ERROR level: connection failures, Cyperf API errors, database errors
  - Include context: start time, duration, retry count
  - Do NOT log Cyperf credentials or full API responses (only summary: "Fetched X profiles")
- **Metrics/Monitoring:** Track in structured logs (JSON format for ELK/Splunk):
  - `cyperf_sync_duration_seconds` — How long sync took
  - `cyperf_profiles_fetched` — Number of profiles
  - `cyperf_cves_extracted` — Total CVEs found
  - `cyperf_sync_failures` — Count of failures for alerts
- **Failure tracking:** Record failure reason in `sync_metadata.error_message` (e.g., "Connection timeout", "Invalid API key", "Database write failed")
- **What constitutes success:** All profiles fetched, all CVEs extracted, database updated, metadata recorded. Partial success (fetched some profiles, not all) is FAILURE.

### Claude's Discretion

The following areas are implementation details that Claude will handle during planning/execution:

- Exact retry backoff timing and retry count tuning
- Cyperf API pagination handling (if profiles endpoint supports limit/offset)
- Database transaction rollback strategy if sync partially fails
- Logging framework choice (structlog, python logging, etc.)
- APScheduler vs alternative job scheduler evaluation
- Timezone handling (UTC vs local — using UTC throughout)
- Alerting thresholds (e.g., "alert after 3 consecutive failures")

</decisions>

---

<specifics>
## Specific Ideas

- **Inspiration:** Follow Shopify's sync patterns — background jobs are simple, resilient, and observable. Full refresh beats complex delta logic.
- **Philosophy:** "Slow and steady wins the race" — 24-hour sync is fine for security CVE data. Avoid over-engineering for real-time that users don't need.
- **Operational safety:** Manual `/admin/sync-cyperf` endpoint is critical for incident response (if profiles change unexpectedly, ops can trigger immediate re-sync)

</specifics>

---

<deferred>
## Deferred Ideas

- **Multi-Cyperf Controller support** — Future phase (v2). Single controller for now.
- **Cyperf Controller health checks** — Could be added to Phase 3, but not required for MVP. Deferred to ops/monitoring phase.
- **Historical sync tracking** — Keeping audit trail of all past syncs. Future phase if compliance requires it.
- **CVE version tracking** — Tracking when a CVE's testability changed over time. Not needed for MVP; deferred to analytics phase.

</deferred>

---

*Phase: 03-cyperf-integration-sync-engine*
*Context gathered: 2026-02-23*
*Decision mode: Claude's Discretion (user delegated all decisions)*
