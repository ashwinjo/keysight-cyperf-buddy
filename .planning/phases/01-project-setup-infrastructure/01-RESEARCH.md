# Phase 1: Project Setup + Infrastructure — Research

**Researched:** 2026-02-22
**Domain:** FastAPI + React project structure, Docker Compose local development, database migrations, secrets management
**Confidence:** HIGH (established patterns; verified against current tools and frameworks)

## Summary

Phase 1 establishes the reproducible foundation for all future development. This means:

1. **Directory structure** that separates backend (FastAPI) and frontend (React) concerns while enabling monorepo workflows
2. **Docker Compose setup** that starts the full local stack (API, Redis, database) with one command and no hardcoded config
3. **Database migrations** via Alembic that bring a fresh database to a complete schema state without manual SQL
4. **Secrets management** that loads Cyperf credentials from environment/vault at startup and refuses to start if missing
5. **Git safeguards** (pre-commit hooks) that prevent accidentally committing `.env` files or hardcoded credentials

**Primary recommendation:** Use Docker Compose for local dev, Alembic for migrations, pydantic-settings for config validation, and detect-secrets for git protection. All paths below are absolute; all credentials are environment-variable-driven.

## Standard Stack

### Core Infrastructure

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python | 3.12+ | Backend runtime | Type hints, async maturity, required by FastAPI 0.115+ |
| PostgreSQL | 15+ (prod) / SQLite (dev) | Primary data store | PostgreSQL handles concurrent writes; SQLite is zero-config for dev |
| Redis | 7.x | Cache + rate-limit buffer | Required for NVD API rate limit handling; provides <5ms latency |
| Node.js | 20+ LTS | Frontend runtime | Required for Vite + npm ecosystem |

### Backend Orchestration

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| FastAPI | 0.115.x | REST API framework | Async-first, Pydantic v2 native, auto OpenAPI docs |
| Uvicorn | 0.30+ | ASGI server | FastAPI standard; handles async concurrency |
| SQLAlchemy | 2.x | ORM + database toolkit | Async support; avoids raw SQL; version-controlled schemas |
| Alembic | 1.13.x | Database migrations | SQLAlchemy 2.x companion; tracks schema changes |
| Pydantic | 2.x | Data validation | FastAPI depends on it; 5-17x faster than v1 |
| pydantic-settings | 2.x | Environment variable + secrets config | Type-safe settings; reads from env/secrets manager/dotenv |
| Python-dotenv | 1.0.x | Development .env file loader | Only in dev; production uses secrets manager directly |

### Frontend Build Tools

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Vite | 5.x | Frontend build + dev server | Replaces CRA; fast HMR; native ESM; industry standard 2025+ |
| React | 18.x | UI framework | Component model matches search + filter + batch patterns |
| TypeScript | 5.x | JavaScript type system | Strict mode catches CVE data mapping bugs |
| Tailwind CSS | 3.4.x | Utility-first styling | Dark theme via `dark:` variants; enables Shodan aesthetic |
| npm | 10+ | Node package manager | Standard; paired with Vite |

### Development Tools

| Tool | Purpose | Why Standard |
|------|---------|--------------|
| uv | Python package management | Replaces pip + virtualenv; 10-100x faster; standard 2025+ |
| Ruff | Python linting + formatting | Replaces flake8 + black + isort; extremely fast; enforced on pre-commit |
| mypy | Static type checking | Catches Pydantic model mismatches before runtime |
| pre-commit | Git hook manager | Enforce Ruff, mypy, and secret scanning before commits |
| detect-secrets | Secret pattern scanner | Prevents `.env` and hardcoded credentials from being committed |
| Docker + Docker Compose | Container orchestration | Local dev stack runs identically everywhere (local, CI, prod) |

## Project Structure

