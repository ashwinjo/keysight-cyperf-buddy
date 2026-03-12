---
phase: 07-frontend-l4-7-test-advisor-ui-tab-to-submit-test-scenarios-and-display-agent-recommendations
plan: 02
subsystem: ui
tags: [react, typescript, tailwind, luxury-theme, navigation, react-query]

# Dependency graph
requires:
  - phase: 07-01
    provides: useGetL47Recommendations hook, L47ScenarioRequest/L47RecommendationResponse types
provides:
  - L47ScenarioForm component with client validation and mutation invocation
  - L47AdvisorPage two-state page (form → ranked results)
  - /l47-advisor route registered in App.tsx
  - AI Tools nav group in Navigation.tsx linking /ashrai-assistant and /l47-advisor
affects:
  - Navigation.tsx (AI Tools group visible on all pages)
  - App.tsx (new route available)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dark luxury-* theme exclusively — no bg-white, bg-gray-*, from-gray-* classes"
    - "card-luxury wrapper for form and result panels"
    - "Manual useState form state (same pattern as QuestionnaireForm, without shadcn/ui deps)"
    - "profileTypeBadge map for application (blue) vs strike (red) badge coloring"

key-files:
  created:
    - frontend/src/components/L47ScenarioForm.tsx
    - frontend/src/pages/L47AdvisorPage.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/layout/Navigation.tsx

key-decisions:
  - "NAV_STRUCTURE group entry for AI Tools inserted before What is Cyperf — no type changes needed, existing group rendering handles it"
  - "L47ScenarioForm uses plain <select>/<textarea>/<input> with luxury-* classes rather than shadcn/ui Input — avoids light-theme default styles from shadcn components"
  - "border-t-transparent spinner pattern (not border-transparent border-t-luxury-accent) to match spinner variant used in plan spec"

requirements-completed:
  - L47-UI-03
  - L47-UI-04
  - L47-UI-05

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 7 Plan 02: L4-7 Test Advisor UI Components Summary

**L47ScenarioForm (4-field controlled form) and L47AdvisorPage (form/results two-state page) built with dark luxury-* theme; /l47-advisor route registered and AI Tools nav group added**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T05:44:18Z
- **Completed:** 2026-03-12T05:46:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `frontend/src/components/L47ScenarioForm.tsx` — controlled form with testing_focus select (app_performance/security_attacks/both), use_case and objectives textareas (min 10 chars), timeline input (min 5 chars); client validation with dark red-900/30 error banners; animate-spin spinner on pending; calls useGetL47Recommendations on submit
- Created `frontend/src/pages/L47AdvisorPage.tsx` — two-state page: form wrapped in card-luxury, results with ranked cards (rank number in luxury-accent, profile_name, profile_type badge with blue for application / red for strike, rationale text); empty recommendations renders agent message + Try Again; non-empty shows up to 3 cards + Start Over link
- Modified `frontend/src/App.tsx` — imported L47AdvisorPage, registered Route path="/l47-advisor" after /ashrai-assistant
- Modified `frontend/src/components/layout/Navigation.tsx` — added AI Tools group (AshRAI + L4-7 Advisor) before What is Cyperf in NAV_STRUCTURE
- Zero TypeScript errors after both tasks
- Production build exits cleanly (npm run build — 1.41s)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create L47ScenarioForm.tsx and L47AdvisorPage.tsx** - `252b1a0` (feat)
2. **Task 2: Wire /l47-advisor route and add AI Tools nav group** - `fe6e87c` (feat)

## Files Created/Modified

- `frontend/src/components/L47ScenarioForm.tsx` - 4-field controlled form with dark luxury-* theme, client validation, loading spinner
- `frontend/src/pages/L47AdvisorPage.tsx` - Two-state page: form panel and ranked recommendation cards
- `frontend/src/App.tsx` - L47AdvisorPage import + /l47-advisor route
- `frontend/src/components/layout/Navigation.tsx` - AI Tools nav group with AshRAI and L4-7 Advisor children

## Decisions Made

- NAV_STRUCTURE group entry for AI Tools inserted before What is Cyperf — the existing NavEntry union type and group rendering logic handled it without any type changes
- L47ScenarioForm uses plain `<select>/<textarea>/<input>` with luxury-* classes rather than shadcn/ui Input — avoids light-theme default styles that shadcn components apply; consistent with dark theme requirement
- border-t-transparent spinner pattern matches plan spec exactly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — both files created and both existing files modified cleanly. Zero TypeScript errors, production build exits 0.

## User Setup Required

None — no new dependencies, environment variables, or external service configuration. The agent service on port 8001 must be running (docker compose) for form submissions to reach the Phase 6 agent, but no new setup is required for this plan.

## Self-Check: PASSED

All created files verified on disk. Both task commits confirmed in git log.

---
*Phase: 07-frontend-l4-7-test-advisor-ui-tab-to-submit-test-scenarios-and-display-agent-recommendations*
*Completed: 2026-03-12*
