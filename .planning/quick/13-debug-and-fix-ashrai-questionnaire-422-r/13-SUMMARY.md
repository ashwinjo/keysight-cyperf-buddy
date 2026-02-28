---
phase: quick
plan: "13"
subsystem: ashrai
tags: [bug-fix, error-handling, fastapi, react-query, axios, pydantic]
dependency_graph:
  requires: [backend/main.py, frontend/src/hooks/useAPI.ts, frontend/src/components/QuestionnaireForm.tsx]
  provides: [flat-string 422 responses, renderable mutation.error.message]
  affects: [AshRAI questionnaire form, all FastAPI routes (422 normalisation)]
tech_stack:
  added: []
  patterns:
    - FastAPI app-level RequestValidationError handler
    - Axios error transformation in React Query mutationFn
    - Defensive String() coercion in JSX error rendering
key_files:
  modified:
    - backend/main.py
    - frontend/src/hooks/useAPI.ts
    - frontend/src/components/QuestionnaireForm.tsx
decisions:
  - Handler registered on app instance (not APIRouter) — FastAPI only supports exception_handler on the FastAPI app object, not on sub-routers
  - Two-layer fix (backend + frontend) — backend normalises at source; frontend fallback handles pre-deployment or non-ashrai 422s from other routes
  - loc filter excludes 'body' prefix — keeps messages concise: 'use_case -> ...' not 'body -> use_case -> ...'
metrics:
  duration: "3 minutes (2026-02-28T04:33:38Z to 2026-02-28T04:36:26Z)"
  completed: "2026-02-28"
  tasks_completed: 3
  files_modified: 3
---

# Quick Task 13: Debug and Fix AshRAI Questionnaire 422 + React Rendering Error — Summary

**One-liner:** Three-layer fix eliminating the React "Objects not valid as React child" crash caused by Pydantic's default 422 array-detail response reaching JSX uncoerced.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend RequestValidationError handler | 4ba83e6 | backend/main.py |
| 2 | Frontend hook error transformation | 5e3cbf3 | frontend/src/hooks/useAPI.ts |
| 3 | Frontend component defensive coercion | d09963b | frontend/src/components/QuestionnaireForm.tsx |

---

## Root Cause Summary

FastAPI's default `RequestValidationError` response returns:

```json
{"detail": [{"type": "string_too_short", "loc": ["body", "use_case"], "msg": "...", "input": "..."}]}
```

`detail` is an **array of objects**. If this array ever reaches a JSX render point, React throws `Objects are not valid as a React child`. The three-layer fix closes every path where this can happen:

1. **Backend** — Normalises 422 at source to `{"detail": "use_case: String should have at least 5 characters"}`.
2. **Frontend hook** — Transforms AxiosError before it reaches `mutation.error`, re-throwing a plain `Error` with a string `.message`.
3. **Frontend component** — `String(mutation.error.message)` prevents any future regression.

---

## Task 1 — Backend: RequestValidationError Handler (backend/main.py)

Added an app-level exception handler registered immediately after `app = FastAPI(...)`:

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    messages: list[str] = []
    for err in errors:
        loc = " -> ".join(str(part) for part in err.get("loc", []) if part != "body")
        msg = err.get("msg", "invalid value")
        messages.append(f"{loc}: {msg}" if loc else msg)
    detail = "; ".join(messages) if messages else "Validation error"
    return JSONResponse(status_code=422, content={"detail": detail})
```

Verified output:
```json
{"detail": "use_case: String should have at least 5 characters"}
```

The handler applies globally to all routes registered on the `app` instance.

---

## Task 2 — Frontend Hook: AxiosError Transformation (frontend/src/hooks/useAPI.ts)

Wrapped the `axios.post` call in try/catch. On `AxiosError`:

- `detail` is `string` (HTTPException) → use directly
- `detail` is `Array` (Pydantic fallback / older backend) → flatten to `loc -> sub: msg` strings joined by `'; '`
- `detail` is neither → fall back to `"Request failed with status {status}"`

Re-throws as `new Error(message)` so `mutation.error.message` is always a string.

---

## Task 3 — Frontend Component: Defensive Coercion (frontend/src/components/QuestionnaireForm.tsx)

Two changes:

1. `String(mutation.error.message)` in the JSX error block — coerces any edge-case object to `'[object Object]'` rather than crashing React.
2. `onError: () => {}` added to `mutation.mutate()` options — makes error state propagation explicit and guarantees re-render on 422.

---

## Verification Results

All three curl tests from the plan pass against the rebuilt container:

| Test | Expected | Actual |
|------|----------|--------|
| `use_case="hi"` (too short) | `{"detail": "use_case: String should have at least 5 characters"}` | PASS |
| `use_case` valid, `application_metric` missing | `{"detail": "application_metric is required..."}` | PASS |
| Full valid request | `{"success": true, "recommendations": [...]}` | PASS (7 recs, 6 steps) |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Container required rebuild (not just restart)**
- **Found during:** Task 1 verification
- **Issue:** Source is baked into Docker image (no volume mounts); `docker restart` does not pick up code changes.
- **Fix:** Ran `docker-compose build api && docker-compose up -d api` after all three tasks were committed.
- **Files modified:** None (infrastructure action only)

None of the code changes deviated from the plan specification.

---

## Self-Check: PASSED

All files exist on disk. All task commits confirmed in git log.

| Item | Status |
|------|--------|
| backend/main.py | FOUND |
| frontend/src/hooks/useAPI.ts | FOUND |
| frontend/src/components/QuestionnaireForm.tsx | FOUND |
| 13-SUMMARY.md | FOUND |
| Commit 4ba83e6 (Task 1) | FOUND |
| Commit 5e3cbf3 (Task 2) | FOUND |
| Commit d09963b (Task 3) | FOUND |
