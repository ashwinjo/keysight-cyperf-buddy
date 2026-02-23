---
phase: 04-frontend-ui
plan: 01
subsystem: ui
tags: [react, typescript, shadcn-ui, tailwind, react-query, react-router, axios]

# Dependency graph
requires:
  - phase: 03-cyperf-integration-sync-engine
    provides: "GET /admin/sync-status endpoint with SyncStatusResponse shape"
  - phase: 01-project-setup
    provides: "Vite + React + Tailwind dark theme baseline (dark-900 #0D1117)"

provides:
  - "shadcn/ui installed with dark theme: button, input, card base components"
  - "TypeScript API types: CVEResponse, BrowseListResponse, SyncStatusResponse, SortState"
  - "React Query hooks: useSearchCVE, useLatestCVEs, useSyncStatus"
  - "Reusable DataTable with sortable columns (CVE ID, CVSS, Published Date)"
  - "Testable Badge: green pill (testable) / gray pill (non-testable)"
  - "Navigation with active page detection via useLocation() + Keysight blue underline"
  - "StatusBar footer showing 'Data last updated: Xh ago' from useSyncStatus()"
  - "StaleDataWarning banner (>25h threshold, dismissible per session, yellow/amber)"
  - "App.tsx layout: QueryClientProvider → Navigation → StaleDataWarning → main → StatusBar"

affects: [04-02-PLAN, Phase 5 batch processing]

# Tech tracking
tech-stack:
  added:
    - "shadcn-ui@0.9.5 (CLI) + @radix-ui/react-slot, @radix-ui/react-dialog, @radix-ui/react-label"
    - "class-variance-authority (CVA) for button variants"
    - "clsx + tailwind-merge (cn() utility)"
    - "lucide-react (icon library)"
    - "@tanstack/react-query (already in package.json, now wired via QueryClientProvider)"
    - "axios (already in package.json, now used in hooks)"
  patterns:
    - "shadcn/ui components ship as local source code under src/components/ui/"
    - "cn() utility (clsx + tailwind-merge) used for conditional Tailwind class merging"
    - "React Query hooks centralized in src/hooks/useAPI.ts — one hook per API endpoint"
    - "Layout composition in App.tsx: persistent nav + conditional banner + flex-1 main + sticky footer"
    - "Dark theme hierarchy: bg-dark-900 (#0D1117) body, bg-dark-950 (#010409) nav/footer"

key-files:
  created:
    - "frontend/src/types/api.ts"
    - "frontend/src/hooks/useAPI.ts"
    - "frontend/src/components/shared/DataTable.tsx"
    - "frontend/src/components/shared/Badge.tsx"
    - "frontend/src/components/layout/Navigation.tsx"
    - "frontend/src/components/layout/StatusBar.tsx"
    - "frontend/src/components/layout/StaleDataWarning.tsx"
    - "frontend/src/components/ui/button.tsx"
    - "frontend/src/components/ui/input.tsx"
    - "frontend/src/components/ui/card.tsx"
    - "frontend/src/lib/utils.ts"
    - "frontend/components.json"
  modified:
    - "frontend/src/App.tsx"
    - "frontend/package.json"
    - "frontend/tsconfig.json"

key-decisions:
  - "Used relative imports (not @/ alias) in components — simpler setup without path alias config"
  - "Skipped deprecated shadcn-ui CLI interactive init; created components.json manually for dark theme"
  - "Extracted formatTimeSince() from StatusBar as pure function for testability"
  - "Navigation uses href (not Link from react-router) — preserves browser history without hydration issues"
  - "StaleDataWarning uses local useState for dismiss state (reappears on reload — matches requirement)"

patterns-established:
  - "Component files in src/components/{layout,shared,ui}/ directory structure"
  - "All API hooks in src/hooks/useAPI.ts with queryKey arrays for React Query cache keying"
  - "Dark theme: text-gray-200/300 for primary, text-gray-400/500 for secondary, text-white for emphasis"
  - "Table rows: hover:bg-gray-900, borders: border-gray-700, headers: bg-dark-950"

