# Summary: Quick Task 3 — AI-Type Strike Ingestion with ai_cves Table

**Completed:** 2026-02-24
**Mode:** quick
**Plan:** 3-PLAN.md

---

## What Was Built

Fixed a silent data-loss bug in the Cyperf ingestion pipeline where AI-type strikes (those with
no `Type='CVE'` reference in their `Metadata.References` array) were permanently discarded.
All five tasks were executed atomically with individual commits.

---

## Tasks Completed

### Task 1 — `backend/db/ai_cves.py` (commit: 48a82e9)

Created `AICve` SQLAlchemy ORM model (`__tablename__ = "ai_cves"`) with:
- `id` `VARCHAR(36)` surrogate PK — new `uuid4` per full-replace cycle
- `cve_id` `VARCHAR(60)` UNIQUE — `NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>`; stable
  across re-syncs (49 chars total; 11-char margin in the column)
- `strike_name` `VARCHAR(512)` — wider than the `VARCHAR(255)` of `cverf_cve_strike_mappings`
  to handle long AI strike names
- `strike_type` `VARCHAR(50)` `server_default='ai_attack'` — extensible for future no-CVE
  categories (`fuzzing`, `protocol_abuse`, etc.) without schema migrations
- `metadata` `TEXT` nullable — `json.dumps()` of raw `Metadata.References` list
- `created_at` / `updated_at` `DateTime(timezone=True)` with `server_default=func.now()`
- Three indexes: `idx_ai_cves_cve_id`, `idx_ai_cves_strike_name`, `idx_ai_cves_strike_type`

Pattern matched `cverf_cve_strike_mappings.py` exactly.

---

### Task 2 — `backend/migrations/versions/003_add_ai_cves.py` (commit: 088c3ca)

Alembic migration `revision="003"`, `down_revision="002"`.

- `upgrade()`: `op.create_table("ai_cves", ...)` with all columns, `PrimaryKeyConstraint("id")`,
  `UniqueConstraint("cve_id")`, three `op.create_index()` calls.
- `downgrade()`: drops indexes in reverse order then `op.drop_table("ai_cves")`.

Migration chain is now: `001 -> 002 -> 003`.

---

### Task 3 — `backend/services/cyperf_service.py` (commit: 021bdaa)

Three changes:

1. Added `import uuid` to imports.

2. Added new dataclasses after `SyncResult`:
   ```python
   @dataclass
   class AIStrikeRecord:
       row_id: str          # uuid4 per insert
       cve_id: str          # NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>
       strike_name: str
       strike_type: str
       metadata_json: str | None

   @dataclass
   class StrikeFetchResult:
       cve_mappings: dict[str, str]
       ai_strikes: list[AIStrikeRecord]
   ```

3. Added `CYPERF_AI_NAMESPACE = uuid.NAMESPACE_DNS` and `_make_synthetic_cve_id(strike_name)`.

4. Changed `fetch_cve_strike_mappings()` return type from `dict[str, str]` to `StrikeFetchResult`.
   Added `found_cve = False` flag before the inner `for ref in refs` loop. After the loop:
   ```python
   if not found_cve:
       ai_strikes.append(AIStrikeRecord(row_id=str(uuid.uuid4()), ...))
   ```
   Updated log line to include AI strike count.

5. Updated `sync_cyperf_cves()` (backward-compat wrapper) to unpack `StrikeFetchResult`.

---

### Task 4 — `backend/services/sync_service.py` (commit: 106e3e3)

Three changes:

1. Added imports: `from db.ai_cves import AICve` and `AIStrikeRecord, StrikeFetchResult` from
   `cyperf_service`.

2. Updated call site to unpack `StrikeFetchResult`:
   ```python
   fetch_result: StrikeFetchResult = await cyperf_service.fetch_cve_strike_mappings()
   cve_mappings = fetch_result.cve_mappings
   ai_strikes: list[AIStrikeRecord] = fetch_result.ai_strikes
   ```

3. Extended the `async with session.begin()` block to also delete+insert `ai_cves` in the
   same transaction as `cverf_cve_strike_mappings`:
   ```python
   await session.execute(delete(AICve))
   for record in ai_strikes:
       session.add(AICve(id=record.row_id, cve_id=record.cve_id, ...))
   ```
   Both tables now roll back atomically on any DB error.

