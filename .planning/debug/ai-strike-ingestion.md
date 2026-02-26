# AI Strike Ingestion Bug — Root Cause Analysis

**Date:** 2026-02-24
**Severity:** Data loss (entire class of AI-type strikes silently excluded from DB)
**Status:** Unresolved — pending implementation

---

## 1. Root Cause

The filtering logic in `fetch_cve_strike_mappings()` assumes every strike contains a structured
`Metadata.References[]` array where each entry has a `{"Type": "CVE", "Value": "YYYY-NNNNN"}`
shape. AI-type strikes do **not** follow this structure.

### Exact failure site

**File:** `/Users/ashwin.joshi/claudeExp/backend/services/cyperf_service.py`
**Lines:** 110-118

```python
refs = strike.get("Metadata", {}).get("References", [])
for ref in refs:
    if ref.get("Type") == "CVE" and ref.get("Value"):  # <-- AI strikes never enter here
        cve_id = f"CVE-{ref['Value']}"
        cve_mappings[cve_id] = strike_name
    elif ref.get("Type") == "CVE":                     # <-- AI strikes never enter here either
        logger.warning(...)
```

AI-type strikes have **no `Type: CVE` reference** — their `References` list contains entries like
`[{'Type': 'url', ...}]` only, or the `References` list may be empty entirely. The `for ref in refs`
loop either iterates with no matching branch (silent skip) or never executes at all.

There is no `else` branch to catch strikes that finish the loop with zero CVE references. These
strikes — and the test of AI attack vectors they represent — are simply **never inserted** into
`cverf_cve_strike_mappings`.

### AI strike name format (from the issue)

```
Strike AI LLM SQL Injection Jailbreak Attack using OpenAI Chat Delimiters - Grok
[{'Type': 'url', 'Value': 'https://...'}]
```

The name itself may embed a stringified list in some Cyperf API versions (rendering artifact),
but the structural problem is in the `Metadata.References` array — no `Type: CVE` entry exists.

---

## 2. Code Locations Requiring Changes

### 2a. Primary change — `cyperf_service.py`

**File:** `/Users/ashwin.joshi/claudeExp/backend/services/cyperf_service.py`

The `fetch_cve_strike_mappings()` method returns `dict[str, str]` (CVE ID → strike name).
This return type assumes every retained strike has a real CVE ID. To handle AI strikes:

- The method must detect strikes where no `Type: CVE` reference exists after iterating refs.
- These strikes need a synthetic `NoCVE_cyperf<uuid>` identifier.
- They must be returned in a separate collection (or the return type must change).

**Current signature:**
```python
async def fetch_cve_strike_mappings(self) -> dict[str, str]:
```

**Required change:** Add a second return value (or a new method) to also yield AI strikes
with synthetic IDs. The cleanest approach is a new dataclass return type:

```python
@dataclass
class StrikeFetchResult:
    cve_mappings: dict[str, str]          # CVE-YYYY-NNNNN -> strike_name
    ai_strikes: list[AIStrikeRecord]      # NoCVE_cyperf<uuid> -> strike data
```

### 2b. Secondary change — `sync_service.py`

**File:** `/Users/ashwin.joshi/claudeExp/backend/services/sync_service.py`

`perform_sync()` currently only processes `cve_mappings` from `fetch_cve_strike_mappings()`.
It must also process the `ai_strikes` collection and write them to a separate `ai_cves` table.

**Lines 96-114:** After receiving the result from `cyperf_service.fetch_cve_strike_mappings()`,
the sync must also:
1. Delete all existing `ai_cves` rows (full-replace strategy, consistent with `cverf_cve_strike_mappings`)
2. Insert all `ai_strikes` records into the `ai_cves` table

### 2c. New ORM model — `db/ai_cves.py`

New file required. See Section 4 for schema.

### 2d. No route changes required for Phase 1

The existing `cve_service.py` and `routes/cve.py` do not need modification to unblock ingestion.
Surfacing AI strikes in the API is a separate concern (Phase 2 of this work).

---

## 3. AI Strike Detection Logic

An AI-type strike is identified by **negative detection** after the references loop completes:

```python
found_cve = False
for ref in refs:
    if ref.get("Type") == "CVE" and ref.get("Value"):
        found_cve = True
        cve_id = f"CVE-{ref['Value']}"
        cve_mappings[cve_id] = strike_name
    elif ref.get("Type") == "CVE":
        logger.warning(f"Incomplete CVE reference in strike '{strike_name}': {ref}")

if not found_cve:
    # No CVE reference found — treat as AI/no-CVE strike
    ai_strikes.append(AIStrikeRecord(...))
```

This handles:
- Strikes with only `Type: url` references (AI LLM attacks)
- Strikes with empty `References: []`
- Strikes with missing `Metadata` entirely (currently silently dropped; could be AI)

To distinguish "genuinely has no CVE" from "malformed", the strike name prefix can be used as a
secondary signal: AI strikes from Cyperf follow the `Strike AI ...` naming convention.

---

## 4. Proposed `ai_cves` Table Schema

### Design rationale

