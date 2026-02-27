---
phase: quick-11
plan: 11
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/shared/SearchBox.tsx
  - frontend/src/components/pages/SearchForm.tsx
  - frontend/src/pages/CyperfAppsPage.tsx
  - frontend/src/pages/CyperfAppTypesPage.tsx
autonomous: true
requirements: [QUICK-11]

must_haves:
  truths:
    - "All three search surfaces show a labelled title above the input"
    - "The input field spans full width of its container"
    - "A stats/summary line appears directly below the input, not above it"
    - "SearchBox is a single reusable component imported by all three callers"
    - "CyperfAppsPage and CyperfAppTypesPage search input is always visible (not conditionally mounted on data load)"
  artifacts:
    - path: "frontend/src/components/shared/SearchBox.tsx"
      provides: "Reusable SearchBox with label, full-width input, optional stats slot"
      exports: ["SearchBox", "SearchBoxProps"]
    - path: "frontend/src/components/pages/SearchForm.tsx"
      provides: "CVE ID search form using SearchBox"
      contains: "SearchBox"
    - path: "frontend/src/pages/CyperfAppsPage.tsx"
      provides: "Apps page using SearchBox with stats below input"
      contains: "SearchBox"
    - path: "frontend/src/pages/CyperfAppTypesPage.tsx"
      provides: "App Types page using SearchBox with stats below input"
      contains: "SearchBox"
  key_links:
    - from: "frontend/src/components/pages/SearchForm.tsx"
      to: "frontend/src/components/shared/SearchBox.tsx"
      via: "named import"
      pattern: "import.*SearchBox.*from.*shared/SearchBox"
    - from: "frontend/src/pages/CyperfAppsPage.tsx"
      to: "frontend/src/components/shared/SearchBox.tsx"
      via: "named import"
      pattern: "import.*SearchBox.*from.*shared/SearchBox"
    - from: "frontend/src/pages/CyperfAppTypesPage.tsx"
      to: "frontend/src/components/shared/SearchBox.tsx"
      via: "named import"
      pattern: "import.*SearchBox.*from.*shared/SearchBox"
---

<objective>
Create a reusable SearchBox component matching the reference design (title label, full-width input, stats section below), then migrate SearchForm, CyperfAppsPage, and CyperfAppTypesPage to use it.

Purpose: Eliminate three divergent ad-hoc search implementations. CyperfAppsPage/AppTypesPage currently render stats ABOVE the input and constrain input width to max-w-md. SearchForm has no label and no stats slot. All three should be visually consistent.

Output: One new shared component; three updated callers with identical search UX.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Stack: React 18 + Vite + Tailwind + shadcn/ui. Luxury dark theme tokens: `text-luxury-text`, `text-luxury-text-secondary`, `text-luxury-accent`, `text-luxury-accent/70`, `card-luxury`, `input-luxury`, `btn-luxury-primary`, `tracking-luxury`, `bg-luxury-bg`, `bg-luxury-bg-subtle`, `border-luxury-border`. shadcn `Input` component lives at `frontend/src/components/ui/input.tsx`.

Existing callers to migrate:
- `frontend/src/components/pages/SearchForm.tsx` — standalone form, no SearchBox yet
- `frontend/src/pages/CyperfAppsPage.tsx` — bare shadcn Input, max-w-md, stats above input
- `frontend/src/pages/CyperfAppTypesPage.tsx` — identical pattern to CyperfAppsPage
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create SearchBox shared component</name>
  <files>frontend/src/components/shared/SearchBox.tsx</files>
  <action>
Create `frontend/src/components/shared/SearchBox.tsx` as a new file. Export a named `SearchBox` component and its `SearchBoxProps` interface.

Props interface:
```ts
interface SearchBoxProps {
  label: string;               // Title shown above input (e.g. "Search CVEs", "Filter Applications")
  placeholder?: string;        // Input placeholder text
  value: string;               // Controlled value
  onChange: (value: string) => void;
  onSubmit?: () => void;       // If provided, render a submit button; otherwise pure filter mode
  isLoading?: boolean;         // Disables input and shows loading text on button
  submitLabel?: string;        // Button text when idle (default: "Search")
  stats?: React.ReactNode;     // Optional stats/summary content rendered below the input row
  error?: string;              // Validation error shown below stats
  className?: string;
}
```

Layout (render order, top to bottom):
1. `<p>` label — `text-xs tracking-luxury uppercase text-luxury-accent/70 font-semibold mb-3`
2. Input row — `flex gap-3 items-center` containing:
   - `<input>` (not shadcn Input — use plain input with `input-luxury` class for styling consistency with SearchForm): `className="input-luxury flex-1"`, `type="text"`, `disabled={isLoading}`, `value`, `onChange={(e) => onChange(e.target.value)}`. On `onSubmit`, attach `onKeyDown` to fire on Enter key as well.
   - If `onSubmit` provided: `<button type="button" onClick={onSubmit} disabled={isLoading} className="btn-luxury-primary disabled:opacity-50 disabled:cursor-not-allowed">{isLoading ? 'Searching...' : (submitLabel ?? 'Search')}</button>`
3. Stats slot (if `stats` provided) — `<div className="mt-3">{stats}</div>`
4. Error (if `error` provided) — `<p className="mt-3 text-sm text-red-400 font-medium tracking-tight px-4 py-3 bg-red-900/20 border border-red-900/50 rounded">⚠ {error}</p>`

Wrap entire component in `<div className={cn("card-luxury", className)}>`. Import `cn` from `"../../lib/utils"` (existing shadcn utility).

The component must NOT manage its own state — it is fully controlled. Callers own query/error state.
  </action>
  <verify>
