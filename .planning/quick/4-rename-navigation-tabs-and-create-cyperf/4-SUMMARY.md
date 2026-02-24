# Summary: Rename Navigation Tabs and Create Cyperf AI CVEs Tab

**Mode:** quick
**Date:** 2026-02-24
**Status:** Completed

---

## Tasks Executed

### Task 1 — Navigation.tsx (commit: `70c62de`)

**File:** `frontend/src/components/layout/Navigation.tsx`

Updated `NAV_ITEMS`:

| Before | After |
|--------|-------|
| Search (`/`) | NVD_Search (`/`) |
| Browse (`/browse`) | Cyperf Non-AI CVEs (`/browse`) |
| Batch (`/batch`) | Cyperf AI CVEs (`/ai-cves`) |
| — | What is Cyperf (`/what-is-cyperf`) |

Also removed the `uppercase` CSS class from nav link elements. The plan flagged
that `uppercase` would distort labels like "Cyperf Non-AI CVEs" and "NVD_Search"
into unreadable all-caps. Labels now render as written.

---

### Task 2 — WhatIsCyperfPage.tsx (commit: `c622dda`)

**File:** `frontend/src/pages/WhatIsCyperfPage.tsx`

Static informational page with four content sections:

- **Overview**: What CyPerf is, cloud-native positioning, multi-cloud support
- **Key Capabilities**: CVE Strike Testing, Application Simulation, AI CVEs, Cloud-Native Agents, REST API Automation
- **CyPerf + CVE²Strike**: Explains how the sync job maps strike profiles; three-column grid distinguishing Non-AI CVEs / AI CVEs / NVD Integration
- **Learn More**: Links to Keysight CyPerf product page, support docs, and Keysight home

Styled with `card-luxury`, `text-luxury-text`, `text-luxury-accent`, `bg-luxury-bg`
consistent with all existing pages. No data fetching.

---

### Task 3 — CyperfAiCvesPage.tsx + hook + type (commit: `645d08d`)

**Files changed:**
- `frontend/src/pages/CyperfAiCvesPage.tsx` (created)
- `frontend/src/hooks/useAPI.ts` (added `useAiCVEs` hook)
- `frontend/src/types/api.ts` (added `AiCVEResponse` interface)

`AiCVEResponse` fields: `id`, `description`, `severity`, `cvss_score`,
`ai_strike_name`, `generated_at`.

`useAiCVEs` fetches `GET /api/ai-cves`, single retry, 5-minute stale time.
Surfaces errors directly rather than silently swallowing them.

`CyperfAiCvesPage` features:
- Search filter across CVE ID, AI strike name, description
- Stats bar (total count, matching count when filtering)
- `AiCveTable` with severity badges (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`/`NONE` color mapping)
- Explicit **endpoint-not-available** placeholder rendered when backend returns 404
  or a network error — includes a `TODO` comment pointing to the backend task
- Generic error state for non-404 failures
- Loading spinner state

**Note:** The `/api/ai-cves` backend endpoint is not yet implemented. The page
renders a placeholder with a clear TODO and endpoint contract description until
the backend is deployed.

---

### Task 4 — App.tsx routing (commit: `0117a0c`)

**File:** `frontend/src/App.tsx`

Added two imports and two routes:

```tsx
import CyperfAiCvesPage from './pages/CyperfAiCvesPage';
import WhatIsCyperfPage from './pages/WhatIsCyperfPage';

<Route path="/ai-cves" element={<CyperfAiCvesPage />} />
<Route path="/what-is-cyperf" element={<WhatIsCyperfPage />} />
```

Existing routes (`/`, `/browse`, `/batch`) unchanged.

---

## Build Verification

```
tsc && vite build
✓ 1984 modules transformed.
✓ built in 1.43s
```

Zero TypeScript errors. Zero Vite build warnings.

---

## Deferred / Follow-up

- `BatchPage` (`/batch`) is still wired and functional but no longer appears in
  the navigation. It can be accessed directly via URL. No changes were made to it.
- `GET /api/ai-cves` backend endpoint needs to be implemented. The frontend
  contract is: `{ results: AiCVEResponse[], total: number }`.
  See `frontend/src/types/api.ts` for the `AiCVEResponse` shape.