- Uses a surrogate `id` (UUID as VARCHAR(36)) since there is no natural composite key
  analogous to `(cve_id, strike_name)` in the CVE mapping table.
- The `cve_id` column holds the synthetic `NoCVE_cyperf<uuid4>` identifier — stable per strike
  across re-syncs if generated deterministically (e.g., `uuid5(NAMESPACE_DNS, strike_name)`).
- `strike_type` defaults to `'ai_attack'` but allows extensibility for future no-CVE strike
  categories (e.g., `'fuzzing'`, `'protocol_abuse'`).
- `metadata` is `TEXT` (JSON-encoded) to store the raw `References` array and any other
  contextual fields from the Cyperf API response without schema migrations for each new field.
- Full-replace strategy matches `cverf_cve_strike_mappings` — no delta tracking at this layer.

### ORM model (`db/ai_cves.py`)

```python
from sqlalchemy import TEXT, VARCHAR, Column, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class AICve(Base):
    __tablename__ = "ai_cves"

    # Surrogate primary key — UUID as string for portability across SQLite/PostgreSQL
    id = Column(
        VARCHAR(36),
        primary_key=True,
        nullable=False,
        comment="UUID primary key (uuid4)",
    )

    # Synthetic CVE identifier: NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)>
    # Deterministic: same strike_name always yields the same cve_id across re-syncs
    cve_id = Column(
        VARCHAR(60),
        nullable=False,
        unique=True,
        comment="Synthetic CVE ID, e.g. NoCVE_cyperf550e8400-e29b...",
    )

    # Full strike name from Cyperf API (e.g. 'Strike AI LLM SQL Injection ...')
    strike_name = Column(
        VARCHAR(512),
        nullable=False,
        comment="Cyperf Strike name (may be long for AI strikes)",
    )

    # Category tag — default 'ai_attack'; extensible for future no-CVE categories
    strike_type = Column(
        VARCHAR(50),
        nullable=False,
        server_default="ai_attack",
        comment="Strike category: ai_attack | fuzzing | protocol_abuse | ...",
    )

    # JSON blob of raw Metadata.References from Cyperf (URL refs, etc.)
    # Stored as TEXT; application layer is responsible for json.loads/dumps
    metadata = Column(
        TEXT,
        nullable=True,
        comment="JSON-encoded Metadata.References from Cyperf API response",
    )

    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when this record was first inserted",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when this record was last updated",
    )

    __table_args__ = (
        Index("idx_ai_cves_cve_id", "cve_id"),
        Index("idx_ai_cves_strike_name", "strike_name"),
        Index("idx_ai_cves_strike_type", "strike_type"),
    )

    def __repr__(self) -> str:
        return f"<AICve(cve_id={self.cve_id!r}, strike={self.strike_name!r})>"
```

### SQL DDL equivalent

```sql
CREATE TABLE ai_cves (
    id           VARCHAR(36)  NOT NULL,
    cve_id       VARCHAR(60)  NOT NULL UNIQUE,
    strike_name  VARCHAR(512) NOT NULL,
    strike_type  VARCHAR(50)  NOT NULL DEFAULT 'ai_attack',
    metadata     TEXT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX idx_ai_cves_cve_id     ON ai_cves(cve_id);
CREATE INDEX idx_ai_cves_strike_name ON ai_cves(strike_name);
CREATE INDEX idx_ai_cves_strike_type ON ai_cves(strike_type);
```

---

## 5. Synthetic CVE ID Generation Strategy

Use `uuid5` (deterministic, name-based) keyed on the strike name. This ensures the same
`NoCVE_cyperf<uuid>` is produced for the same strike across every re-sync, making the
full-replace strategy idempotent without needing to track history.

```python
import uuid

CYPERF_AI_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # uuid.NAMESPACE_DNS

def make_synthetic_cve_id(strike_name: str) -> str:
    """Generate deterministic NoCVE_cyperf<uuid5> for a no-CVE strike."""
    deterministic_uuid = uuid.uuid5(CYPERF_AI_NAMESPACE, strike_name)
    return f"NoCVE_cyperf{deterministic_uuid}"
```

Example output: `NoCVE_cyperf550e8400-e29b-11d4-a716-446655440000`

The `id` column (surrogate PK) uses `uuid4()` — new random UUID per insert (reset each full-replace).
The `cve_id` column uses `uuid5` — stable identifier for external references.

---

## 6. Migration Strategy

### Migration file location

All migrations are in:
```
/Users/ashwin.joshi/claudeExp/backend/migrations/versions/
```

Current chain:
- `001_initial_schema.py` (revision: `001`, down_revision: `None`)
- `002_add_cverf_cve_strike_mappings.py` (revision: `002`, down_revision: `001`)

New migration:
- `003_add_ai_cves.py` (revision: `003`, down_revision: `002`)

### Migration content