`cd /Users/ashwin.joshi/claudeExp/frontend && npx tsc --noEmit 2>&1 | head -30`

No TypeScript errors for the new file.
  </verify>
  <done>
`frontend/src/components/shared/SearchBox.tsx` exists and exports `SearchBox` and `SearchBoxProps`. TypeScript compiles cleanly. Component renders: label, full-width input, optional submit button, optional stats below, optional error below stats.
  </done>
</task>

<task type="auto">
  <name>Task 2: Migrate SearchForm, CyperfAppsPage, and CyperfAppTypesPage to SearchBox</name>
  <files>
    frontend/src/components/pages/SearchForm.tsx
    frontend/src/pages/CyperfAppsPage.tsx
    frontend/src/pages/CyperfAppTypesPage.tsx
  </files>
  <action>
**SearchForm.tsx** — Replace the current `<form>` with SearchBox:
- Keep existing `input` state, `error` state, `validateCVEID`, and `handleSubmit` logic unchanged.
- Remove the `<form>` wrapper and the inline `<input>` + `<button>` + error `<p>`.
- Render: `<SearchBox label="Search CVEs" placeholder="e.g., CVE-2024-1234" value={input} onChange={(v) => { setInput(v); if (error) setError(''); }} onSubmit={handleSubmit} isLoading={isLoading} submitLabel="Search" error={error} />`
- `handleSubmit` no longer needs to call `e.preventDefault()` — remove the `React.FormEvent` parameter and make it a plain `() => void` function since SearchBox calls it via button onClick / Enter keyDown, not a form submit event.
- Drop the `import` for anything no longer used.

**CyperfAppsPage.tsx** — Replace the bare Input and separate stats card with SearchBox:
- Remove `import { Input } from '../components/ui/input'`.
- Add `import { SearchBox } from '../components/shared/SearchBox'`.
- Remove the existing `{/* Stats */}` card-luxury block and the `{/* Search input */}` conditional block entirely.
- After the error block and before the table, render a single SearchBox unconditionally (always visible, not gated on `apps && apps.length > 0`):

```tsx
<SearchBox
  label="Filter Applications"
  placeholder="Filter by name or description..."
  value={query}
  onChange={setQuery}
  stats={
    !isLoading && !isError ? (
      <p className="text-sm font-semibold text-luxury-accent">
        {query.trim()
          ? `${filtered.length} of ${apps?.length || 0} applications`
          : `${apps?.length || 0} applications`}
      </p>
    ) : undefined
  }
/>
```

The stats content appears inside SearchBox below the input. No separate stats card-luxury block should remain.

**CyperfAppTypesPage.tsx** — Apply the identical migration as CyperfAppsPage but for app types:
- Remove `import { Input }`.
- Add `import { SearchBox }`.
- Remove existing stats card block and search input conditional block.
- Render unconditional SearchBox after error block:

```tsx
<SearchBox
  label="Filter Application Types"
  placeholder="Filter by name or description..."
  value={query}
  onChange={setQuery}
  stats={
    !isLoading && !isError ? (
      <p className="text-sm font-semibold text-luxury-accent">
        {query.trim()
          ? `${filtered.length} of ${appTypes?.length || 0} application types`
          : `${appTypes?.length || 0} application types`}
      </p>
    ) : undefined
  }
/>
```

Do NOT change the table rendering logic, empty state messages, loading state, or error state in either page. Only replace the search input + stats section.
  </action>
  <verify>
`cd /Users/ashwin.joshi/claudeExp/frontend && npx tsc --noEmit 2>&1 | head -30`

No TypeScript errors. Then `npm run dev` starts without errors (check process output for compilation errors).

Manual checks in browser:
1. SearchPage — input is full width inside card-luxury, label "Search CVEs" visible above input, submit button present, error shown below on bad CVE format.
2. CyperfAppsPage — SearchBox always visible (not waiting for data), stats line appears below input showing count, no separate stats card above.
3. CyperfAppTypesPage — same as Apps page with "Filter Application Types" label.
  </verify>
  <done>
All three files import SearchBox and render it. No remaining bare `&lt;Input&gt;` from shadcn in any of the three files. Stats section is always below the input, not above. TypeScript compiles with zero new errors.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

1. `grep -r "from.*shared/SearchBox" /Users/ashwin.joshi/claudeExp/frontend/src` — returns 3 matches (SearchForm, CyperfAppsPage, CyperfAppTypesPage).
2. `grep -n "max-w-md" /Users/ashwin.joshi/claudeExp/frontend/src/pages/CyperfAppsPage.tsx` — returns no matches (width constraint removed).
3. `grep -n "max-w-md" /Users/ashwin.joshi/claudeExp/frontend/src/pages/CyperfAppTypesPage.tsx` — returns no matches.
4. TypeScript: `cd /Users/ashwin.joshi/claudeExp/frontend && npx tsc --noEmit` — exits 0.
</verification>

<success_criteria>
- `frontend/src/components/shared/SearchBox.tsx` exists with label + full-width input + stats slot below + error slot.
- `SearchForm.tsx` uses SearchBox (no bare form element or inline input).
- `CyperfAppsPage.tsx` uses SearchBox; stats count appears below input; input always rendered.
- `CyperfAppTypesPage.tsx` uses SearchBox; stats count appears below input; input always rendered.
- TypeScript compiles cleanly across all four files.
- No `max-w-md` constraint on the search inputs in Apps or AppTypes pages.
</success_criteria>

<output>
After completion, create `.planning/quick/11-standardize-all-search-boxes-to-match-re/11-SUMMARY.md` with:
- What was built (SearchBox component + 3 callers migrated)
- Any implementation decisions made
- Verification results
</output>