The `if cves_count == 0` guard was preserved — zero real CVE mappings is still a suspicious
sync result regardless of AI strike count.

---

### Task 5 — `backend/tests/test_cyperf_integration.py` (commit: 9d75e2e)

Five changes:

1. Added imports: `AICve`, `StrikeFetchResult`.

2. Added `await conn.execute("DELETE FROM ai_cves")` to `_clean_cverf_rows()` (before existing
   table deletions, respecting FK-free design).

3. Added two AI strikes to `mock_strikes` fixture:
   - URL-only: `"Strike AI LLM SQL Injection Jailbreak Attack using OpenAI Chat Delimiters - Grok"`
     with `[{"Type": "url", "Value": "https://arxiv.org/abs/2307.15043"}]`
   - Empty refs: `"Strike AI Protocol Fuzzer - EmptyRefs"` with `{"References": []}`

4. Updated all 4 existing `TestCyperfServiceFetchMappings` tests to use `result.cve_mappings`
   and added `assert isinstance(result, StrikeFetchResult)` to each.

5. Added `TestAIStrikeDetection` class with 5 unit tests:
   - `test_ai_strikes_captured_in_ai_strikes_list` — AI strikes in `ai_strikes`, not
     `cve_mappings`; 4 total no-CVE records from `mock_strikes`
   - `test_ai_strike_cve_id_starts_with_nocve_prefix` — all `cve_id` values start with
     `"NoCVE_cyperf"`
   - `test_ai_strike_cve_id_is_deterministic` — same `cve_id` across two calls (uuid5
     idempotency); different `row_id` each time (uuid4)
   - `test_ai_strike_url_only_metadata_json_contains_url` — `metadata_json` is valid JSON
     containing the url reference
   - `test_ai_strike_empty_refs_metadata_json_is_none` — empty refs produces `metadata_json=None`

6. Added `test_perform_sync_writes_ai_cves_rows` integration test to `TestPerformSyncRefactored`
   — asserts `ai_cves` has 1 row after sync, with correct `strike_name`, `NoCVE_cyperf` prefix
   on `cve_id`, and `strike_type='ai_attack'`.

---

## Files Changed

| File | Action | Commit |
|---|---|---|
| `backend/db/ai_cves.py` | Created | 48a82e9 |
| `backend/migrations/versions/003_add_ai_cves.py` | Created | 088c3ca |
| `backend/services/cyperf_service.py` | Modified | 021bdaa |
| `backend/services/sync_service.py` | Modified | 106e3e3 |
| `backend/tests/test_cyperf_integration.py` | Modified | 9d75e2e |

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Separate `ai_cves` table (not reusing `cverf_cve_strike_mappings`) | `cve_id` on existing table is `VARCHAR(20)` — too narrow for 49-char synthetic IDs; semantic model differs |
| `uuid5(NAMESPACE_DNS, strike_name)` for `cve_id` | Deterministic: same strike -> same ID across all re-syncs; external references remain stable |
| `uuid4` for `id` (PK) | Full-replace strategy resets PK each cycle; surrogate key avoids needing composite natural key |
| Both tables in one transaction | Atomic: if `ai_cves` insert fails, `cverf_cve_strike_mappings` also rolls back; prevents split-brain |
| `found_cve` flag (not name-prefix heuristic) | Structural detection is more robust than string matching on strike names |
| `VARCHAR(512)` for `strike_name` | AI strike names exceed the `VARCHAR(255)` of the existing table |
| `strike_type` with `server_default='ai_attack'` | Extensible without migrations; future: `fuzzing`, `protocol_abuse` |

---

## Out of Scope (Phase 1 — not implemented)

- Surfacing AI strikes in `GET /cve/latest` or `GET /cve/search`
- Frontend Browse tab changes
- CVSS scoring for AI strikes
- Deduplication of variant strike names (e.g. `- Grok` vs `- GPT4`)

---

## Validation

All 5 commits passed pre-commit hooks (ruff lint + ruff-format). The test file was
auto-reformatted by ruff-format on first commit attempt and re-staged cleanly.

Unit tests (`TestAIStrikeDetection`) can be run without a live database.
Integration test (`test_perform_sync_writes_ai_cves_rows`) requires `migration 003` applied
to the PostgreSQL dev database before execution.
