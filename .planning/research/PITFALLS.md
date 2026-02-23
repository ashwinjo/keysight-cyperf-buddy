# Pitfalls Research

**Domain:** CVE Tracker + NVD/Cyperf API Integration
**Researched:** 2026-02-22
**Confidence:** MEDIUM-HIGH (NVD API gotchas well-documented; Cyperf patterns inferred; tested against security tool projects)

---

## Critical Pitfalls

### Pitfall 1: NVD API Rate Limiting Surprise

**What goes wrong:**
- Application works fine for 10 concurrent users, then suddenly fails with 429 (Too Many Requests)
- No graceful degradation; errors returned to users
- Team doesn't realize rate limits apply PER IP ADDRESS, not per app

**Why it happens:**
- Developers test locally (single requests) then deploy to production (burst traffic)
- NVD rate limits are strict: 5 req/30s without API key, 50 req/30s with key
- No built-in backoff/queuing; errors must be handled in application code

**How to avoid:**
1. **Get API key immediately** — Request from https://nvd.nist.gov/developers/request-an-api-key (free)
2. **Implement Redis queue** — Buffer requests using APScheduler + celery-like pattern
3. **Add circuit breaker** — If rate-limited, serve stale cache instead of error
4. **Cache aggressively** — TTL=3600s (1h) for CVE data; NVD updates on schedule not on-demand
5. **Load test with realistic concurrency** — Simulate 50+ simultaneous searches before launch

**Warning signs:**
- Error logs showing `HTTP 429 Too Many Requests` from nvd.nist.gov
- Users reporting "random failures" that clear up after a minute
- Metrics show correlation between search spike and error spike

**Phase to address:**
- Phase 2 (Backend Setup): Implement caching + rate limit handling upfront, not as afterthought
- Phase 4 (Integration Testing): Load test NVD integration with 100+ simulated users

---

### Pitfall 2: Cyperf API Credentials Exposed in Code/Logs

**What goes wrong:**
- Cyperf username/password ends up in git history, logs, or environment files
- Credentials rotate, code doesn't; service breaks on next deploy
- Multiple developers share same account credentials; no audit trail

**Why it happens:**
- Developers use `.env` file for secrets (works locally, gets committed)
- Error logs print full exceptions including credential context
- "Just use environment variables" seems secure but isn't if env file is committed

**How to avoid:**
1. **Use secrets manager** — Vault, AWS Secrets Manager, or Azure Key Vault
2. **Never commit .env files** — Add to .gitignore immediately; use .env.example instead
3. **Rotate credentials regularly** — Service account should support programmatic credential rotation
4. **Audit logging** — Log "Cyperf sync started" but NOT the credentials used
5. **One service account per environment** — Dev uses dev Cyperf Controller, prod uses prod

**Warning signs:**
- Credentials found in git blame on a non-sensitive file
- Error stack trace printed to logs showing cyperf-api-wrapper auth failure with full context
- Manual credential sharing between team members

**Phase to address:**
- Phase 1 (Project Setup): Configure secrets manager before any backend code
- Phase 2 (Backend Setup): Cyperf client integration uses secrets manager, not env vars

---

### Pitfall 3: Cyperf Controller Unreachability Breaks User Experience

**What goes wrong:**
- Cyperf Controller goes offline for maintenance
- Every user search returns "Service Unavailable"
- No graceful fallback; application is down

**Why it happens:**
- Synchronous call to Cyperf in the request path: `compute_testability() → query Cyperf → return result`
- No cache of previously-known Cyperf state
- No health check or retry logic

**How to avoid:**
1. **Background sync only** — Query Cyperf every 24h via background job, NOT on request
2. **Cache in database** — Store last-known Cyperf CVE mapping; survives restarts
3. **Serve stale data gracefully** — Display "Cyperf data is X hours old" banner if stale
4. **Add Cyperf health check** — Retry with exponential backoff; emit alerts
5. **Circuit breaker pattern** — If Cyperf fails 3x, circuit opens; return cached data with warning

**Warning signs:**
- Cyperf downtime correlates exactly with app error spike
- Logs show repeated connection timeouts to Cyperf Controller
- Users can't search or get inconsistent "testable" badges

**Phase to address:**
- Phase 3 (Cyperf Integration): Background job + caching built in, not added after
- Phase 4 (Integration Testing): Test Cyperf failure scenarios (kill controller, network timeout)

---

### Pitfall 4: NVD Data Staleness Not Communicated