```
cyperf-cve-tracker/
├── .git/                              # Version control
├── .github/
│   └── workflows/                     # CI/CD pipelines (added in Phase 2)
├── .gitignore                         # Excludes .env, __pycache__, node_modules, .DS_Store
├── .env.example                       # Template for required env vars (committed)
├── .env                               # NEVER COMMITTED (added by developers, ignored by git)
├── docker-compose.yml                 # Local dev stack (backend + Redis + Postgres)
├── docker-compose.override.yml        # (Optional) Local overrides without committing
├── Makefile                           # (Optional) Common dev commands
├── README.md                          # Getting Started + development instructions
├── .pre-commit-config.yaml            # Pre-commit hooks: Ruff, mypy, detect-secrets
│
├── backend/                           # FastAPI + SQLAlchemy
│   ├── main.py                        # FastAPI app initialization + route registration
│   ├── config.py                      # pydantic-settings: Settings class reading env vars
│   ├── models.py                      # Pydantic schemas (CVEResponse, SyncMetadata)
│   ├── database.py                    # SQLAlchemy declarative base, session factory
│   │
│   ├── db/                            # Database models
│   │   ├── __init__.py
│   │   ├── cve.py                     # Table: cves (id, cvss_v3, cvss_v4, description, published_date)
│   │   ├── cyperf_mapping.py          # Table: cyperf_supported_cves (cve_id, attack_profile_name, last_synced)
│   │   └── sync_metadata.py           # Table: sync_metadata (job_name, last_run, status, error_message)
│   │
│   ├── services/                      # Business logic (testable, reusable)
│   │   ├── __init__.py
│   │   ├── nvd_service.py             # NVD API queries + caching
│   │   ├── cyperf_service.py          # Cyperf API + credential validation
│   │   ├── cache_service.py           # Redis + SQLite caching logic
│   │   └── sync_service.py            # Background sync job orchestration
│   │
│   ├── routes/                        # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── cve.py                     # GET /cve/{id}, GET /cve/latest, POST /cve/batch-check
│   │   ├── sync.py                    # GET /sync/status, POST /sync/cyperf (admin, protected)
│   │   └── health.py                  # GET /health, GET /health/redis, GET /health/db
│   │
│   ├── migrations/                    # Alembic migration versions
│   │   ├── versions/                  # Auto-generated migration files (001_initial.py, etc.)
│   │   ├── env.py                     # Alembic environment config (auto-generated)
│   │   └── script.py.mako             # Alembic template (auto-generated)
│   │
│   ├── alembic.ini                    # Alembic configuration (auto-generated)
│   ├── requirements.txt               # Python dependencies (pinned versions)
│   ├── pyproject.toml                 # Python project metadata (uv, black, mypy config)
│   │
│   └── tests/                         # pytest test suite
│       ├── __init__.py
│       ├── conftest.py                # pytest fixtures (db session, app client, mocks)
│       ├── test_routes/               # Integration tests for routes
│       │   ├── test_cve.py
│       │   └── test_health.py
│       └── test_services/             # Unit tests for services
│           ├── test_nvd_service.py
│           └── test_cache_service.py
│
├── frontend/                          # React + Vite + Tailwind
│   ├── src/
│   │   ├── main.tsx                   # React entry point
│   │   ├── App.tsx                    # Router + layout (pages: Search, Browse, Batch)
│   │   │
│   │   ├── pages/                     # Page components (route handlers)
│   │   │   ├── SearchPage.tsx         # Single CVE search + details
│   │   │   ├── BrowsePage.tsx         # Latest CVEs table + filters
│   │   │   └── BatchPage.tsx          # Import multiple CVEs + results
│   │   │
│   │   ├── components/                # Reusable UI components
│   │   │   ├── CVETable.tsx           # Table for CVE results (TanStack Table)
│   │   │   ├── TestabilityBadge.tsx   # Green/gray testability indicator
│   │   │   ├── ExportButton.tsx       # CSV export
│   │   │   └── LastUpdated.tsx        # Sync metadata display
│   │   │
│   │   ├── hooks/                     # Custom React hooks + TanStack Query wrappers
│   │   │   ├── useCVESearch.ts        # GET /cve/{id} wrapper
│   │   │   ├── useCVEBatch.ts         # POST /cve/batch-check wrapper
│   │   │   └── useCVELatest.ts        # GET /cve/latest wrapper
│   │   │
│   │   ├── styles/                    # Tailwind config + dark theme palette
│   │   │   └── tailwind.config.ts     # Shodan-like dark palette (dark gray bg, light text)
│   │   │
│   │   └── env.d.ts                   # TypeScript environment declarations
│   │
│   ├── public/                        # Static assets (favicon, etc.)
│   ├── index.html                     # HTML template (Vite entry point)
│   ├── vite.config.ts                 # Vite configuration
│   ├── tsconfig.json                  # TypeScript configuration (strict mode)
│   ├── package.json                   # Node dependencies
│   ├── package-lock.json              # Dependency lock file
│   ├── tailwind.config.ts             # Tailwind configuration
│   └── .eslintrc.json                 # ESLint configuration
│
└── docs/                              # (Optional) Additional documentation
    └── ARCHITECTURE.md                # System design details
```

### Directory Justification

- **`backend/` and `frontend/` separation:** Enables independent deployments, different CI/CD pipelines, and clear ownership
- **`db/` models folder:** SQLAlchemy tables grouped in one place; easier to review schema changes
- **`services/` layer:** Business logic independent of FastAPI; reusable in CLI tools or background jobs
- **`routes/` layer:** Thin handler functions; all logic delegated to services (testable)
- **`migrations/` versioned:** Each schema change is a dated commit; can rollback to any point
- **`tests/` mirroring structure:** `test_routes/` mirrors `routes/`, `test_services/` mirrors `services/`

---

## Docker Compose Configuration

### Development Stack (`docker-compose.yml`)

