# Phase 7: Frontend L4-7 Test Advisor UI - Research

**Researched:** 2026-03-11
**Domain:** React/TypeScript frontend — form submission, async mutation, results display, dark theme integration
**Confidence:** HIGH (all stack choices verified against existing codebase; API contract confirmed from agent-service/models.py)

---

## Summary

Phase 7 adds a new page to the CyperfBuddy React frontend that allows users to submit L4-7 test scenarios (four fields: testing_focus, use_case, objectives, timeline) to the Phase 6 agent service at `POST /api/l47/recommend` (agent container on port 8001) and displays the ranked recommendations returned (up to 3, each with rank, profile_name, profile_type, rationale). The backend contract is fixed and fully implemented: `agent-service/models.py` defines the exact Pydantic schemas used at runtime.

The key integration challenge is **proxy routing**: the Vite dev proxy at `/api` currently points exclusively to `http://localhost:8000` (the main backend). The agent service runs on port `8001`. A new proxy entry `/api/l47` → `http://localhost:8001` must be added to `vite.config.ts` and the nginx production config must forward `/api/l47/` to `http://agent:8001`. Without this, all agent requests will hit the main backend and return 404.

The page follows the exact same pattern as `AshAiAssistantPage.tsx` + `QuestionnaireForm.tsx`: controlled form state, `useMutation` hook in `useAPI.ts`, results rendered after successful mutation. The dark theme is fully defined via Tailwind utility classes (`luxury-*` tokens). No new dependencies are needed; the existing stack (React Query, axios, shadcn/ui components, Tailwind) covers all requirements.

**Primary recommendation:** Mirror the AshRAI page structure — new `L47AdvisorPage.tsx` + `L47ScenarioForm.tsx` + `useGetL47Recommendations` mutation hook — then wire the Vite proxy and nginx before adding the nav link. Verify proxy routing before any UI work to avoid silent 404s during development.

---

## API Contract (Phase 6 — CONFIRMED)

The agent service is complete. These schemas are the source of truth (from `agent-service/models.py`):

### Request: `POST /api/l47/recommend`
```
{
  "testing_focus": "app_performance" | "security_attacks" | "both",
  "use_case": string (10–1000 chars, required),
  "objectives": string (10–1000 chars, required),
  "timeline": string (5–200 chars, required)
}
```

### Response: `L47RecommendationResponse`
```
{
  "success": boolean,
  "message": string,
  "recommendations": [
    {
      "rank": integer,         // 1, 2, 3
      "profile_name": string,
      "profile_type": "application" | "strike",
      "rationale": string      // 2-3 sentences
    }
  ]
}
```

**Key differences from AshRAI:**
- No `next_steps` field (AshRAI has it; L4-7 does not)
- No `priority` / `category` fields on recommendations (L4-7 uses `rank` + `profile_type` instead)
- `testing_focus` values are snake_case: `app_performance`, `security_attacks`, `both` (not "Application Profile")
- Four required fields — no conditional field logic based on focus type (all four always required)
- Agent always returns HTTP 200, never 4xx/5xx (graceful degradation built into agent service)

---

## Standard Stack

No new dependencies required. All libraries are already installed.

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 | 18.x | UI rendering | Project standard |
| TypeScript | 5.x | Type safety | Project standard |
| TanStack React Query | 5.x | Async data fetching, mutation state | Already used for all API calls (useMutation pattern) |
| axios | 1.x | HTTP client | Already used in all hooks; error normalization pattern exists |
| Tailwind CSS | 3.x | Styling | Project standard; `luxury-*` tokens defined |
| shadcn/ui (Button, Input, Card) | Current | UI primitives | Already installed; used in QuestionnaireForm |
| React Router v6 | 6.x | Routing | Already configured in App.tsx |

### No New Dependencies
The AshRAI page demonstrates the full pattern without any extra libraries. Do not add:
- React Hook Form + Zod (already used in contact form, but AshRAI uses manual state — stay consistent with AshRAI pattern for this simpler 4-field form)
- Any animation or skeleton library (not used elsewhere on data pages)

**Installation:** None required.

---

## Architecture Patterns

