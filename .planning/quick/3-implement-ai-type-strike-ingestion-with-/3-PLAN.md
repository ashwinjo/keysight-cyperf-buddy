# Plan: Implement AI-Type Strike Ingestion with ai_cves Table

**Created:** 2026-02-24
**Mode:** quick
**Debug context:** `.planning/debug/ai-strike-ingestion.md`

---

## Root Cause (from debug session)

`fetch_cve_strike_mappings()` in `cyperf_service.py` lines 110-118 silently drops any strike
where the `Metadata.References` array contains no `{"Type": "CVE", ...}` entry. AI-type strikes
use only `{"Type": "url", ...}` references. No else/fallthrough branch exists. They are never
inserted into `cverf_cve_strike_mappings` and are lost permanently.

The existing `cverf_cve_strike_mappings.cve_id` column is `VARCHAR(20)` — sufficient for
`CVE-YYYY-NNNNNNN` (19 chars) but too narrow for a synthetic `NoCVE_cyperf<uuid5>` ID (49 chars).
A separate table is required.

---

## Tasks

### Task 1 — Create ai_cves ORM model

**File to create:** `/Users/ashwin.joshi/claudeExp/backend/db/ai_cves.py`

Model class `AICve(Base)`, `__tablename__ = "ai_cves"`.

Columns:

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `VARCHAR(36)` | PK, NOT NULL | `uuid4` per insert (new each full-replace) |
| `cve_id` | `VARCHAR(60)` | UNIQUE, NOT NULL | `NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>` |
| `strike_name` | `VARCHAR(512)` | NOT NULL | Full Cyperf strike name; 512 to handle AI strike name length |
| `strike_type` | `VARCHAR(50)` | NOT NULL, `server_default='ai_attack'` | Extensible: `ai_attack`, `fuzzing`, `protocol_abuse` |
| `metadata` | `TEXT` | nullable | `json.dumps()` of raw `Metadata.References` list |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()` | |
| `updated_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()`, `onupdate=func.now()` | |

Indexes:
- `idx_ai_cves_cve_id` on `cve_id`
- `idx_ai_cves_strike_name` on `strike_name`
- `idx_ai_cves_strike_type` on `strike_type`

Pattern: match style of `/Users/ashwin.joshi/claudeExp/backend/db/cverf_cve_strike_mappings.py`.

---

### Task 2 — Create Alembic migration 003

**File to create:** `/Users/ashwin.joshi/claudeExp/backend/migrations/versions/003_add_ai_cves.py`

```
revision = "003"
down_revision = "002"
```

`upgrade()`: `op.create_table("ai_cves", ...)` with all columns above + `PrimaryKeyConstraint("id")`
+ `UniqueConstraint("cve_id")` + three `op.create_index()` calls.

`downgrade()`: drop indexes in reverse order, then `op.drop_table("ai_cves")`.

Pattern: match style of `/Users/ashwin.joshi/claudeExp/backend/migrations/versions/002_add_cverf_cve_strike_mappings.py`.

---

### Task 3 — Refactor cyperf_service.py ingestion logic

**File:** `/Users/ashwin.joshi/claudeExp/backend/services/cyperf_service.py`

#### 3a. Add new dataclasses (after existing `SyncResult`)

```python
@dataclass
class AIStrikeRecord:
    row_id: str          # uuid4 — surrogate PK for this insert cycle
    cve_id: str          # NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>
    strike_name: str
    strike_type: str     # default: 'ai_attack'
    metadata_json: str | None  # json.dumps(refs) or None


@dataclass
class StrikeFetchResult:
    cve_mappings: dict[str, str]      # CVE-YYYY-NNNNN -> strike_name
    ai_strikes: list[AIStrikeRecord]  # no-CVE strikes with synthetic IDs
```

#### 3b. Add synthetic ID generator function

```python
import uuid

CYPERF_AI_NAMESPACE = uuid.NAMESPACE_DNS

def _make_synthetic_cve_id(strike_name: str) -> str:
    deterministic = uuid.uuid5(CYPERF_AI_NAMESPACE, strike_name)
    return f"NoCVE_cyperf{deterministic}"
```

#### 3c. Update `fetch_cve_strike_mappings()` signature and logic

Change return type from `dict[str, str]` to `StrikeFetchResult`.

Inside the `for strike in strikes` loop, add a `found_cve = False` flag before the `for ref in refs`
loop. Set `found_cve = True` when a valid CVE ref is processed. After the inner loop:

```python
if not found_cve:
    cve_id = _make_synthetic_cve_id(strike_name)
    refs = strike.get("Metadata", {}).get("References", [])
    ai_strikes.append(AIStrikeRecord(
        row_id=str(uuid.uuid4()),
        cve_id=cve_id,
        strike_name=strike_name,
        strike_type="ai_attack",
        metadata_json=json.dumps(refs) if refs else None,
    ))
