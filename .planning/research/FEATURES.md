# Feature Research

**Domain:** CVE Tracker with Cyperf API Integration
**Researched:** 2026-02-22
**Confidence:** MEDIUM (Training knowledge + Project context; Cyperf-specific features unverified against live API)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist for a CVE tracker. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Search CVE by number/ID | Core lookup functionality; every CVE tool has this | LOW | Substring and exact match; pagination for results |
| View CVE details (CVSS, description) | Security professionals need full context to assess risk | LOW | Pull from NVD API; include CVSS v3.1 and v4.0 scores |
| Filter/browse latest CVEs | Track emerging threats; security teams monitor new releases | MEDIUM | Sort by published date; real-time or daily sync |
| Testability badge ("Can be Tested") | Core value prop: know if Cyperf can test a given CVE | LOW | Boolean flag from Cyperf API intersection |
| Batch import / bulk check | Security teams often have lists of CVEs they care about | MEDIUM | CSV/paste input; async processing for large batches |
| Dark theme UI | Security professionals expect this; reduces eye strain | MEDIUM | Shodan.io aesthetic per PROJECT.md |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Export results (CSV/JSON) | Teams need to share findings with management/legal | LOW | Include CVE#, CVSS, testability status, Cyperf profile |
| Cyperf Attack Profile details | Show which Attack Profile covers each CVE | MEDIUM | Requires querying Cyperf API for profile metadata |
| CVE severity heatmap / trends | Visual representation of threat landscape | MEDIUM | Graph: CVE count by CVSS band over time |
| Email alerts on new testable CVEs | Proactive notification for relevant new CVEs | HIGH | Requires email integration + user subscriptions (v2+) |
| Integration with Keysight Service Portal | Single sign-on; auto-populate Cyperf credentials | HIGH | Deferred to v2; requires portal API access |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|----------------|
| Real-time CVE sync (sub-minute) | "Need latest immediately" | NVD has no real-time feed; breaks rate limits; unnecessary complexity | Daily/hourly sync is standard; NVD updates on schedule not immediately |
| Vulnerability remediation guidance | "Tool should tell us how to fix" | Out of scope for Keysight; creates liability; requires expert curation | Link to NVD references and vendor advisories instead |
| Multi-Cyperf Controller support | "We have multiple Cyperf instances" | Credential management complexity; auth/authorization headache | Start single Controller; upgrade if demand warrants |
| User accounts / authentication | "Teams need separate logins" | Premature complexity; adds auth/secrets/DB burden in v1 | v1 is public/team-shared; v2 adds auth if needed |
| Mobile app | "Viewing on phone" | Shodan-like dark tables don't translate well to mobile; separate dev effort | Web-first; responsive design later if metrics justify |

---

## Feature Dependencies

```
Search CVE
    └──requires──> CVE Data Source (NVD API)
                       └──requires──> Rate Limiting / Caching

"Can be Tested" Badge
    └──requires──> CVE Data
    └──requires──> Cyperf API Integration
                       └──requires──> Credential Management (secrets)

Browse Latest CVEs
    └──requires──> CVE Data
    └──requires──> Sorting/Filtering UI

Batch Import
    └──requires──> CSV/Text Parsing
    └──requires──> Bulk Intersection (NVD + Cyperf)
    └──requires──> Results Export

Export Results
    └──enhances──> Batch Import
    └──enhances──> Search (shareable output)

Dark UI Theme
    └──enhances──> All features (visual foundation)
```

### Dependency Notes

- **Search CVE requires CVE Data:** Can't search what isn't cached/indexed. NVD API is the data source.
- **"Can be Tested" Badge requires Cyperf API:** This is the intersection logic — fundamental to MVP.
- **Batch Import requires Bulk Intersection:** Processing N CVEs against Cyperf = potential for rate limit/performance issues. Plan accordingly.
- **Export Results enhances batch/search:** Teams always need "here, send this to Bob" — make it easy early.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] **Search by CVE Number** — Primary user workflow
- [ ] **View CVE Details** — CVSS, description, published date from NVD
- [ ] **"Can be Tested" Badge** — Intersection with Cyperf supported CVEs
- [ ] **Browse Latest CVEs** — Sorted by published date with testability filter
- [ ] **Batch Import/Check** — Paste a list, get results
- [ ] **Dark Shodan-like UI** — Per user aesthetic requirement
- [ ] **Export CSV** — Teams need to share findings

### Add After Validation (v1.x)

Features to add once core is working and we have user feedback.

- [ ] **CVE Severity Heatmap** — Trend visualization
- [ ] **Cyperf Attack Profile Details** — Which profile covers each CVE
- [ ] **Performance Optimizations** — Caching layers, async batch processing
- [ ] **Responsive Design** — Better mobile experience

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **User Accounts / Authentication** — Multi-team support
- [ ] **Email Alerts** — Subscriptions for new testable CVEs
- [ ] **Multiple Cyperf Controllers** — Enterprise deployments
- [ ] **Keysight Service Portal Integration** — SSO, auto-credentials
- [ ] **Vulnerability Remediation Guidance** — Curated fix recommendations

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Search CVE | HIGH | LOW | P1 |
| View CVE Details | HIGH | LOW | P1 |
| "Can be Tested" Badge | HIGH | MEDIUM | P1 |
| Browse Latest CVEs | HIGH | MEDIUM | P1 |
| Batch Import | MEDIUM | MEDIUM | P1 |
| Dark UI | MEDIUM | MEDIUM | P1 |
| Export CSV | MEDIUM | LOW | P1 |
| Heatmap Trends | MEDIUM | HIGH | P2 |
| Cyperf Profile Details | MEDIUM | MEDIUM | P2 |
| User Accounts | LOW | HIGH | P3 |
| Email Alerts | LOW | HIGH | P3 |
| Mobile App | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Shodan.io | Vulners | OpenCVE | Our Approach |
|---------|-----------|---------|---------|-------------|
| CVE Search | Yes, powerful filtering | Yes, API-first | Yes, open source | Simple search + filter, focus on testability |
| CVSS Display | Yes, multiple versions | Yes | Yes | Yes, v3.1 + v4.0 |
| Integration with security tools | Limited | Extensive API | Limited | Cyperf-focused; single tool deep integration |
| Bulk operations | Yes (paid) | Yes | Limited | Free, built-in for MVP |
| Batch Processing | Yes (paid) | API-only | Limited | Free, web UI + API |
| Real-time data | Limited | Real-time | Real-time | Daily/hourly refresh (good enough) |

**Our advantage:** Deep integration with ONE tool (Cyperf) vs. shallow integration with many. Security teams using Cyperf get definitive answer: "Can I test this CVE?"

---

## Sources

- Project context: `.planning/PROJECT.md`
- NVD API: Standard features for CVE lookups (training knowledge, HIGH confidence)
- Cyperf API: Wrapper exists; integration patterns inferred from security tool patterns (MEDIUM confidence)
- Competitor products: Shodan.io, Vulners, OpenCVE (training knowledge snapshot; products evolve)
- UX patterns: Shodan.io aesthetic per user aesthetic requirement (PROJECT.md)

---

*Feature research for: Cyperf CVE Tracker*
*Researched: 2026-02-22*