### Recommended File Structure (new files only)
```
frontend/src/
├── pages/
│   └── L47AdvisorPage.tsx          # Page component (mirrors AshAiAssistantPage.tsx)
├── components/
│   └── L47ScenarioForm.tsx         # Form component (mirrors QuestionnaireForm.tsx)
└── hooks/
    └── useAPI.ts                   # Add useGetL47Recommendations mutation here
```

```
frontend/
└── vite.config.ts                  # Add /api/l47 proxy entry

nginx.conf                          # Add /api/l47/ proxy_pass to agent:8001

frontend/src/
└── App.tsx                         # Add <Route path="/l47-advisor" element={<L47AdvisorPage />} />

frontend/src/components/layout/
└── Navigation.tsx                  # Add nav link to /l47-advisor
```

### Pattern 1: React Query Mutation Hook for Agent Call

The exact pattern from `useGetRecommendations` in `useAPI.ts` applies here. Add alongside existing hooks:

```typescript
// In frontend/src/hooks/useAPI.ts — add these types and hook

export interface L47ScenarioRequest {
  testing_focus: 'app_performance' | 'security_attacks' | 'both';
  use_case: string;
  objectives: string;
  timeline: string;
}

export interface L47Recommendation {
  rank: number;
  profile_name: string;
  profile_type: 'application' | 'strike';
  rationale: string;
}

export interface L47RecommendationResponse {
  success: boolean;
  message: string;
  recommendations: L47Recommendation[];
}

export const useGetL47Recommendations = () => {
  return useMutation({
    mutationFn: async (scenario: L47ScenarioRequest) => {
      try {
        // NOTE: /api/l47 proxied to agent service (port 8001) via Vite proxy
        const res = await axios.post<L47RecommendationResponse>(
          '/api/l47/recommend',
          scenario
        );
        return res.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          const detail = err.response.data?.detail;
          let message: string;
          if (typeof detail === 'string') {
            message = detail;
          } else if (Array.isArray(detail)) {
            message = detail
              .map((d: { loc?: unknown[]; msg?: string }) => {
                const loc = (d.loc ?? [])
                  .filter((part) => part !== 'body')
                  .join(' -> ');
                return loc ? `${loc}: ${d.msg ?? 'invalid value'}` : (d.msg ?? 'invalid value');
              })
              .join('; ');
          } else {
            message = `Request failed with status ${err.response.status}`;
          }
          throw new Error(message);
        }
        throw err;
      }
    },
  });
};
```

**Source:** Existing pattern in `frontend/src/hooks/useAPI.ts` — `useGetRecommendations` hook

### Pattern 2: Form Component with Controlled State

The form has 4 always-required fields. No conditional fields (unlike AshRAI). Use controlled state + simple client validation:

```typescript
// frontend/src/components/L47ScenarioForm.tsx
import React, { useState } from 'react';
import { useGetL47Recommendations, type L47ScenarioRequest } from '../hooks/useAPI';
import { Button } from './ui/button';

type TestingFocus = 'app_performance' | 'security_attacks' | 'both';

interface L47ScenarioFormProps {
  onSubmit?: (response: L47RecommendationResponse) => void;
}

export const L47ScenarioForm: React.FC<L47ScenarioFormProps> = ({ onSubmit }) => {
  const [testingFocus, setTestingFocus] = useState<TestingFocus>('app_performance');
  const [useCase, setUseCase] = useState('');
  const [objectives, setObjectives] = useState('');
  const [timeline, setTimeline] = useState('');
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const mutation = useGetL47Recommendations();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationErrors([]);

    const errors: string[] = [];
    if (useCase.trim().length < 10) errors.push('Use case must be at least 10 characters');
    if (objectives.trim().length < 10) errors.push('Objectives must be at least 10 characters');
    if (timeline.trim().length < 5) errors.push('Timeline must be at least 5 characters');

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    const request: L47ScenarioRequest = {
      testing_focus: testingFocus,
      use_case: useCase.trim(),
      objectives: objectives.trim(),
      timeline: timeline.trim(),
    };

    mutation.mutate(request, {
      onSuccess: (data) => onSubmit?.(data),
      onError: () => {},
    });
  };
  // ... form JSX using luxury-* Tailwind tokens
};
```