```

Change final return to `StrikeFetchResult(cve_mappings=cve_mappings, ai_strikes=ai_strikes)`.

Update log line: `f"Fetched {profiles_count} strikes, {len(cve_mappings)} CVE mappings, {len(ai_strikes)} AI strikes"`.

---

### Task 4 — Update sync_service.py to write ai_cves

**File:** `/Users/ashwin.joshi/claudeExp/backend/services/sync_service.py`

#### 4a. Update imports

Add:
```python
from db.ai_cves import AICve
from services.cyperf_service import AIStrikeRecord, StrikeFetchResult
```

#### 4b. Update call site (line 97)

```python
# Before
cve_mappings = await cyperf_service.fetch_cve_strike_mappings()
cves_count = len(cve_mappings)

# After
fetch_result: StrikeFetchResult = await cyperf_service.fetch_cve_strike_mappings()
cve_mappings = fetch_result.cve_mappings
ai_strikes = fetch_result.ai_strikes
cves_count = len(cve_mappings)
```

Keep the existing `if cves_count == 0` guard — it is still valid; a sync returning zero real CVE
mappings is suspicious regardless of AI strike count.

#### 4c. Extend the atomic full-replace block (after existing CvrfCveStrikeMappings insert)

Inside the existing `async with session.begin()` block, after inserting CVE mappings:

```python
# Full-replace AI strikes
await session.execute(delete(AICve))
for record in ai_strikes:
    session.add(AICve(
        id=record.row_id,
        cve_id=record.cve_id,
        strike_name=record.strike_name,
        strike_type=record.strike_type,
        metadata=record.metadata_json,
    ))

logger.info(f"Full-replace sync: inserted {len(ai_strikes)} AI strike rows into ai_cves")
```

Both tables are updated in a single transaction — if either insert fails, both roll back.

#### 4d. Update the `record_sync_complete` call metadata

The existing call passes `cves_count` twice (as `profiles_count` and `cves_count`). No schema
change is required for Phase 1 — the AI strike count can be logged only. If the `SyncMetadata`
model supports an `extra` or notes field, record `ai_strikes_count=len(ai_strikes)` there.

---

### Task 5 — Update tests

**File:** `/Users/ashwin.joshi/claudeExp/backend/tests/test_cyperf_integration.py`

#### 5a. Add AI strike to `mock_strikes` fixture

Append to the list in `mock_strikes()`:

```python
{
    "Name": "Strike AI LLM SQL Injection Jailbreak Attack using OpenAI Chat Delimiters - Grok",
    "Metadata": {
        "References": [
            {"Type": "url", "Value": "https://arxiv.org/abs/2307.15043"},
        ],
    },
},
```

Also add an empty-refs case:

```python
{
    "Name": "Strike AI Protocol Fuzzer - EmptyRefs",
    "Metadata": {"References": []},
},
```

#### 5b. Update `TestCyperfServiceFetchMappings` assertions

`fetch_cve_strike_mappings()` now returns `StrikeFetchResult`, not `dict`. Update all call sites:

```python
result = await service.fetch_cve_strike_mappings()
assert isinstance(result, StrikeFetchResult)
cve_mappings = result.cve_mappings
ai_strikes = result.ai_strikes
```

Add assertions:
- AI strike name NOT in `cve_mappings` values
- `ai_strikes` contains exactly 2 records (URL-only + empty-refs)
- `ai_strikes[0].cve_id` starts with `"NoCVE_cyperf"`
- Calling `fetch_cve_strike_mappings()` again produces the same `cve_id` for the same strike name
  (determinism check — uuid5 property)
- `ai_strikes[0].metadata_json` is a valid JSON string containing `"url"`
- `ai_strikes[1].metadata_json` is None (empty refs)

#### 5c. Add cleanup to `_clean_cverf_rows()`

```python
await conn.execute("DELETE FROM ai_cves")
```

#### 5d. Update integration test for `perform_sync()`

Add assertion that `ai_cves` table has rows after sync completes (query via `select(AICve)`).

---

## Execution Order

```
Task 1 (ORM model)
    -> Task 2 (migration — depends on schema being finalized)
    -> Task 3 (cyperf_service — no db dependency, can parallel with Task 2)
        -> Task 4 (sync_service — depends on Task 3 return type + Task 1 model)
            -> Task 5 (tests — depends on all above)
```

Tasks 2 and 3 can proceed in parallel after Task 1 is complete.

---

## Constraints and Edge Cases

| Scenario | Handling |
|---|---|
| AI strike name > 255 chars | `VARCHAR(512)` in new schema; old table is `VARCHAR(255)` |
| Same AI strike re-synced | `cve_id` is identical (uuid5); `id` PK is new uuid4 — full-replace handles this |
| Missing `Metadata` key entirely | `strike.get("Metadata", {})` returns `{}`, `refs = []`, `found_cve = False`, written to `ai_cves` with `metadata_json=None` |
| CVE strike that also matches AI naming | Independent — real CVE ref takes precedence; `found_cve=True` skips AI path |
| `NoCVE_cyperf` + uuid5 = 49 chars | `VARCHAR(60)` has 11 chars margin; safe |
| Both tables in one transaction | If `ai_cves` insert fails, `cverf_cve_strike_mappings` also rolls back — atomic |

---

## Out of Scope (Phase 1)

- Surfacing AI strikes in `GET /cve/latest` or `GET /cve/search`
- Frontend Browse tab changes
- CVSS scoring for AI strikes
- Deduplication of strike name variants (e.g. "- Grok" vs "- GPT4")
- Parsing embedded stringified list artifact from AI strike names
