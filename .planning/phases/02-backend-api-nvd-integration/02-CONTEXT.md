# Phase 2: Backend API + NVD Integration - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build FastAPI endpoints to query CVE data from NVD with Redis caching and rate-limit resilience. Users interact via HTTP GET requests for:
- Searching CVE by exact ID with fuzzy/prefix support
- Browsing latest CVEs with pagination and severity filtering
- NVD responses cached in Redis to prevent rate-limit failures and ensure <100ms response times on cache hits

</domain>

<decisions>
## Implementation Decisions

### Response Structure
- Return curated subset of fields per CVE: ID, CVSS v3.1 score, CVSS v4.0 score, description, published date, references
- Flatten nested data into top-level fields (cvss_v3_score, cvss_v4_score, reference_urls) rather than nested objects
- Do not include full NVD response; focus on essential fields to minimize payload

### Pagination
- Default page size for `/cve/latest`: 50-100 results per page
- Maximum page size limit: 500 results
- Fixed sort order: published date descending (newest first)
- No custom sort parameters; always newest-first for consistency

### Caching Behavior
- Cache individual CVE records only (not paginated browse result sets)
- Cache TTL: 24+ hours per record (NVD updates infrequently)
- Proactively refresh popular CVEs in cache before TTL expiry (stale-while-revalidate pattern) to minimize NVD queries
- Serve cached data transparently: no cache metadata in response headers or body (no X-Cache-Age, no cached_at field)

### Search Query Design
- `/cve/search?id=...` supports exact match AND fuzzy/prefix matching (e.g., `CVE-2024-*` wildcards)
- `/cve/latest?severity=...` filters on CVSS v3.1 OR v4.0: return CVE if it meets the requested severity in either version
- Severity filter values are case-insensitive (HIGH, high, High all work)
- `/cve/search` endpoint also accepts optional severity parameter for combined filters (e.g., `/cve/search?id=CVE-2024-*&severity=HIGH`)

### Rate-Limit Resilience
- When NVD returns 429 rate-limit response, API serves the last cached result for that CVE with HTTP 200 (no 500 error exposed to client)
- Implement retry logic with exponential backoff before falling back to cache

### Claude's Discretion
- Error response format and status codes (4xx vs 5xx logic)
- Exact fuzzy search algorithm and performance tuning
- Proactive refresh trigger logic (when to refresh: access frequency threshold, time-until-expiry, etc.)
- Retry count and backoff strategy details

</decisions>

<specifics>
## Specific Ideas

- API should feel reliable and resilient — if NVD is unavailable, users get stale data rather than errors
- Response format should be intuitive for security tools/dashboards that consume this API
- Flattened structure is preferred because it's easier for frontend/CLI consumers to work with vs nested hierarchies

</specifics>

<deferred>
## Deferred Ideas

- Manual triggering of sync from Cyperf (belongs in Phase 3: Sync Engine)
- Batch CVE import/export (belongs in Phase 5: Batch Processing)
- Advanced search (substring search, regex patterns) — defer to future enhancement
- Rate-limit information in responses (X-RateLimit-Remaining header) — nice-to-have for future iteration

</deferred>

---

*Phase: 02-backend-api-nvd-integration*
*Context gathered: 2026-02-22*
