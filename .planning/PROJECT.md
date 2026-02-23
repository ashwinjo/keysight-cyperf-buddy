# Cyperf CVE Tracker

## What This Is

A web application for Keysight customers to quickly determine whether specific CVEs can be tested using Keysight's Cyperf security testing tool. Users search, browse, or batch-import CVEs and see which ones map to Cyperf's available Attack Profiles.

## Core Value

Enable security-focused Keysight customers to confidently identify which CVEs their Cyperf deployment can test, removing guesswork from vulnerability testing decisions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can search for a CVE by number (e.g., CVE-2024-1234)
- [ ] Search results display "Can be Tested" badge if CVE is supported by Cyperf
- [ ] User can browse latest CVEs from NVD API
- [ ] Browse view allows filtering by "Testable with Cyperf" status
- [ ] User can batch import a list of CVE numbers for checking
- [ ] Batch results display as downloadable/copyable report
- [ ] CVE details show CVSS score, description, references
- [ ] System syncs Cyperf supported CVEs via Cyperf Controller API

### Out of Scope

- Mobile app — Web-first, mobile optimization later
- Real-time alert subscriptions — Batch checks only in v1
- CVE remediation guidance — Tracking only, not remediation workflow
- Multi-tenant admin features — Single Cyperf Controller target in v1

## Context

**User Base:** Keysight customers (security/QA teams) validating if Cyperf covers their CVE testing needs

**Data Sources:**
- NVD API (https://nvd.nist.gov/developers/vulnerabilities) — authoritative CVE list
- Cyperf Controller API (via cyperf-api-wrapper) — Cyperf-supported CVEs

**Architecture:**
- Frontend: Web UI (dark theme, Shodan.io aesthetic)
- Backend: Python service that queries both APIs and computes intersection
- Cyperf Controller stands up separately; app connects via cyperf-api-wrapper with stored credentials

**Cyperf Details:**
- Cyperf has Controller (brain) + Agents (traffic generators) architecture
- API requires username/password authentication
- Official Python wrapper: https://github.com/Keysight/cyperf-api-wrapper

## Constraints

- **Tech Stack:** Cyperf API accessed via official cyperf-api-wrapper (Python)
- **Authentication:** Cyperf credentials managed via secrets manager (not user-entered)
- **Design:** Dark theme (Shodan.io aesthetic) with Keysight brand colors — avoid generic AI-generated UI
- **NVD API:** Public endpoint, no auth required; rate limits apply (plan for caching/batch queries)
- **Controller Endpoint:** Keysight to stand up Cyperf Controller with default credentials

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use official cyperf-api-wrapper | Keysight maintains it, reduces integration risk | — Pending |
| Dark UI inspired by Shodan.io | Security audience expects professional, serious aesthetic | — Pending |
| Secrets manager for Cyperf auth | Safer than asking users for credentials; centralizes security | — Pending |
| NVD API as CVE source | Authoritative, public, well-documented | — Pending |

---
*Last updated: 2026-02-22 after initialization*