**What goes wrong:**
- User sees CVE-2024-9999 in app but NVD API shows it doesn't exist yet
- New CVEs appear on NVD but app shows them 24+ hours later
- User thinks tool is broken; team gets "your data is out of sync" complaints

**Why it happens:**
- Background sync job runs on schedule, but sync time/success not displayed
- No "last updated" timestamp on results
- User doesn't know app data is intentionally stale

**How to avoid:**
1. **Show sync timestamp** — "CVE data updated 2 hours ago" footer on every page
2. **Show sync status** — Success/failure badge for Cyperf sync
3. **Allow manual refresh** — Admin button to force immediate NVD sync (rate-limit aware)
4. **Document sync strategy** — README explains "data updates every 24 hours"
5. **Alert on sync failure** — Email ops if NVD or Cyperf sync fails twice in a row

**Warning signs:**
- User feedback: "Your data is 3 days old"
- Mismatch between app results and NVD.nist.gov results
- No indication on UI when data was last refreshed

**Phase to address:**
- Phase 3 (Cyperf Integration): Build timestamp/status tracking into sync job
- Phase 2 (Frontend): Display metadata on every page

---

### Pitfall 5: Dark Theme UI Implementation Breaks Readability

**What goes wrong:**
- "Dark theme" means black background but insufficient contrast on text
- Tables are unreadable due to low contrast
- Shodan aesthetic aspiration becomes unusable accessibility disaster

**Why it happens:**
- Copy-pasting Tailwind `dark:` classes without checking WCAG AA compliance
- Developers test on high-quality displays; users on laptops/bad monitors suffer
- "Shodan.io aesthetic" interpreted literally without considering Shodan's specific color choices