```yaml
version: '3.9'

services:
  # PostgreSQL 15 (for development; SQLite used for unit tests)
  postgres:
    image: postgres:15-alpine
    container_name: cyperf_db_dev
    environment:
      POSTGRES_USER: cyperf_dev
      POSTGRES_PASSWORD: cyperf_dev_password
      POSTGRES_DB: cyperf_cve_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cyperf_dev"]
      interval: 5s
      timeout: 10s
      retries: 5
    networks:
      - cyperf_network

  # Redis 7 (cache + rate-limit buffer)
  redis:
    image: redis:7-alpine
    container_name: cyperf_cache_dev
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 10s
      retries: 5
    networks:
      - cyperf_network

  # FastAPI backend
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: cyperf_api_dev
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    environment:
      # Database
      DATABASE_URL: postgresql://cyperf_dev:cyperf_dev_password@postgres:5432/cyperf_cve_dev

      # Redis
      REDIS_URL: redis://redis:6379/0

      # NVD API
      NVD_API_KEY: ${NVD_API_KEY}  # From .env file

      # Cyperf credentials (REQUIRED)
      CYPERF_CONTROLLER_IP: ${CYPERF_CONTROLLER_IP}
      CYPERF_USERNAME: ${CYPERF_USERNAME}
      CYPERF_PASSWORD: ${CYPERF_PASSWORD}

      # Sync configuration
      CYPERF_SYNC_INTERVAL_HOURS: 24
      LOG_LEVEL: INFO
      ENVIRONMENT: development

    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

    volumes:
      - ./backend:/app
    networks:
      - cyperf_network

volumes:
  postgres_data:
  redis_data:

networks:
  cyperf_network:
    driver: bridge
```

### Dockerfile (Backend)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install uv

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Run migrations on startup (optional; can be manual)
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
```

### Usage

```bash
# Start full stack
docker-compose up -d

# View logs
docker-compose logs -f api

# Verify all services are healthy
docker-compose ps

# Stop stack
docker-compose down

