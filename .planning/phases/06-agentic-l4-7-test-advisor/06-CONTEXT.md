# Phase 6: Agentic L4-7 Test Advisor - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A Gemini-powered agentic service that accepts a structured L4-7 test scenario (use case, objectives, timeline, focus area), queries CyPerf profile data via the existing backend REST API, and returns a ranked list of up to 3 recommended CyPerf Application or Strike profiles with rationale. Ships as a standalone FastAPI container — UI integration is a follow-on task.

</domain>

<decisions>
## Implementation Decisions

### Input Design
- All 4 fields are required: `testing_focus`, `use_case`, `objectives`, `timeline`
- `testing_focus` accepts: `app_performance`, `security_attacks`, `both` — aligns with AshRAI convention
- Schema design (whether to extend AshRAI's `QuestionnaireRequest` or create a new model): Claude's discretion based on codebase patterns

### Recommendation Output
- Return top 3 ranked recommendations
- Each recommendation includes: **profile name + type** (application or strike) and **rationale** (2-3 concise sentences explaining why it matches the scenario)
- When `testing_focus` is `both`: return a single mixed ranked list (top 3 across both types, not split)
- No `next_steps` field — keep response lean
- No debug transparency — black box response (no `matched_profiles` or internal query data)

### Interaction Model
- Single-shot: one request → one response (stateless, no conversation)
- If no DB matches found: return empty recommendations list with a plain-language explanation message
- No follow-up or refinement endpoint in this phase

### Container & API Interface
- Standalone FastAPI service on a dedicated port (separate from main backend)
- No auth for this phase — internal service, consumed directly
- DB data access: agent calls the **existing main backend REST API** (e.g., `/cyperf-apps`, `/cyperf-app-types`, strike endpoints) — no direct PostgreSQL connection
- Gemini API key configured via environment variable (`GEMINI_API_KEY`) in `.env` / `docker-compose.yml`

### Claude's Discretion
- Whether to extend AshRAI's `QuestionnaireRequest` or define a new Pydantic model
- Which specific backend endpoints to call for data retrieval
- Gemini tool-calling vs prompt-with-context approach
- Confidence scoring / ranking algorithm
- Docker Compose port assignment for the agent container

</decisions>

<specifics>
## Specific Ideas

- User wants to eventually export recommendation output as text that can initialize a Claude session — noted as deferred, not in this phase
- Keep the response structure clean and minimal — the user will consume this programmatically

</specifics>

<deferred>
## Deferred Ideas

- **Export recommendations as text for Claude session initialization** — user explicitly mentioned this. Likely fits in the portal UI integration phase or a dedicated export/handoff phase.
- **Auth on the agent service** — add API key auth when agent integrates into the portal (follow-on task)

</deferred>

---

*Phase: 06-agentic-l4-7-test-advisor*
*Context gathered: 2026-03-11*