```python
"""Add ai_cves table for no-CVE AI-type strikes.

Revision ID: 003
Revises: 002
Create Date: 2026-02-24 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_cves",
        sa.Column("id", sa.VARCHAR(36), nullable=False),
        sa.Column("cve_id", sa.VARCHAR(60), nullable=False),
        sa.Column("strike_name", sa.VARCHAR(512), nullable=False),
        sa.Column(
            "strike_type",
            sa.VARCHAR(50),
            nullable=False,
            server_default="ai_attack",
        ),
        sa.Column("metadata", sa.TEXT(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cve_id"),
    )
    op.create_index("idx_ai_cves_cve_id", "ai_cves", ["cve_id"])
    op.create_index("idx_ai_cves_strike_name", "ai_cves", ["strike_name"])
    op.create_index("idx_ai_cves_strike_type", "ai_cves", ["strike_type"])


def downgrade() -> None:
    op.drop_index("idx_ai_cves_strike_type", table_name="ai_cves")
    op.drop_index("idx_ai_cves_strike_name", table_name="ai_cves")
    op.drop_index("idx_ai_cves_cve_id", table_name="ai_cves")
    op.drop_table("ai_cves")
```

---

## 7. Implementation Approach (Ordered Steps)

### Step 1 — New ORM model
Create `/Users/ashwin.joshi/claudeExp/backend/db/ai_cves.py` with the `AICve` model above.

### Step 2 — Alembic migration
Create `/Users/ashwin.joshi/claudeExp/backend/migrations/versions/003_add_ai_cves.py` with
the migration from Section 6.

### Step 3 — New dataclass in cyperf_service.py
Add `AIStrikeRecord` dataclass and `StrikeFetchResult` to replace the bare `dict[str, str]`
return type of `fetch_cve_strike_mappings()`.

```python
@dataclass
class AIStrikeRecord:
    strike_name: str
    strike_type: str
    metadata_json: str  # json.dumps of raw References list
    cve_id: str         # pre-computed NoCVE_cyperf<uuid5>
    row_id: str         # uuid4 for the PK column
```

### Step 4 — Modify `fetch_cve_strike_mappings()` detection logic
After the inner `for ref in refs` loop completes without finding any CVE reference, append an
`AIStrikeRecord` to a local `ai_strikes` list. Return `StrikeFetchResult(cve_mappings, ai_strikes)`.

### Step 5 — Modify `perform_sync()` in sync_service.py
After inserting `cve_mappings` into `cverf_cve_strike_mappings`, also:
- `DELETE FROM ai_cves` (full-replace)
- Insert each `AIStrikeRecord` as an `AICve` row

Update `SyncMetadata.record_sync_complete()` call to include AI strike count in metadata
(pass via `profiles_count` or add a new field if tracking separately matters).

### Step 6 — Update test fixtures
Add an AI strike mock to `mock_strikes` fixture in `test_cyperf_integration.py`:

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

Add assertions that:
- The AI strike does NOT appear in `cve_mappings` (no CVE ID)
- The AI strike DOES appear in `ai_strikes` with a `NoCVE_cyperf...` synthetic ID
- `perform_sync()` writes it to `ai_cves` table

---

## 8. Edge Cases and Failure Modes

| Scenario | Current behavior | Correct behavior after fix |
|---|---|---|
| AI strike with only `Type: url` refs | Silently dropped | Written to `ai_cves` with `strike_type='ai_attack'` |
| Strike with empty `References: []` | Silently dropped | Written to `ai_cves` with `strike_type='ai_attack'`, `metadata=null` |
| Strike with missing `Metadata` entirely | Silently dropped | Logged as warning; optionally written to `ai_cves` with `metadata=null` |
| Same AI strike name across re-syncs | N/A | `cve_id` is stable (uuid5); `id` (PK) is new uuid4 each full-replace |
| AI strike name > 255 chars | Would truncate on VARCHAR(255) | `strike_name` is VARCHAR(512) in new schema |
| CVE strike also has AI attack variant | Independent rows | CVE mapping in `cverf_cve_strike_mappings`; AI variant separate in `ai_cves` |

### Idempotency guarantee

The uuid5-based `cve_id` is deterministic: the same strike name always produces the same
synthetic CVE ID regardless of when the sync runs. This means any downstream system or
external reference that bookmarks a `NoCVE_cyperf...` ID will remain stable across full-replace
re-syncs, even though the `id` (PK) column changes each cycle.

### VARCHAR(20) constraint on existing `cverf_cve_strike_mappings.cve_id`

The existing table uses `VARCHAR(20)` for `cve_id` (sufficient for `CVE-YYYY-NNNNNNN` = 19 chars).
The new `ai_cves.cve_id` must be `VARCHAR(60)` to hold `NoCVE_cyperf` (13 chars) + UUID (36 chars)
= 49 chars total. **Do not attempt to store AI synthetic IDs in the existing table** — the column
is too narrow and the semantic model is different.

---

## 9. Out of Scope (This Investigation)

- Surfacing AI strikes in `GET /cve/latest` or `GET /cve/search` (requires `cve_service.py` changes)
- Parsing embedded stringified metadata from AI strike names (the `[{...}]` suffix in the name string)
- Assigning CVSS scores to AI strikes (no NVD equivalent exists; would require manual tagging)
- Frontend display of AI strike rows (requires new UI component for the Browse tab)
- Deduplication of AI strikes that share the same vulnerability class but differ only in model name
  (e.g., "- Grok" vs "- GPT4" variants)