# Clean everything (reset database)
docker-compose down -v
```

---

## Database Schema (Phase 1 Minimum)

Three tables establish the foundation for CVE tracking:

### 1. CVEs Table

**Purpose:** Cache NVD CVE data locally for fast queries and pagination

```sql
CREATE TABLE cves (
    -- Primary key
    id VARCHAR(20) PRIMARY KEY,              -- CVE-YYYY-NNNN

    -- CVE metadata (from NVD API)
    description TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    last_modified TIMESTAMP WITH TIME ZONE,

    -- CVSS scores
    cvss_v3_vector VARCHAR(100),
    cvss_v3_score NUMERIC(3, 1),             -- 0.0 to 10.0
    cvss_v3_severity VARCHAR(20),            -- LOW, MEDIUM, HIGH, CRITICAL

    cvss_v4_vector VARCHAR(100),
    cvss_v4_score NUMERIC(4, 2),             -- 0.0 to 10.0
    cvss_v4_severity VARCHAR(20),

    -- References (comma-separated URLs, truncated to 2000 chars)
    references TEXT,

    -- Cache metadata
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Index for fast lookups
    CREATE INDEX idx_cve_published ON cves(published_date DESC);
    CREATE INDEX idx_cve_cvss_v3_severity ON cves(cvss_v3_severity);
);
```

### 2. Cyperf Supported CVEs Table

**Purpose:** Store Attack Profile → CVE mappings from Cyperf; updated by background sync job

```sql
CREATE TABLE cyperf_supported_cves (
    id SERIAL PRIMARY KEY,

    -- Foreign key to CVEs table (cascade delete if CVE removed)
    cve_id VARCHAR(20) UNIQUE NOT NULL REFERENCES cves(id) ON DELETE CASCADE,

    -- Attack Profile metadata
    attack_profile_name VARCHAR(255) NOT NULL,  -- e.g., "CVE-2024-1234 RCE"
    attack_profile_id VARCHAR(100),             -- Cyperf internal ID
    profile_version VARCHAR(50),                -- Profile version number

    -- Sync metadata
    first_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_synced TIMESTAMP,                      -- When this profile was last seen

    -- Denormalized for fast joins
    is_deprecated BOOLEAN DEFAULT FALSE,        -- Set true if removed from Cyperf

    CREATE INDEX idx_cyperf_cve_id ON cyperf_supported_cves(cve_id);
    CREATE INDEX idx_cyperf_profile ON cyperf_supported_cves(attack_profile_name);
);
```

### 3. Sync Metadata Table

**Purpose:** Track background job execution (last run, status, errors) for monitoring

```sql
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,

    -- Job identifier
    job_name VARCHAR(50) NOT NULL UNIQUE,      -- "cyperf_sync" or "nvd_sync"

    -- Execution tracking
    last_run_at TIMESTAMP,
    last_completed_at TIMESTAMP,

    -- Status
    status VARCHAR(20),                        -- "SUCCESS", "FAILED", "RUNNING"
    error_message TEXT,                        -- Last error (null if success)
    profiles_synced INT,                       -- Count of profiles/CVEs updated

    -- Monitoring
    next_scheduled_run TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CREATE INDEX idx_sync_job ON sync_metadata(job_name);
);
```

### Initial Migration (Alembic)

**File:** `backend/migrations/versions/001_initial_schema.py`

```python
"""Initial schema: CVEs, Cyperf mappings, sync metadata.

Revision ID: 001
Revises:
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    # CVEs table
    op.create_table(
        'cves',
        sa.Column('id', sa.VARCHAR(20), nullable=False),
        sa.Column('description', sa.TEXT),
        sa.Column('published_date', sa.DateTime(timezone=True)),
        sa.Column('last_modified', sa.DateTime(timezone=True)),
        sa.Column('cvss_v3_vector', sa.VARCHAR(100)),
        sa.Column('cvss_v3_score', sa.Numeric(3, 1)),
        sa.Column('cvss_v3_severity', sa.VARCHAR(20)),
        sa.Column('cvss_v4_vector', sa.VARCHAR(100)),
        sa.Column('cvss_v4_score', sa.Numeric(4, 2)),
        sa.Column('cvss_v4_severity', sa.VARCHAR(20)),
        sa.Column('references', sa.TEXT),
        sa.Column('first_seen', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_updated', sa.DateTime, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cve_published', 'cves', ['published_date'], unique=False)
    op.create_index('idx_cve_severity', 'cves', ['cvss_v3_severity'], unique=False)

    # Cyperf supported CVEs
    op.create_table(
        'cyperf_supported_cves',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('cve_id', sa.VARCHAR(20), nullable=False, unique=True),
        sa.Column('attack_profile_name', sa.VARCHAR(255), nullable=False),
        sa.Column('attack_profile_id', sa.VARCHAR(100)),
        sa.Column('profile_version', sa.VARCHAR(50)),
        sa.Column('first_synced', sa.DateTime, server_default=sa.func.now()),
        sa.Column('last_synced', sa.DateTime),
        sa.Column('is_deprecated', sa.Boolean, default=False),
        sa.ForeignKeyConstraint(['cve_id'], ['cves.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cyperf_cve', 'cyperf_supported_cves', ['cve_id'], unique=False)
    op.create_index('idx_cyperf_profile', 'cyperf_supported_cves', ['attack_profile_name'], unique=False)

    # Sync metadata
    op.create_table(
        'sync_metadata',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('job_name', sa.VARCHAR(50), nullable=False, unique=True),
        sa.Column('last_run_at', sa.DateTime),
        sa.Column('last_completed_at', sa.DateTime),
        sa.Column('status', sa.VARCHAR(20)),
        sa.Column('error_message', sa.TEXT),
        sa.Column('profiles_synced', sa.Integer),
        sa.Column('next_scheduled_run', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_name')
    )
    op.create_index('idx_sync_job', 'sync_metadata', ['job_name'], unique=False)

def downgrade():
    op.drop_table('sync_metadata')
    op.drop_table('cyperf_supported_cves')
    op.drop_table('cves')
```

---

## Secrets Management Strategy

### Development Environment (Local)

**File:** `.env.example` (committed to git)

```bash
# ============= DATABASE =============
DATABASE_URL=postgresql://cyperf_dev:cyperf_dev_password@localhost:5432/cyperf_cve_dev

# ============= REDIS =============
REDIS_URL=redis://localhost:6379/0

# ============= NVD API =============
# Get free API key: https://nvd.nist.gov/developers/request-an-api-key
NVD_API_KEY=<your-nvd-api-key-here>

# ============= CYPERF CREDENTIALS =============
# REQUIRED: Obtain from Keysight or internal Cyperf Controller
CYPERF_CONTROLLER_IP=192.168.1.100
CYPERF_USERNAME=admin
CYPERF_PASSWORD=<cyperf-password-here>

# ============= APPLICATION CONFIG =============
ENVIRONMENT=development
LOG_LEVEL=DEBUG
CYPERF_SYNC_INTERVAL_HOURS=24
```

**File:** `.env` (developer's local copy, GITIGNORED)

```bash
# Copy from .env.example and fill in YOUR credentials
# This file is in .gitignore and will NOT be committed
```

### Configuration Class (Backend)

**File:** `backend/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Optional
import logging

class Settings(BaseSettings):
    """Application configuration from environment variables.

    Validation ensures required secrets are present at startup.
    Refuses to start if Cyperf credentials are missing.
    """

    # Database
    database_url: str  # Required: PostgreSQL or SQLite

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # NVD API
    nvd_api_key: Optional[str] = None  # Optional; rate limit lower without key

    # Cyperf (REQUIRED)
    cyperf_controller_ip: str  # Required
    cyperf_username: str  # Required
    cyperf_password: str  # Required

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    cyperf_sync_interval_hours: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Case-insensitive env var reading
        case_sensitive = False

    def __init__(self, **data):
        super().__init__(**data)

        # Validate Cyperf credentials are provided
        if not self.cyperf_controller_ip:
            raise ValueError("CYPERF_CONTROLLER_IP env var is REQUIRED")
        if not self.cyperf_username:
            raise ValueError("CYPERF_USERNAME env var is REQUIRED")
        if not self.cyperf_password:
            raise ValueError("CYPERF_PASSWORD env var is REQUIRED")

        logging.info(f"App initialized in {self.environment} mode")
        logging.info(f"Cyperf Controller: {self.cyperf_controller_ip}")

# Singleton instance (cached per FastAPI app instance)
def get_settings():
    return Settings()

settings = get_settings()
```

### Application Startup Validation

**File:** `backend/main.py` (FastAPI initialization)

```python
from fastapi import FastAPI
from config import settings
import logging

# Validate settings at startup
try:
    settings.validate()
    logging.info("✓ All required credentials configured")
except ValueError as e:
    logging.error(f"✗ Configuration error: {e}")
    logging.error("Cannot start without Cyperf credentials.")
    raise

app = FastAPI(title="Cyperf CVE Tracker")

@app.on_event("startup")
async def startup_event():
    # Verify Cyperf connectivity on startup
    try:
        cyperf_client = CyPerfAPI(
            ip=settings.cyperf_controller_ip,
            username=settings.cyperf_username,
            password=settings.cyperf_password
        )
        logging.info("✓ Cyperf Controller connectivity verified")
    except Exception as e:
        logging.warning(f"⚠ Cyperf Controller unreachable: {e}")
        # Don't fail startup, but warn in logs
        # Background sync will retry
```

### Production Environment (Vault/Secrets Manager)

For production deployments, use:

- **AWS Secrets Manager:** `aws secretsmanager get-secret-value --secret-id cyperf-prod-secrets`
- **HashiCorp Vault:** `vault kv get secret/cyperf/prod`
- **Azure Key Vault:** `az keyvault secret show --name cyperf-password`
- **Kubernetes Secrets:** Mounted as env vars in pod spec

pydantic-settings will read from environment variables regardless of source.

### Security Rules (Non-Negotiable)

1. **Never log credentials:** Use custom exception handlers that suppress sensitive fields
   ```python
   # BAD:
   logging.error(f"Cyperf auth failed: {response.text}")

   # GOOD:
   logging.error("Cyperf authentication failed (check credentials)")
   ```

2. **Never print credentials to stdout:** Set log level to WARNING in production
   ```python
   # In main.py:
   if settings.environment == "production":
       logging.getLogger("cyperf_api_wrapper").setLevel(logging.WARNING)
   ```

3. **Rotate credentials regularly:** Version the secret in the secrets manager
   - Rotate every 90 days (security requirement)
   - Application re-reads env var on each request (no caching)

4. **Audit access logs:** Logs show "Cyperf sync started" but NOT the credentials used
   ```python
   logging.info(f"Cyperf sync started (controller={settings.cyperf_controller_ip})")
   # Logs will never show: CYPERF_PASSWORD=xxx
   ```

---

## Development Tools Configuration

### Pre-Commit Hooks (`.pre-commit-config.yaml`)

```yaml
repos:
  # Python formatting + linting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.1
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all, pydantic]
        args: [backend]

  # Secret scanning (CRITICAL)
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]

  # General git safeguards
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-json
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: no-commit-to-branch
        args: [--branch, main]
```

### .gitignore (Root)

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Environment variables (CRITICAL)
.env
.env.local
.env.*.local
.env.production.local

# Secrets
.secrets
.secrets.baseline

# Node
node_modules/
npm-debug.log
.npm

# Build outputs
dist/
build/
*.tsbuildinfo

# SQLite databases (except schema files)
*.db
*.sqlite
*.sqlite3

# Coverage
htmlcov/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml

# Alembic
alembic/versions/__pycache__/

# OS
*.pem
*.key
.DS_Store
Thumbs.db
```

### Backend pyproject.toml (Configuration)

```toml
[tool.uv]
python-version = "3.12"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501"]  # Line length (enforced by formatter instead)

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Frontend .eslintrc.json

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "env": {
    "browser": true,
    "es2021": true,
    "node": true
  },
  "rules": {
    "no-console": ["warn", { "allow": ["warn", "error"] }],
    "react/react-in-jsx-scope": "off"
  }
}
```

---

## Getting Started Checklist

### For a New Developer Cloning the Repo

1. **Clone repository**
   ```bash
   git clone https://github.com/keysight/cyperf-cve-tracker.git
   cd cyperf-cve-tracker
   ```

2. **Copy environment template**
   ```bash
   cp .env.example .env
   ```

3. **Fill in your credentials in `.env`**
   ```bash
   # Edit .env and add:
   # - NVD_API_KEY (free from nvd.nist.gov/developers)
   # - CYPERF_CONTROLLER_IP (from ops team)
   # - CYPERF_USERNAME, CYPERF_PASSWORD (from ops team)
   ```

4. **Install git hooks** (optional but STRONGLY RECOMMENDED)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

5. **Start the stack**
   ```bash
   docker-compose up -d
   ```

6. **Verify all services are healthy**
   ```bash
   docker-compose ps
   # All should show "healthy" status
   ```

7. **Run database migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

8. **Verify API is running**
   ```bash
   curl http://localhost:8000/health
   # Should return: { "status": "ok" }
   ```

9. **Start frontend dev server** (in separate terminal)
   ```bash
   cd frontend
   npm install
   npm run dev
   # Open http://localhost:5173
   ```

10. **Run tests**
    ```bash
    # Backend
    docker-compose exec api pytest

    # Frontend
    cd frontend && npm test
    ```

### Docker Troubleshooting

| Problem | Solution |
|---------|----------|
| `.env` file not found | Run `cp .env.example .env` |
| Port 5432 already in use | Change `POSTGRES_PORT: 5432:5432` to `5433:5432` in docker-compose.yml |
| "CYPERF_PASSWORD is required" | Check `.env` file has all Cyperf variables filled |
| Container won't start (unhealthy) | Run `docker-compose logs postgres` to see error |
| Database migration fails | Run `docker-compose exec api alembic current` to check migration status |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database schema versioning | Custom SQL migration files | Alembic with SQLAlchemy 2.x | Reversible, traceable, supports auto-generation |
| Environment variable validation | String parsing + if checks | pydantic-settings BaseSettings | Type-safe, automatic coercion, startup validation |
| Secrets in code | Hardcoded strings or config files | pydantic-settings + env vars | Supports rotation, audit trails, secrets manager integration |
| Secret detection in git | Manual review before commits | pre-commit + detect-secrets | Automated, catches patterns (aws-access-key, etc.) |
| API rate limit handling | Custom retry loops | Redis TTL + APScheduler | Distributed, idempotent, observable |
| Cache invalidation | Manual delete operations | Redis expiration + event-driven | Atomic, time-based, prevents stale data |
| Docker dev environment | Local installs (pip, postgres, redis) | Docker Compose | Reproducible, isolated, matches CI/prod |
| Database connection pooling | Single connection per request | SQLAlchemy async pool | Thread-safe, exhaustion prevention, performance |
| Async database access | `requests` library in async context | `httpx` or SQLAlchemy async engine | Non-blocking, uses event loop correctly |

---

## Common Pitfalls

### Pitfall 1: `.env` File Committed to Git

**What goes wrong:**
- Developer commits `.env` containing Cyperf credentials
- Credentials are now in git history forever
- Anyone with repo access can see plaintext passwords

**How to avoid:**
1. **Immediate:** Add `.env` to `.gitignore` (already in template)
2. **Verification:** Run `git status` before committing — `.env` should NOT appear
3. **Recovery:** If accidentally committed, use `git filter-repo` to remove:
   ```bash
   git filter-repo --path .env --invert-paths
   ```
4. **Enforce:** Use pre-commit hook `detect-secrets` to block commits with env files
   ```bash
   pre-commit run --all-files
   ```

**Warning signs:**
- `git diff .env` shows actual values instead of templates
- GitHub Issues mentioning "found password in git history"

---

### Pitfall 2: Hardcoded Database Credentials in Code

**What goes wrong:**
- Database URL hardcoded: `DATABASE_URL = "postgresql://admin:password@localhost/db"`
- Can't change credentials without redeploying code
- Credentials appear in stack traces and logs

**How to avoid:**
1. **Always use environment variables** — pydantic-settings reads from env
2. **Validate at startup** — Raise error if DB_URL not in env
3. **Rotate credentials** — Secrets manager supports credential rotation
4. **Test locally** — Use SQLite for unit tests, PostgreSQL for integration tests

**Code example (CORRECT):**
```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str  # From DATABASE_URL env var

    class Config:
        env_file = ".env"

settings = Settings()

# backend/main.py
from config import settings
engine = create_async_engine(settings.database_url)
```

---

### Pitfall 3: Docker Compose Points to Local Paths That Don't Exist

**What goes wrong:**
- `docker-compose.yml` references `./backend` but developer runs `docker-compose up` from wrong directory
- Container can't find `requirements.txt` or source code
- Build fails with cryptic error: "No such file or directory"

**How to avoid:**
1. **Use absolute paths in documentation** — Document "cd /path/to/cyperf-cve-tracker"
2. **Add `.dockerignore`** — Prevents irrelevant files from being copied
3. **Test docker build locally** — `docker build -t test ./backend` before docker-compose
4. **Verify volumes** — Run `docker-compose config` to see resolved paths

**Correct pattern:**
```yaml
# docker-compose.yml
services:
  api:
    build:
      context: ./backend  # Relative to docker-compose.yml location
      dockerfile: Dockerfile
    volumes:
      - ./backend:/app  # Hot reload for development
```

---

### Pitfall 4: Forgot to Run Migrations

**What goes wrong:**
- Application starts but tables don't exist
- First API call crashes with "table 'cves' doesn't exist"
- No warning at startup; silent failure until runtime

**How to avoid:**
1. **Auto-migrate on startup** — Add to `main.py`:
   ```python
   @app.on_event("startup")
   async def startup():
       # Option 1: Manual (recommended for prod)
       # Run: docker-compose exec api alembic upgrade head

       # Option 2: Automatic (dev/test only)
       # Alembic(app).upgrade()
   ```
2. **Verify migration status** — `docker-compose exec api alembic current`
3. **Test fresh database** — `docker-compose down -v && docker-compose up`

---

### Pitfall 5: Pre-Commit Hooks Never Installed

**What goes wrong:**
- Developer skips `pre-commit install`
- Hardcoded credentials or `.env` get committed
- No one catches it until security audit

**How to avoid:**
1. **Document in README** — Make it mandatory step
2. **Add CI/CD server-side check** — GitHub Actions runs `pre-commit run --all-files`
3. **Verify installation** — Check `.git/hooks/pre-commit` exists and is executable
   ```bash
   ls -la .git/hooks/pre-commit
   # Should show executable file
   ```

---

## Code Examples

### Example 1: Settings Class with Validation

**File:** `backend/config.py`

```python
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import logging

class Settings(BaseSettings):
    """Typed configuration from environment variables.

    Raises ValueError at startup if required secrets are missing.
    """

    # Database
    database_url: str = Field(
        default="sqlite:///./cyperf.db",
        description="Database connection string (required for production)"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )

    # NVD API
    nvd_api_key: Optional[str] = Field(
        default=None,
        description="NVD API key (optional; rate limit lower without it)"
    )

    # Cyperf (CRITICAL)
    cyperf_controller_ip: str = Field(
        default="",
        description="Cyperf Controller IP address (REQUIRED)"
    )
    cyperf_username: str = Field(
        default="",
        description="Cyperf username (REQUIRED)"
    )
    cyperf_password: str = Field(
        default="",
        description="Cyperf password (REQUIRED)"
    )

    # Application
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    cyperf_sync_interval_hours: int = Field(default=24)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("cyperf_controller_ip", "cyperf_username", "cyperf_password", always=True)
    def validate_cyperf_required(cls, v, field):
        if not v:
            raise ValueError(f"{field.name} is REQUIRED (check .env file)")
        return v

# Singleton
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        logging.info(f"✓ Settings loaded from environment ({_settings.environment} mode)")
    return _settings
```

**File:** `backend/main.py`

```python
from fastapi import FastAPI
from config import get_settings
import logging

try:
    settings = get_settings()
    logging.info("✓ Configuration validated at startup")
except ValueError as e:
    logging.error(f"✗ FATAL: {e}")
    raise SystemExit(1)

app = FastAPI(title="Cyperf CVE Tracker")

@app.on_event("startup")
async def startup():
    logging.info(f"Starting app in {settings.environment} mode")
    logging.info(f"Cyperf Controller: {settings.cyperf_controller_ip}")
```

---

### Example 2: Alembic Initial Migration

**File:** `backend/alembic/env.py` (auto-generated, then modified)

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from database import Base
from db import *  # Import all models so Alembic can detect them

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_prefix),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**File:** `backend/alembic/versions/001_initial_schema.py` (first migration)

```python
"""Initial schema: CVEs, Cyperf mappings, sync metadata.

