# Plan: Rename Navigation Tabs and Create Cyperf AI CVEs Tab

**Mode:** quick
**Date:** 2026-02-24

## Context

- Navigation defined in: `frontend/src/components/layout/Navigation.tsx`
- Routing defined in: `frontend/src/App.tsx`
- Existing pages: `SearchPage.tsx` (`/`), `BrowsePage.tsx` (`/browse`), `BatchPage.tsx` (`/batch`)
- New tab structure: NVD_Search, Cyperf Non-AI CVEs, Cyperf AI CVEs, What is Cyperf

---

## Tasks

### Task 1: Update Navigation labels and add new routes

**File:** `frontend/src/components/layout/Navigation.tsx`

Update `NAV_ITEMS` array:

```ts
const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'NVD_Search' },
  { path: '/browse', label: 'Cyperf Non-AI CVEs' },
  { path: '/ai-cves', label: 'Cyperf AI CVEs' },
  { path: '/what-is-cyperf', label: 'What is Cyperf' },
];
```

No other changes needed in this file.

---

### Task 2: Create `CyperfAiCvesPage.tsx`

**File:** `frontend/src/pages/CyperfAiCvesPage.tsx`

- Mirrors structure of `BrowsePage.tsx` but targets ai_cves data source
- Fetches from a backend endpoint (e.g. `/api/ai-cves`) — placeholder fetch if endpoint not yet implemented
- Renders a table of AI CVE entries (CVE ID, description, severity at minimum)
- Display a "no data" state if the table is empty or endpoint returns 404

---

### Task 3: Create `WhatIsCyperfPage.tsx`

**File:** `frontend/src/pages/WhatIsCyperfPage.tsx`

- Static informational page — no data fetching required
- Content: what Cyperf is, its purpose, link to Keysight/Cyperf docs
- Styled consistently with existing luxury theme (use `text-luxury-text`, `bg-luxury-bg`)

---

### Task 4: Wire new pages into App.tsx routing

**File:** `frontend/src/App.tsx`

- Import `CyperfAiCvesPage` and `WhatIsCyperfPage`
- Add two new `<Route>` entries:
  - `<Route path="/ai-cves" element={<CyperfAiCvesPage />} />`
  - `<Route path="/what-is-cyperf" element={<WhatIsCyperfPage />} />`
- Existing routes for `/` (SearchPage) and `/browse` (BrowsePage) remain unchanged
- `/batch` route stays wired to `BatchPage` unless `BatchPage` is being repurposed (it is not — "What is Cyperf" is a new route)

---

## Execution Order

1. Task 1 — Navigation labels (unblocked, standalone)
2. Task 3 — WhatIsCyperfPage (unblocked, static, no deps)
3. Task 2 — CyperfAiCvesPage (depends on knowing the backend endpoint shape)
4. Task 4 — App.tsx routing (depends on Tasks 2 and 3 producing page components)

---

## Notes

- `BatchPage.tsx` is NOT renamed or deleted — "What is Cyperf" maps to a new `/what-is-cyperf` route, not `/batch`
- If the `ai_cves` backend table/endpoint is not yet implemented, `CyperfAiCvesPage` should render a placeholder with a clear TODO comment
- The `uppercase` CSS class on nav links will render "Cyperf Non-AI CVEs" and "NVD_Search" in all caps — evaluate whether to remove `uppercase` from the nav link class or accept the visual result