### Pattern 3: Page Component — Two-State (Form / Results)

Mirror `AshAiAssistantPage.tsx` state machine: `showForm` boolean drives which panel renders.

```typescript
// frontend/src/pages/L47AdvisorPage.tsx
import React, { useState } from 'react';
import { L47ScenarioForm } from '../components/L47ScenarioForm';
import { type L47RecommendationResponse } from '../hooks/useAPI';

export const L47AdvisorPage: React.FC = () => {
  const [result, setResult] = useState<L47RecommendationResponse | null>(null);

  if (!result) {
    return (
      <div className="space-y-8 animate-in">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-display font-bold text-luxury-text mb-2 tracking-luxury">
            L4-7 Test Advisor
          </h1>
          <p className="text-luxury-text-secondary tracking-tight">
            Describe your test scenario — get ranked Cyperf profile recommendations
          </p>
        </div>
        {/* Form card */}
        <div className="card-luxury">
          <L47ScenarioForm onSubmit={setResult} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in">
      {/* Results view */}
      {/* ... ranked recommendation cards + reset button */}
    </div>
  );
};
```

### Pattern 4: Recommendation Display — Ranked Cards

The `L47Recommendation` type has `rank`, `profile_name`, `profile_type`, `rationale`. Display as rank-ordered cards with `profile_type` badge (application vs strike).

```typescript
// Inline in L47AdvisorPage.tsx results section
const profileTypeBadge = {
  application: 'bg-blue-900/40 text-blue-300 border border-blue-700/40',
  strike: 'bg-red-900/40 text-red-300 border border-red-700/40',
};

{result.recommendations.map((rec) => (
  <div key={rec.rank} className="card-luxury space-y-3">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-2xl font-display font-bold text-luxury-accent">
          #{rec.rank}
        </span>
        <span className="text-lg font-semibold text-luxury-text">
          {rec.profile_name}
        </span>
      </div>
      <span className={`text-xs font-semibold px-3 py-1 rounded-full ${profileTypeBadge[rec.profile_type]}`}>
        {rec.profile_type}
      </span>
    </div>
    <p className="text-luxury-text-secondary text-sm leading-relaxed">
      {rec.rationale}
    </p>
  </div>
))}
```

### Pattern 5: Proxy Configuration — CRITICAL

The Vite dev proxy currently routes ALL `/api/*` to `http://localhost:8000`. The agent endpoint is `/api/l47/recommend` on port 8001. Vite applies proxy rules in definition order — the more specific `/api/l47` rule MUST come before the generic `/api` rule:

```typescript
// vite.config.ts — add BEFORE the existing /api entry
proxy: {
  '/api/l47': {
    target: 'http://localhost:8001',
    changeOrigin: true,
    // No rewrite needed: agent expects /api/l47/recommend at its own root
  },
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
  '/admin': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
},
```

**IMPORTANT:** The existing `/api` entry strips the `/api` prefix (via `rewrite`). The agent expects to receive the full path `/api/l47/recommend`. The `/api/l47` proxy entry must NOT use the same rewrite, or it will send `/l47/recommend` to the agent and get 404. Verify the agent's actual route registration in `agent-service/main.py`: route is `@app.post("/api/l47/recommend")` — so the agent expects the path WITH `/api/l47/recommend`.

For **production nginx**, add BEFORE the generic `/api/` block:
```nginx
location /api/l47/ {
    proxy_pass http://agent:8001/api/l47/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Pattern 6: Navigation Integration

Add as a standalone link in `NAV_STRUCTURE` in `Navigation.tsx`. Based on existing structure, it could go as a standalone link or nested under a new "AI Tools" group alongside the `/ashrai-assistant` route (which is currently not in nav). Research shows `/ashrai-assistant` is also missing from the NAV_STRUCTURE array — consider whether to add both routes or just the L4-7 advisor.

```typescript
// Option A: Standalone link (simple)
{ type: 'link', path: '/l47-advisor', label: 'L4-7 Advisor' }