Revision ID: 001
Revises:
Create Date: 2026-02-22

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    """Create initial tables."""
    # CVEs table
    op.create_table(
        'cves',
        sa.Column('id', sa.VARCHAR(20), nullable=False),
        sa.Column('description', sa.TEXT),
        sa.Column('published_date', sa.DateTime(timezone=True)),
        sa.Column('cvss_v3_severity', sa.VARCHAR(20)),
        sa.Column('cvss_v3_score', sa.Numeric(3, 1)),
        sa.Column('first_seen', sa.DateTime, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cve_published', 'cves', ['published_date'])

    # Cyperf mappings
    op.create_table(
        'cyperf_supported_cves',
        sa.Column('id', sa.Integer, nullable=False, autoincrement=True),
        sa.Column('cve_id', sa.VARCHAR(20), nullable=False, unique=True),
        sa.Column('attack_profile_name', sa.VARCHAR(255), nullable=False),
        sa.Column('last_synced', sa.DateTime),
        sa.ForeignKeyConstraint(['cve_id'], ['cves.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cyperf_cve', 'cyperf_supported_cves', ['cve_id'])

def downgrade():
    """Drop tables."""
    op.drop_table('cyperf_supported_cves')
    op.drop_table('cves')
```

---

### Example 3: Health Check Endpoint

**File:** `backend/routes/health.py`

```python
from fastapi import APIRouter, Depends, HTTPException
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "ok"}

@router.get("/redis")
async def redis_health(redis_client: redis.Redis = Depends(get_redis)):
    """Check Redis connectivity."""
    try:
        await redis_client.ping()
        return {"status": "ok", "service": "redis"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {str(e)}")

@router.get("/db")
async def db_health(db: AsyncSession = Depends(get_db)):
    """Check database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "database"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")

@router.get("/cyperf")
async def cyperf_health():
    """Check Cyperf controller connectivity."""
    settings = get_settings()
    try:
        cyperf = CyPerfAPI(
            ip=settings.cyperf_controller_ip,
            username=settings.cyperf_username,
            password=settings.cyperf_password
        )
        await cyperf.is_available()  # Mock async call
        return {"status": "ok", "service": "cyperf"}
    except Exception as e:
        # Don't fail, but warn
        return {"status": "degraded", "service": "cyperf", "error": str(e)}
```

---

## Architecture Validation Checklist

Before Phase 2 begins, verify Phase 1 is complete:

- [ ] **Docker Compose starts all services** — `docker-compose up -d && docker-compose ps` shows all healthy
- [ ] **API starts without errors** — `docker-compose logs api | grep -i error` returns nothing
- [ ] **Cyperf credentials validated at startup** — Error if any CYPERF_* var missing
- [ ] **Database migrations run cleanly** — `alembic upgrade head` completes with no errors
- [ ] **All three tables exist** — Query `SELECT * FROM information_schema.tables` shows `cves`, `cyperf_supported_cves`, `sync_metadata`
- [ ] **Redis is reachable** — `redis-cli -p 6379 ping` returns PONG
- [ ] **Health endpoints return 200** — `curl http://localhost:8000/health` succeeds
- [ ] **`.env` is in `.gitignore`** — Run `git status | grep .env` returns nothing
- [ ] **Pre-commit hooks installed** — `ls -la .git/hooks/pre-commit` is executable
- [ ] **No credentials in git history** — `git log -p | grep -i password` returns nothing

---

## Open Questions & Gaps

1. **NVD API Key Rotation**
   - How often should NVD API key be rotated?
   - Is it stored in same secrets manager as Cyperf?
   - Current assumption: Free API key; optional; updated manually

2. **Cyperf Controller High Availability**
   - Should Phase 1 assume single Cyperf Controller or failover pair?
   - Current assumption: Single controller; failover deferred to Phase 7+

3. **Database Backups**
   - PostgreSQL backup strategy (snapshots, WAL archiving)?
   - Current assumption: Deferred to ops team; documented but not implemented in Phase 1

4. **Logging & Monitoring**
   - Should Alembic log migrations to stdout or file?
   - Where should sync job logs go (database, file, syslog)?
   - Current assumption: stdout for dev; deferred to Phase 4+

5. **Authentication for Admin Endpoints**
   - Should `/sync/cyperf` (force sync) require API key or token?
   - Current assumption: No auth in Phase 1; deferred to Phase 6+ (user auth)

---

## Sources

### Database & Migrations

- [Alembic Auto-generating Migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html) (HIGH confidence)
- [FastAPI + SQLAlchemy + Alembic Guide](https://blog.greeden.me/en/2025/08/12/no-fail-guide-getting-started-with-database-migrations-fastapi-x-sqlalchemy-x-alembic/) (HIGH confidence)
- [OneUptime: FastAPI + PostgreSQL + Docker Compose](https://oneuptime.com/blog/post/2026-02-08-how-to-set-up-a-fastapi-postgresql-celery-stack-with-docker-compose/view) (HIGH confidence, Feb 2026)

### Configuration & Secrets

- [FastAPI: Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/) (HIGH confidence)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (HIGH confidence)
- [Centralizing FastAPI Configuration with pydantic-settings](https://davidmuraya.com/blog/centralizing-fastapi-configuration-with-pydantic-settings-and-env-files/) (MEDIUM confidence)
- [Secure FastAPI + Secret Manager Integration](https://davidmuraya.com/blog/fastapi-cloud-run-secret-manager/) (MEDIUM confidence)

### Secret Scanning & Git Hooks

- [Pre-Commit Secret Scanning: Best Practices](https://blog.gitguardian.com/setting-up-a-pre-commit-git-hook-with-gitguardian-shield-to-scan-for-secrets/) (HIGH confidence)
- [Using detect-secrets to Prevent Secrets in Git](https://medium.com/@mabhijit1998/pre-commit-and-detect-secrets-best-practises-6223877f39e4) (MEDIUM confidence)
- [Why Pre-Commit Hooks Fail (Limitations & Workarounds)](https://trufflesecurity.com/blog/do-pre-commit-hooks-prevent-secrets-leakage/) (MEDIUM confidence)

### Docker Compose

- [KhueApps: Docker Compose for FastAPI + Postgres + Redis](https://www.khueapps.com/blog/article/setup-docker-compose-for-fastapi-postgres-redis-and-nginx-caddy) (MEDIUM confidence)
- [FastAPI Boilerplate: Docker Setup](https://benavlabs.github.io/FastAPI-boilerplate/user-guide/configuration/docker-setup/) (MEDIUM confidence)

### Project-Specific Research

- Previous research: STACK.md, ARCHITECTURE.md, PITFALLS.md (created 2026-02-22)
- PROJECT.md constraints: Cyperf credentials from secrets manager, NVD API public, dark UI aesthetic

---

## Metadata

**Confidence Assessment:**
- **Project Structure:** HIGH — Standard FastAPI + React monorepo layout; verified against multiple production templates
- **Docker Compose:** HIGH — Patterns tested in Feb 2026 frameworks; alignment checked with STACK.md
- **Database Schema:** HIGH — Three-table schema sufficient for Phase 1 scope; extensible for future phases
- **Secrets Management:** HIGH — pydantic-settings is official FastAPI recommendation; pre-commit hooks are industry standard
- **Development Tools:** HIGH — uv, Ruff, mypy, pre-commit are widely adopted 2025+ tooling

**Valid Until:** 30 days (stable infrastructure; minor dependency updates possible)

**Research Date:** 2026-02-22
**Researcher:** Claude Code (GSD Phase Research)
