# Phase 4: Frontend UI - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

---

<domain>
## Phase Boundary

Build a React single-page application where users can search for CVEs, browse latest CVEs with filters, and view testability status (whether Cyperf can test them). All within a dark theme inspired by Shodan.io with Keysight branding accents.

Scope: Frontend only. Backend API (Phase 2) and Cyperf sync (Phase 3) are separate phases. Batch processing is Phase 5.

</domain>

---

<decisions>
## Implementation Decisions

### Dark Theme & Visual Design
- **Palette**: Shodan.io inspired (dark gray backgrounds, light text) with Keysight accent colors (blue/red)
- **Background**: #0D1117 or equivalent dark gray
- **Primary Text**: #E0E0E0 (light gray)
- **Accent Colors**: Keysight blue for interactive elements, Keysight red for alerts
- **Testable Badge**: Solid green (#22C55E) for testable, muted gray (#9CA3AF) for non-testable
- **Contrast**: WCAG AA minimum (4.5:1 for body text)
- **Font**: Monospace/semi-mono for CVE IDs, sans-serif for body
- **Components**: shadcn/ui with Tailwind dark mode

### Search & Browse Layouts
- **Format**: Data table (compact, rows with columns)
- **Columns**: CVE ID, CVSS Score, Published Date, Testable Badge
- **Sorting**: Ascending/descending on CVE ID, CVSS, Published Date (click column header)
- **Search Results**: Table view with same columns as browse
- **Pagination**: Implement pagination (not infinite scroll) for browse and search results
- **Rows per page**: 25 rows default (user can change)

### Navigation & Page Structure
- **Pattern**: Single-page app (React Router v6)
- **Main Pages**: Search, Browse, Batch (3 top-level pages)
- **Nav Location**: Top navigation bar (tab-like, persistent)
- **Active State**: Current page highlighted/underlined in nav
- **Browser Back Button**: Works via React Router (browser back/forward)
- **Responsive**: Hamburger menu on mobile, full nav on desktop

### Status Indicators & Warnings
- **Last Updated**: "Data last updated: X hours ago" in footer (subtle, always visible)
- **Stale Warning**: Banner at top of page if Cyperf sync >25 hours old
  - Color: Yellow/amber background with dark text (not intrusive but noticeable)
  - Text: "Cyperf data is outdated (last sync X hours ago). Some testability badges may be inaccurate."
  - Dismissible: User can close banner but it reappears on page reload
- **Manual Sync**: Optional: Show a "Refresh data" button for admins

### Claude's Discretion
- Exact component library choices (shadcn vs others)
- Animation and transition timings
- Mobile breakpoints and responsive behavior details
- Form validation and error messages for search input
- Loading skeleton designs for tables
- Accessibility implementation (keyboard nav, aria labels)

</decisions>

---

<specifics>
## Specific Ideas

- **Shodan Aesthetic**: The dark theme should evoke Shodan.io's "security researcher tool" feel — professional, minimalist, no unnecessary colors
- **No Flashy Animations**: Keep transitions subtle. This is a security tool, not a consumer app
- **Fast and Direct**: Users should find/filter CVEs quickly. No hidden features or surprise interactions
- **Keysight Branding**: Blue accents for call-to-action buttons (Search, Filter). Red for warnings only
- **Monospace for CVE IDs**: CVE-2024-1234 should render in a monospace font for clarity

</specifics>

---

<deferred>
## Deferred Ideas

- **Advanced Search Filters**: Full-text search, date range picker, severity ranges (Phase 5+)
- **User Accounts & Saved Searches**: Login, bookmarks, saved search history (Phase 6+)
- **Dark/Light Mode Toggle**: Dark theme only for v1; light mode is Phase 6+
- **Export to PDF**: Batch export feature (different from CSV export in Phase 5)
- **Real-time Notifications**: New CVE alerts (Phase 6+, requires backend changes)

</deferred>

---

*Phase: 04-frontend-ui*
*Context gathered: 2026-02-23*
*Decision mode: User-directed (user made all 4 design decisions)*