// Option B: New "AI Tools" group with AshRAI
{
  type: 'group',
  label: 'AI Tools',
  children: [
    { path: '/ashrai-assistant', label: 'AshRAI' },
    { path: '/l47-advisor', label: 'L4-7 Advisor' },
  ],
}
```

Option B is recommended since AshRAI is already deployed but not in the nav — grouping both is cleaner.

### Anti-Patterns to Avoid

- **Using the same `/api` Vite proxy for agent calls without adding `/api/l47` first:** Requests will silently hit the main backend (port 8000) and return 404.
- **Adding `rewrite` to the `/api/l47` proxy entry:** The agent's route is `/api/l47/recommend` — no prefix stripping needed. Stripping breaks it.
- **Copying AshRAI's `testing_focus` display values (`'Application Profile'`, `'Security / Attacks'`):** The L4-7 agent uses snake_case values (`app_performance`, `security_attacks`, `both`). Sending wrong values causes 422 validation failure.
- **Expecting `next_steps` in the response:** L4-7 response has no `next_steps`. Accessing it will return `undefined`.
- **Rendering priority/category badges from L4-7 response:** The L4-7 `Recommendation` type has no `priority` or `category` — only `rank`, `profile_name`, `profile_type`, `rationale`.
- **Checking `result.success` to guard rendering:** Agent always returns `success: true` with empty recommendations array on failures. Guard on `result.recommendations.length > 0` instead.
- **Using light-theme CSS classes (bg-white, text-gray-*):** All pages use `luxury-*` Tailwind tokens. `AshAiAssistantPage.tsx` currently has light theme classes — this is an inconsistency. Phase 7 page MUST use dark theme tokens.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async mutation state management | Custom useState for loading/error/data | `useMutation` from React Query | Handles pending/error/success states, re-render on status change, automatic cleanup |
| HTTP error normalization | Custom try/catch per component | Error transform in `useGetL47Recommendations` hook (copy from `useGetRecommendations`) | Centralizes 422 detail flattening; prevents object-in-JSX render errors |
| Form validation | Zod schema + React Hook Form | Manual `errors: string[]` state (same as AshRAI) | AshRAI precedent; 4-field form is simple enough; avoids library inconsistency |
| Loading spinner | Custom CSS animation | `animate-spin` Tailwind utility (copy from CyperfAppsPage) | Already in project; consistent |
| Rank badge / profile type badge | Custom styled component | Inline Tailwind conditional class map | All existing pages use this pattern |

**Key insight:** The AshRAI implementation is the exact template. Copy its structure and adapt the field names and types. Do not introduce new patterns.

---

## Common Pitfalls

### Pitfall 1: Proxy Order in vite.config.ts
**What goes wrong:** Agent requests route to main backend (port 8000) and return 404. No obvious error — just an empty-looking 404 from FastAPI.
**Why it happens:** Vite applies proxy rules in definition order. The existing `/api` rule with `rewrite` catches all `/api/*` before `/api/l47` can match.
**How to avoid:** Add `/api/l47` proxy entry ABOVE the existing `/api` entry. Verify by checking response header `x-forwarded-host` or watching agent container logs.
**Warning signs:** Dev console shows 404 on `POST /api/l47/recommend`; main backend logs show the request arriving at port 8000.

### Pitfall 2: Wrong testing_focus Values
**What goes wrong:** Form sends `'Application Profile'` (AshRAI style) instead of `'app_performance'` (L4-7 style). Agent returns 422.
**Why it happens:** Copy-paste from `QuestionnaireForm.tsx` without updating the enum values.
**How to avoid:** The agent Pydantic model accepts exactly: `"app_performance"`, `"security_attacks"`, `"both"`. Define the TypeScript union type to match, and use a display label map for the UI.
**Warning signs:** 422 on submit with message about `testing_focus` field.

### Pitfall 3: Missing objectives and timeline Fields
**What goes wrong:** Form does not include `objectives` or `timeline` fields (only `use_case` and `testing_focus` like AshRAI). Agent returns 422 with "field required" for missing fields.
**Why it happens:** AshRAI only has `use_case`, not `objectives`/`timeline`. Developer copies form structure without reading the L4-7 schema.
**How to avoid:** All four fields (`testing_focus`, `use_case`, `objectives`, `timeline`) are required by the agent Pydantic model. Confirm against `agent-service/models.py`.
**Warning signs:** 422 on submit listing `objectives` or `timeline` as missing.

### Pitfall 4: Light Theme Classes on New Page
**What goes wrong:** New page renders with white background (`bg-white`, `bg-gray-50`) and dark text — jarring inconsistency with all other pages in the dark-themed app.
**Why it happens:** `AshAiAssistantPage.tsx` already has this bug (uses `bg-gradient-to-b from-gray-50 to-white`). Developer copies it.
**How to avoid:** Use `luxury-*` tokens throughout: `bg-luxury-bg`, `text-luxury-text`, `text-luxury-text-secondary`, `border-luxury-border`, `card-luxury` CSS class.
**Warning signs:** Page renders with visible white/light background in the dark-themed app.

### Pitfall 5: Agent Service Not Running Locally
**What goes wrong:** Dev proxy correctly routes to `http://localhost:8001`, but agent is not running locally. All requests fail with connection refused.
**Why it happens:** `start.sh` may not start the agent service; developer only ran the main backend and Vite.
**How to avoid:** During development, either run `docker compose up agent` or run the agent locally: `cd agent-service && uvicorn main:app --port 8001`. Verify with `curl http://localhost:8001/health`.
**Warning signs:** Network error "ECONNREFUSED" on `/api/l47/recommend` calls.

### Pitfall 6: Empty Recommendations Array Handled as Error
**What goes wrong:** Agent returns `{success: true, message: "No matching profiles found", recommendations: []}`. Frontend renders nothing (or crashes) instead of showing the message.
**Why it happens:** Developer assumes `recommendations.length > 0` always when `success: true`.
**How to avoid:** After mutation success, always check `data.recommendations.length`. If 0, render `data.message` as an info state rather than the results panel.
**Warning signs:** Blank screen after submission with no error displayed.

---

## Code Examples

Verified patterns from existing codebase:

### Empty/Error State Pattern (from CyperfAppsPage.tsx)
```typescript
// Use this pattern for empty recommendations
{!mutation.isPending && result && result.recommendations.length === 0 && (
  <div className="card-luxury text-center py-12 space-y-2">
    <p className="text-luxury-text-secondary text-sm">{result.message}</p>
    <p className="text-luxury-text-secondary text-xs">
      Try a more specific scenario or ensure Cyperf data is synced.
    </p>
  </div>
)}
```

### Loading State (from CyperfAppsPage.tsx)
```typescript
{mutation.isPending && (
  <div className="card-luxury flex items-center gap-3 text-luxury-text-secondary text-sm">
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-luxury-accent border-t-transparent" />
    Getting recommendations...
  </div>
)}
```

### Server Error Display (from QuestionnaireForm.tsx)
```typescript
{mutation.error && (
  <div className="bg-red-900/30 border border-red-700/40 rounded-md p-4">
    <p className="text-red-300 text-sm font-semibold">
      {mutation.error instanceof Error
        ? String(mutation.error.message)
        : 'Failed to get recommendations'}
    </p>
  </div>
)}
```
Note: Use dark-theme red tokens (`bg-red-900/30`, `border-red-700/40`, `text-red-300`) not light theme (`bg-red-50`, `text-red-800`).

### Route Registration (from App.tsx pattern)
```typescript
// In App.tsx, add inside <Routes>:
import { L47AdvisorPage } from './pages/L47AdvisorPage';

<Route path="/l47-advisor" element={<L47AdvisorPage />} />
```

### Profile Type Display Map
```typescript
// Display-friendly labels for profile_type values
const PROFILE_TYPE_LABELS: Record<string, string> = {
  application: 'Application',
  strike: 'Strike',
};

// Display-friendly labels for testing_focus values
const TESTING_FOCUS_LABELS: Record<string, string> = {
  app_performance: 'Application Performance',
  security_attacks: 'Security / Attacks',
  both: 'Both',
};
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Global fetch state in component | React Query useMutation | Auto pending/error/success tracking, retry, deduplication |
| Inline error messages (string literals) | Normalized error in hook | Prevents unrenderable objects in JSX (the AshRAI 422 bug) |
| Direct fetch to backend port | Vite proxy + nginx passthrough | CORS-free development, production-identical routing |
| Light-theme components | Dark-theme luxury-* tokens | Consistent Shodan aesthetic across all pages |

---

## Open Questions

1. **Should `/ashrai-assistant` be added to the nav at the same time as `/l47-advisor`?**
   - What we know: AshRAI page exists at `/ashrai-assistant` but is not in `NAV_STRUCTURE` in `Navigation.tsx` — it's unreachable from nav.
   - What's unclear: Whether this is intentional (AshRAI is a legacy/deprecated route) or an oversight.
   - Recommendation: Group both under an "AI Tools" nav group during Phase 7 — low cost, completes the nav.

2. **Should the L4-7 form use React Hook Form + Zod (like contact form) or manual state (like AshRAI)?**
   - What we know: Both patterns exist in the project. AshRAI uses manual state. Contact form uses RHF + Zod.
   - What's unclear: Which pattern the team prefers for new forms.
   - Recommendation: Use manual state (consistent with AshRAI, simpler for 4 fields). If RHF + Zod is preferred, it's already installed but adds boilerplate for minimal gain here.

3. **Does the agent service have a CORS issue when called directly from the browser?**
   - What we know: In production, nginx proxies `/api/l47/` to the agent container — no CORS issue. In dev, Vite proxy does the same.
   - What's unclear: Whether the agent service has CORS middleware configured (not visible in `main.py`).
   - Recommendation: The proxy pattern means CORS is irrelevant for this architecture. No action needed.

4. **What URL path does the Vite proxy send to the agent service?**
   - What we know: Agent route is `@app.post("/api/l47/recommend")`. The Vite proxy for `/api/l47` does NOT rewrite the path (unlike the `/api` entry which strips `/api`).
   - What's unclear: Whether the agent's uvicorn server expects the path with or without `/api/l47`.
   - Recommendation: Confirmed from `agent-service/main.py`: route is `/api/l47/recommend`. Proxy without rewrite sends the correct full path. Do NOT add a rewrite to the proxy config.

---

## Sources

### Primary (HIGH confidence)

- `agent-service/models.py` — Exact Pydantic schemas for request/response; source of truth for API contract
- `agent-service/main.py` — Confirmed route path `/api/l47/recommend`, port 8001, graceful degradation behavior
- `frontend/src/hooks/useAPI.ts` — Confirmed `useMutation` + axios error normalization pattern
- `frontend/src/pages/AshAiAssistantPage.tsx` — Confirmed form→results state machine pattern
- `frontend/src/components/QuestionnaireForm.tsx` — Confirmed controlled form state, validation errors, dark-theme-incompatible classes to avoid
- `frontend/vite.config.ts` — Confirmed proxy config; `/api` maps to localhost:8000 with rewrite; `/api/l47` not yet present
- `nginx.conf` — Confirmed production proxy config; `/api/` not yet routing to agent
- `frontend/tailwind.config.ts` — Confirmed `luxury-*` color tokens for dark theme
- `docker-compose.yml` — Confirmed agent service on port 8001, container name `cyperf_agent_l47`

### Secondary (MEDIUM confidence)

- `frontend/src/pages/CyperfAppsPage.tsx` — Verified loading/error/empty state patterns, dark theme Tailwind usage
- `frontend/src/components/layout/Navigation.tsx` — Verified NAV_STRUCTURE format for adding new routes
- `frontend/src/App.tsx` — Verified Route registration pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use
- Architecture: HIGH — direct codebase verification; API contract confirmed from agent source
- Pitfalls: HIGH — proxy ordering pitfall confirmed by reading vite.config.ts; type mismatch confirmed by reading both models.py and QuestionnaireForm.tsx
- Dark theme tokens: HIGH — tailwind.config.ts reviewed; SearchPage/CyperfAppsPage confirm usage

**Research date:** 2026-03-11
**Valid until:** 2026-04-10 (30 days; stable stack; agent API contract is implemented and will not change)

**Critical pre-planning verification:**
- The `/api/l47` proxy entry in `vite.config.ts` does not exist yet — planner MUST include this as task 1 (blocking all others)
- The nginx production config does not route `/api/l47/` yet — planner MUST include nginx update
- `AshAiAssistantPage.tsx` uses light-theme CSS — new page must NOT copy light-theme classes