requirements-completed: [UI-01, UI-03, UI-04, SYNC-03, SYNC-04]

# Metrics
duration: 6min
completed: 2026-02-23
---

# Phase 4 Plan 01: Shared UI Infrastructure Summary

**React Query hooks, shadcn/ui dark theme components, and layout composition (Navigation + StaleDataWarning + StatusBar) wired into App.tsx — unblocks SearchPage and BrowsePage in Plan 02**

## Performance

- **Duration:** 6 minutes
- **Started:** 2026-02-23T18:17:13Z
- **Completed:** 2026-02-23T18:23:05Z
- **Tasks:** 9 (+ 1 refactor pass for documentation)
- **Files modified:** 14 (7 new components/hooks/types + 3 shadcn/ui base + 4 config/modified)

## Accomplishments

- Complete shared UI infrastructure established: 7 new functional files, 3 shadcn/ui base components
- React Query wired globally via QueryClientProvider in App.tsx with 3 domain hooks
- Layout contract locked: Navigation → StaleDataWarning → main content → StatusBar on every page
- Dark theme compliance: bg-dark-900 (#0D1117) body, dark-950 nav/footer, WCAG AA gray-200 text

## Component Inventory

| Component | File | Purpose |
|-----------|------|---------|
| DataTable | src/components/shared/DataTable.tsx | Sortable CVE table with loading/empty states |
| Badge | src/components/shared/Badge.tsx | Green/gray testable status pill |
| Navigation | src/components/layout/Navigation.tsx | Active-state nav with Keysight blue underline |
| StatusBar | src/components/layout/StatusBar.tsx | Footer sync timestamp "Xh ago" |
| StaleDataWarning | src/components/layout/StaleDataWarning.tsx | Dismissible >25h stale data banner |
| Button | src/components/ui/button.tsx | shadcn/ui button with dark variants |
| Input | src/components/ui/input.tsx | Dark-themed text input |
| Card | src/components/ui/card.tsx | Dark-themed card container |

## Hook Inventory

| Hook | queryKey | Endpoint | staleTime | refetchInterval |
|------|----------|----------|-----------|-----------------|
| useSearchCVE | ['cve', 'search', id] | GET /cve/search | 5min | — |
| useLatestCVEs | ['cve', 'latest', page, size, filter] | GET /cve/latest | 5min | — |
| useSyncStatus | ['sync', 'status'] | GET /admin/sync-status | 1min | 5min |

## Type Definitions

| Interface | Purpose |
|-----------|---------|
| CVEResponse | Full CVE data shape from Phase 3 backend |
| BrowseListResponse | Paginated CVE list with total/has_next |
| SyncStatusResponse | Cyperf sync timing with status union type |
| SortState | Column sort state for DataTable |
| SortDirection | 'asc' \| 'desc' \| null type alias |

## Task Commits

Each task was committed atomically:

1. **Task 1: Install shadcn/ui with dark theme** - `58ada8b` (feat)
2. **Task 2: TypeScript API types** - `e20eb01` (feat)
3. **Task 3: React Query hooks** - `3183dde` (feat)
4. **Task 4: DataTable component** - `fdc37fb` (feat)
5. **Task 5: Badge component** - `ebe1dbd` (feat)
6. **Task 6: Navigation component** - `124a21b` (feat)
7. **Task 7: StatusBar footer** - `c8f9eef` (feat)
8. **Task 8: StaleDataWarning banner** - `405b03a` (feat)
9. **Task 9: App.tsx layout composition** - `46c655c` (feat)
10. **Documentation pass** - `43fb7f6` (refactor)

## Files Created/Modified

- `frontend/src/types/api.ts` — TypeScript API response types (5 interfaces)
- `frontend/src/hooks/useAPI.ts` — 3 React Query hooks for CVE and sync API
- `frontend/src/components/shared/DataTable.tsx` — Sortable CVE table component
- `frontend/src/components/shared/Badge.tsx` — Green/gray testable status pill
- `frontend/src/components/layout/Navigation.tsx` — Active-state nav bar
- `frontend/src/components/layout/StatusBar.tsx` — Sync timestamp footer
- `frontend/src/components/layout/StaleDataWarning.tsx` — Stale data warning banner
- `frontend/src/components/ui/button.tsx` — shadcn/ui Button with dark theme
- `frontend/src/components/ui/input.tsx` — shadcn/ui Input with dark theme
- `frontend/src/components/ui/card.tsx` — shadcn/ui Card with dark theme
- `frontend/src/lib/utils.ts` — cn() utility (clsx + tailwind-merge)
- `frontend/components.json` — shadcn/ui configuration for dark mode
- `frontend/src/App.tsx` — Updated with QueryClientProvider + layout composition
- `frontend/package.json` — Added shadcn/ui and Radix UI runtime deps
- `frontend/tsconfig.json` — Fixed noEmit flag, added vite/client types

## Decisions Made

1. **Relative imports over @/ aliases** — Simpler setup without requiring path alias config in both tsconfig and vite.config.ts
2. **Manual components.json** — shadcn-ui CLI is deprecated; created config manually to avoid interactive init blocking
3. **href over React Router Link in Navigation** — Preserves standard browser history behavior without React Router hydration complexity for simple nav links
4. **formatTimeSince() as extracted pure function** — Easier to unit test independently from React component state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed tsconfig.json allowImportingTsExtensions conflict**
- **Found during:** Task 1 (first build attempt)
- **Issue:** `allowImportingTsExtensions: true` requires `noEmit: true` or `emitDeclarationOnly: true` — build failed with TS5096
- **Fix:** Added `"noEmit": true` to tsconfig.json compilerOptions; removed `outDir` (incompatible with noEmit). Vite handles its own output via `build.outDir` in vite.config.ts
- **Files modified:** `frontend/tsconfig.json`
- **Verification:** `npm run build` passes with `✓ built in 670ms`
- **Committed in:** `58ada8b` (Task 1 commit)

**2. [Rule 3 - Blocking] Added vite/client types for import.meta.env**
- **Found during:** Task 3 (useAPI.ts hook creation)
- **Issue:** `import.meta.env.VITE_API_URL` fails TypeScript check without `vite/client` in types array — error TS2339: Property 'env' does not exist on type 'ImportMeta'
- **Fix:** Added `"types": ["vite/client"]` to tsconfig.json compilerOptions
- **Files modified:** `frontend/tsconfig.json`
- **Verification:** `npm run build` passes after addition
- **Committed in:** `3183dde` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking issues)
**Impact on plan:** Both were pre-existing config gaps that blocked TypeScript compilation. No scope creep. All task implementations match plan spec exactly.

## Issues Encountered

- shadcn-ui@0.9.5 CLI is deprecated wrapper that outputs a redirect message — could not run `npx shadcn-ui@latest init`. Resolved by creating `components.json` manually and installing Radix UI dependencies directly. All shadcn/ui base components created as local source files (standard shadcn pattern).

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- Plan 02 (SearchPage + BrowsePage) can be built immediately using DataTable, Badge, useSearchCVE, useLatestCVEs
- All layout components (Navigation, StatusBar, StaleDataWarning) require zero changes for Plan 02
- TypeScript types (CVEResponse, BrowseListResponse) provide compile-time safety for page data binding
- React Query cache keys established — SearchPage and BrowsePage can invalidate/refetch without hook changes

---
*Phase: 04-frontend-ui*
*Completed: 2026-02-23*

## Self-Check: PASSED

- All 13 files found on disk
- All 10 task commits verified in git history
- `npm run build` completes: ✓ built in 977ms (0 TypeScript errors)