**How to avoid:**
1. **Use a vetted dark palette** — Shodan uses muted grays (#1a1a1a bg, #e0e0e0 text); replicate these
2. **Check contrast ratios** — Use WCAG AA standard (4.5:1 for text) during design
3. **Test on multiple monitors** — Built-in laptop display, external monitor, phone browser
4. **Use shadcn/ui dark theme** — Components already meet accessibility standards
5. **Get designer review** — If possible; dark UIs are easy to mess up

**Warning signs:**
- User feedback: "Table is hard to read on my screen"
- Contrast checker shows 3:1 ratio (fails WCAG AA)
- Fidgeting with colors test 10+ variants to get it readable

**Phase to address:**
- Phase 1 (UI Design): Test dark palette before coding
- Phase 2 (Frontend): Accessibility audit before launch

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|--------------------|
| Hardcoded Cyperf IP/port | Faster setup | Can't rotate; breaks on network change | Never — costs more to fix later |
| SQLite in production | Zero setup | Breaks under concurrent load; no HA | Dev/demo only |
| No database backups | Saves 30 min setup | Data loss on disk failure | Never — MVP still needs backups |
| Caching with 1-hour TTL only | Simple; avoids stale data | But NVD changes infrequently; wasted cache hits | Acceptable; tune after metrics |
| No rate-limit handling | Faster MVP | App fails under load | Unacceptable; must handle before release |
| Credentials in .env | Fast local development | Security breach when committed | Only in dev; use secrets manager for prod |
| No Cyperf sync retry logic | Simpler code | One network blip = permanent stale state | Unacceptable; implement retries |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|---------------------|
| NVD API pagination | Assume result count < 2000 | NVD returns paginated results; use nvdlib's pagination handling or limit startIndex to max 99,900 |
| NVD API timestamp format | Parse published/modified as ISO8601 string naively | NVD returns RFC3339 format; use dateutil.parser.parse() to handle timezone correctly |
| Cyperf API session auth | Store session token globally between requests | Cyperf-api-wrapper handles token lifecycle; create new client per request or reuse with connection pooling |
| Redis key collisions | Use same prefix for all keys | Namespace keys: `cve:{cve_id}`, `cyperf:sync:timestamp`, `rate_limit:nvd` |
| SQLite write locks | Query DB during write transaction | Use SQLite WAL mode (Write-Ahead Logging) or migrate to Postgres for production |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|--------------------|
| Unbounded NVD query (no limit) | First search fine, batch search crashes | Always paginate; limit results to 2000 | Any batch > 2000 CVEs |
| Redis connection pool exhausted | Random "connection timeout" errors | Set pool_size=10, max_overflow=5 in Redis config | > 10 concurrent requests |
| Lazy-load all Cyperf profiles on startup | Slow startup; high memory | Load on first request or background job | Cyperf has 1000+ profiles |
| No DB query index on cve_id | Fast for 100 CVEs, slow for 10k | Add `CREATE INDEX idx_cve_id ON cves(cve_id)` | > 5k CVEs in table |
| Serialize entire CVE object to Redis | JSON bloat; slow serialization | Store only necessary fields: id, cvss, published | Large result sets (1000+ CVEs) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|---------------|
| Trust Cyperf response without validation | Injection attack; corrupted data from Cyperf | Validate all Cyperf API responses against Pydantic models; fail on validation error |
| Expose CVE data in error messages | Information disclosure | Log full exceptions to stderr only; return generic error to frontend ("CVE not found") |
| No HTTPS for Cyperf connection | Credentials intercepted; auth bypass | Always use TLS; verify certificate in production; fail loudly if cert invalid |
| Allow arbitrary SQL queries from user input | SQL injection | Use ORM (SQLAlchemy) only; parameterized queries; never string-interpolate user input |
| CVE search query logged without sanitization | PII exposure if CVE contains proprietary info | Log only CVE ID, not full CVE details; assume CVE list may be sensitive |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| "Can be Tested" badge is faint gray on dark background | Users miss the key info | Make testable CVEs GREEN (#22c55e) or YELLOW (#eab308); non-testable is gray |
| Search doesn't find CVE-2024-1234 if entered as "2024-1234" | Frustration; "app is broken" | Auto-format input: accept "2024-1234" and "CVE-2024-1234" and "cve 2024 1234" |
| Batch import result not exportable | Users must copy-paste manually | Always provide "Export CSV" button on results page |
| No indication of sync status or freshness | Users don't know data is 24h old | Show "Last updated: 2 hours ago" on every page; show Cyperf sync age |
| Slow search (5+ seconds) | Users think app is broken | Load test; if real, show progress indicator; stream results if batch > 100 |

---

## "Looks Done But Isn't" Checklist

- [ ] **Search endpoint:** Works with exact CVE ID but fails with partial match (e.g., "2024-1") — need autocomplete or tolerance
- [ ] **Testability badge:** Appears on search but is missing from browse/batch results — needs consistent styling
- [ ] **Cyperf sync:** Runs daily but doesn't log errors — monitor can't detect silent failures
- [ ] **Rate limiting:** Works locally but not in production because IP address is shared — need queue/backoff
- [ ] **Error handling:** Returns 500 on NVD timeout but should return 503 (Service Unavailable) with cached result
- [ ] **Dark mode:** Works on new Chrome but not on Safari (vendor prefix issue) — test cross-browser

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|-----------------|
| NVD API rate limited | LOW | Implement queue + backoff; clear error to user; serve stale cache |
| Cyperf credentials exposed | HIGH | Rotate credentials immediately; scan git history; audit logs; notify security |
| Cyperf sync failed silently for 3 days | MEDIUM | Restore from backup; re-sync; add monitoring alerts |
| Database corruption due to SQLite write lock | HIGH | Restore from backup; migrate to Postgres; audit data integrity |
| Dark theme unreadable (contrast too low) | LOW | Adjust palette; push hotfix; no data loss |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------------|
| NVD Rate Limiting | Phase 2 (Backend) | Load test with 100+ concurrent searches; verify no 429 errors |
| Cyperf Credentials Exposed | Phase 1 (Setup) | Review .gitignore; scan git history for plaintext secrets; use secrets manager |
| Cyperf Unreachability | Phase 3 (Integration) | Test by disabling Cyperf; verify graceful degradation + stale data served |
| NVD Data Staleness | Phase 3 (Integration) | Add sync timestamp; verify displayed on UI; test manual refresh works |
| Dark Theme Readability | Phase 2 (Frontend) | WCAG AA contrast check; user acceptance testing on 3+ displays |
| SQL Injection | Phase 2 (Backend) | Code review; use SQLAlchemy ORM exclusively; fuzz test with malicious input |
| Silent Sync Failures | Phase 3 (Integration) | Add monitoring; verify alerts fire when sync fails 2x in a row |

---

## Sources

- NVD API documentation: nvd.nist.gov/developers (HIGH confidence)
- Cyperf API wrapper: GitHub repo + Keysight SDK patterns (MEDIUM confidence)
- WCAG accessibility standards: W3C (HIGH confidence)
- Rate limiting patterns: Industry best practices (HIGH confidence)
- Common CVE tracker mistakes: Shodan, Vulners, OpenCVE design patterns (MEDIUM confidence)

---

*Pitfalls research for: Cyperf CVE Tracker*
*Researched: 2026-02-22*
