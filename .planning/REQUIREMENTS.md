# Requirements: Cyperf CVE Tracker

**Defined:** 2026-02-22
**Core Value:** Enable security-focused Keysight customers to confidently identify which CVEs their Cyperf deployment can test

---

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Search & Lookup

- [ ] **SEARCH-01**: User can search for a CVE by exact ID (e.g., CVE-2024-1234)
- [ ] **SEARCH-02**: Search results include CVE details (CVSS v3.1 + v4.0 scores, description, published date, references)
- [ ] **SEARCH-03**: Each search result displays "Can be Tested" badge indicating Cyperf testability
- [ ] **SEARCH-04**: Each search result displays the Cyperf Attack Profile name that covers this CVE
- [ ] **SEARCH-05**: User can filter search results by CVSS severity (LOW, MEDIUM, HIGH, CRITICAL)

### Browse

- [ ] **BROWSE-01**: User can view latest CVEs in a sortable, paginated table
- [ ] **BROWSE-02**: Latest CVEs are sorted by published date (newest first)
- [ ] **BROWSE-03**: User can filter browse results by "Can be Tested" status (testable / not testable)
- [ ] **BROWSE-04**: Each row in browse table shows CVE ID, CVSS score, published date, and testability status

### Batch Import & Processing

- [ ] **BATCH-01**: User can paste or import a list of CVE IDs (newline-separated or CSV)
- [ ] **BATCH-02**: Batch import processes CVEs asynchronously (user doesn't wait for results)
- [ ] **BATCH-03**: Batch results display in a results table with columns: CVE ID, CVSS, testability, Attack Profile
- [ ] **BATCH-04**: User can export batch results as CSV file

### User Interface

- [ ] **UI-01**: Application uses dark theme (Shodan.io aesthetic) with proper contrast (WCAG AA)
- [ ] **UI-02**: All tables support sorting by column (CVE ID, CVSS, published date)
- [ ] **UI-03**: Search, browse, and batch pages are accessible from main navigation
- [ ] **UI-04**: "Can be Tested" badge is visually prominent (green for testable, gray for not testable)

### Data Sync & Reliability

- [ ] **SYNC-01**: CVE data from NVD API is cached for performance
- [ ] **SYNC-02**: Cyperf supported CVEs are synced from Cyperf Controller daily (background job)
- [ ] **SYNC-03**: Last sync timestamp is displayed on UI ("Data last updated: X hours ago")
- [ ] **SYNC-04**: If Cyperf is unreachable, app serves last-known data with warning banner
- [ ] **SYNC-05**: If NVD API is rate-limited, app serves cached result gracefully (no 500 error)

---

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Search

- [ ] **SEARCH-ADV-01**: CVE autocomplete as user types
- [ ] **SEARCH-ADV-02**: Search by keyword (description, reference)
- [ ] **SEARCH-ADV-03**: Advanced filters (published date range, modified date range)

### Analytics & Reporting

- [ ] **ANALYTICS-01**: CVE severity heatmap (trend visualization by CVSS band)
- [ ] **ANALYTICS-02**: Testability coverage metrics (X% of CVEs are testable)
- [ ] **ANALYTICS-03**: Attack Profile usage dashboard (which profiles cover most CVEs)

### User Management & Sharing

- [ ] **USER-01**: User authentication / login
- [ ] **USER-02**: Teams can have separate CVE watchlists
- [ ] **USER-03**: Share batch results via link
- [ ] **USER-04**: Email alerts for new testable CVEs

### Cyperf Integration Extensions

- [ ] **CYPERF-01**: Support multiple Cyperf Controllers
- [ ] **CYPERF-02**: Display Cyperf Controller health status
- [ ] **CYPERF-03**: Trigger Cyperf syncs from UI (admin button)

---

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time CVE alerts (push notifications) | Out of scope for v1; requires user auth + notification infrastructure. Email alerts in v2. |
| Mobile app | Web-first approach; responsive design later if metrics justify. |
| Vulnerability remediation guidance | Outside Keysight scope; instead link to NVD and vendor advisories. |
| Multi-language support | English-only for v1; i18n infrastructure not justified yet. |
| Offline mode | Requires complex sync strategy; online-only for MVP. |
| Integration with other security tools (non-Cyperf) | Cyperf-focused integration only; other tools deferred. |
| Real-time CVE data (sub-hour sync) | NVD publishes on schedule; 24h sync is standard in industry. |

---

## Traceability

Which phases cover which requirements. Updated after roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEARCH-01 | Phase 2 | Pending |
| SEARCH-02 | Phase 2 | Pending |
| SEARCH-03 | Phase 3 | Pending |
| SEARCH-04 | Phase 3 | Pending |
| SEARCH-05 | Phase 2 | Pending |
| BROWSE-01 | Phase 2 | Pending |
| BROWSE-02 | Phase 2 | Pending |
| BROWSE-03 | Phase 4 | Pending |
| BROWSE-04 | Phase 2 | Pending |
| BATCH-01 | Phase 5 | Pending |
| BATCH-02 | Phase 5 | Pending |
| BATCH-03 | Phase 5 | Pending |
| BATCH-04 | Phase 5 | Pending |
| UI-01 | Phase 4 | Pending |
| UI-02 | Phase 4 | Pending |
| UI-03 | Phase 4 | Pending |
| UI-04 | Phase 4 | Pending |
| SYNC-01 | Phase 2 | Pending |
| SYNC-02 | Phase 3 | Pending |
| SYNC-03 | Phase 4 | Pending |
| SYNC-04 | Phase 4 | Pending |
| SYNC-05 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---

*Requirements defined: 2026-02-22*
*Last updated: 2026-02-22 after roadmap creation (traceability populated)*
