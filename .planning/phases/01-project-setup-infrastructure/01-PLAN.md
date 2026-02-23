# Phase 1 Plan: Project Setup + Infrastructure

## Plan Overview

**Total Tasks:** 7 cohesive work units
**Estimated Scope:** 6-8 hours solo developer time
**Wave Structure:** 3 waves (parallel setup → docker → validation)

**Task Dependencies:**
- **Wave 1 (parallel):** Git setup, backend skeleton, frontend skeleton, env templates
- **Wave 2 (sequential):** Docker Compose + Dockerfile, Alembic initialization
- **Wave 3 (sequential):** Health check endpoints, final verification + pre-commit hooks

**Parallelizable Work:**
- Tasks 1.1, 1.2, 1.3, 1.4 can run in parallel (independent file creation)
- Task 1.5 depends on 1.1 (backend structure exists) + 1.3 (env template exists)
- Task 1.6 depends on 1.5 (Docker Compose working)
- Task 1.7 depends on 1.6 (database migrated)

---

## Goal-Backward Verification

**Phase Goal:** Development environment is reproducible, secrets are managed securely, and the data layer (PostgreSQL/SQLite + Redis) is operational and schema-complete.

**Observable Truths (must ALL be true when Phase 1 completes):**
1. Developer can clone repo → copy `.env.example` → run `docker compose up -d` and all services are healthy within 30 seconds
2. API container fails to start (with clear error) if any Cyperf env var is missing
3. Running `alembic upgrade head` creates three tables: `cves`, `cyperf_supported_cves`, `sync_metadata` with correct schemas
4. `curl http://localhost:8000/health/redis` returns `{"status": "ok", "service": "redis"}`
5. Running `git add .env` followed by `pre-commit run --all-files` rejects the commit with "secret detected"

**Required Artifacts:**
- `/Users/ashwin.joshi/claudeExp/docker-compose.yml` (multi-service orchestration)
- `/Users/ashwin.joshi/claudeExp/backend/Dockerfile` (API container definition)
- `/Users/ashwin.joshi/claudeExp/backend/config.py` (Settings validation with Cyperf check)
- `/Users/ashwin.joshi/claudeExp/backend/main.py` (FastAPI app + startup validation)
- `/Users/ashwin.joshi/claudeExp/backend/migrations/versions/001_initial_schema.py` (Alembic migration)
- `/Users/ashwin.joshi/claudeExp/backend/routes/health.py` (Health check endpoints)
- `/Users/ashwin.joshi/claudeExp/.pre-commit-config.yaml` (Secret scanning + linting hooks)
- `/Users/ashwin.joshi/claudeExp/.env.example` (env var template)
- `/Users/ashwin.joshi/claudeExp/.gitignore` (exclude `.env`, credentials)

**Key Links (critical connections):**
- `docker-compose.yml` → `backend/Dockerfile`: Build context must point to `./backend` with `requirements.txt` present
- `backend/main.py` → `backend/config.py`: Startup must load Settings and raise error if Cyperf vars missing
- `docker-compose.yml` → environment section: All `${VAR_NAME}` must map to keys in `.env.example`
- `backend/migrations/versions/001_initial_schema.py` → database schema: Migration must create all three tables for Phase 2 to query them
- `.pre-commit-config.yaml` → `.git/hooks/pre-commit`: Pre-commit install must succeed for hooks to activate

---

## Task Breakdown

### Task 1.1: Initialize Git Repository + Pre-Commit Hooks

**Goal:** Set up git tracking and configure automated pre-commit safeguards to prevent credential leaks.

**Depends on:** None (Wave 1)

**Files Created/Modified:**
- `.git/` (git repo initialization — likely already present, but verify)
- `.pre-commit-config.yaml` (hook configuration)
- `.gitignore` (exclude `.env`, cache, build artifacts)
- `.secrets.baseline` (detect-secrets baseline)

**Action:**
1. Verify `.git/` exists; if not, run `git init`
2. Create `.gitignore` with entries for:
   - Python: `__pycache__/`, `*.py[cod]`, `.egg-info/`, `venv/`, `*.egg`, `.mypy_cache/`, `.pytest_cache/`
   - Environment: `.env`, `.env.local`, `.env.*.local`
   - Secrets: `.secrets`, `.secrets.baseline`
   - IDE/OS: `.vscode/`, `.idea/`, `.DS_Store`, `*.swp`, `*.swo`
   - Node: `node_modules/`, `npm-debug.log`
   - SQLite: `*.db`, `*.sqlite`, `*.sqlite3`
   - Build: `dist/`, `build/`, `*.tsbuildinfo`
3. Create `.pre-commit-config.yaml` with hooks for:
   - **ruff**: Python formatting + linting (`--fix` enabled)
   - **mypy**: Type checking (target `backend/`)
   - **detect-secrets**: Secret pattern scanning (baseline file: `.secrets.baseline`)
   - **pre-commit/pre-commit-hooks**: Check added large files (500KB limit), merge conflicts, yaml syntax, trailing whitespace, no commits to main branch
4. Run `pre-commit install` to activate hooks in `.git/hooks/`
5. Run `pre-commit run --all-files` once to initialize baseline (creates `.secrets.baseline`)
6. Verify `.git/hooks/pre-commit` is executable: `ls -la .git/hooks/pre-commit | grep -x ....-r..-r..`

**Verify:**
```bash
# Hooks installed and executable
ls -la .git/hooks/pre-commit

# Baseline created
test -f .secrets.baseline && echo "✓ Baseline exists"

# .env file is gitignored
git status | grep -q ".env" && echo "✗ .env tracked!" || echo "✓ .env ignored"

# Test secret detection
echo 'CYPERF_PASSWORD=admin123' > test_secret.py
pre-commit run detect-secrets --all-files 2>&1 | grep -q "Yelp detect-secrets" && echo "✓ Secret detection works"
rm test_secret.py
```

**Done:** Pre-commit hooks are installed and configured. Running `git add .env` followed by `git commit` is rejected with detect-secrets error. All python files pass Ruff + mypy checks before commit.

---

### Task 1.2: Backend Project Skeleton + Python Configuration

**Goal:** Create reproducible Python project structure with uv/pip, pyproject.toml, and first test.

**Depends on:** None (Wave 1)

**Files Created/Modified:**
- `backend/` (directory structure)
- `backend/pyproject.toml` (project metadata, dependencies)
- `backend/requirements.txt` (pinned dependencies for Docker)
- `backend/__init__.py` (package marker)
- `backend/main.py` (FastAPI app initialization stub)
- `backend/config.py` (Settings class with validation)
- `backend/database.py` (SQLAlchemy engine + session factory)
- `backend/models.py` (Pydantic schemas)

**Action:**
1. Create `backend/` directory structure:
   ```
   backend/
   ├── __init__.py
   ├── main.py
   ├── config.py
   ├── database.py
   ├── models.py
   ├── db/
   │   ├── __init__.py
   │   ├── cve.py
   │   ├── cyperf_mapping.py
   │   └── sync_metadata.py
   ├── routes/
   │   ├── __init__.py
   │   ├── health.py
   │   └── cve.py (stub)
   ├── services/
   │   ├── __init__.py
   │   └── health_service.py
   ├── migrations/
   │   └── (initialized in Task 1.5)
   ├── tests/
   │   ├── __init__.py
   │   └── conftest.py (pytest fixtures)
   ├── pyproject.toml
   ├── requirements.txt
   └── .env.example (symlink or copy from root, Task 1.3)
   ```

2. Create `backend/pyproject.toml`:
   ```toml
   [project]
   name = "cyperf-cve-tracker-backend"
   version = "0.1.0"
   description = "FastAPI backend for Cyperf CVE Tracker"
   requires-python = ">=3.12"

   [tool.uv]
   python-version = "3.12"

   [tool.ruff]
   line-length = 100
   target-version = "py312"

   [tool.ruff.lint]
   select = ["E", "F", "W", "I", "UP"]
   ignore = ["E501"]

   [tool.mypy]
   python_version = "3.12"
   strict = true
   warn_return_any = true
   disallow_untyped_defs = true

   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   ```

3. Create `backend/requirements.txt` with pinned versions:
   ```
   fastapi==0.115.0
   uvicorn==0.30.0
   sqlalchemy==2.0.25
   alembic==1.13.1
   pydantic==2.6.0
   pydantic-settings==2.1.0
   python-dotenv==1.0.0
   redis==5.0.1
   httpx==0.26.0
   psycopg==3.1.15
   pytest==7.4.4
   pytest-asyncio==0.23.2
   ```

4. Create `backend/config.py` with Settings class:
   - Load all environment variables (DATABASE_URL, REDIS_URL, CYPERF_*, NVD_API_KEY)
   - Validate that CYPERF_CONTROLLER_IP, CYPERF_USERNAME, CYPERF_PASSWORD are present
   - Raise ValueError at import time if validation fails
   - Log "✓ All required credentials configured" on success

5. Create `backend/database.py`:
   - SQLAlchemy async engine using DATABASE_URL
   - AsyncSessionLocal factory
   - Base declarative class for ORM models

6. Create `backend/models.py`:
   - Pydantic schemas: CVEResponse, CyperfMappingResponse, SyncStatusResponse (used in Phase 2)

7. Create `backend/main.py`:
   - FastAPI app initialization
   - Load settings at module level (triggers validation)
   - Register routes: `/health`, `/cve`, `/sync` (stubs for now)
   - Log startup messages

**Verify:**
```bash
cd backend

# Can import without error (means config validation passed)
python -c "from config import settings; print(f'✓ Loaded {settings.environment} mode')"

# pyproject.toml is valid
python -m toml < pyproject.toml > /dev/null 2>&1 && echo "✓ Valid TOML"

# requirements.txt installs (skip actual install, just validate syntax)
python -m pip install --dry-run -r requirements.txt 2>&1 | grep -q "Would install" && echo "✓ Requirements valid"
```

**Done:** Backend skeleton exists with valid pyproject.toml and requirements.txt. Importing `config.settings` validates Cyperf env vars. FastAPI app can be imported (`from main import app`).

---

### Task 1.3: Frontend Project Skeleton + Environment Template

**Goal:** Create React + Vite + Tailwind frontend structure and root-level `.env.example` template.

**Depends on:** None (Wave 1)

**Files Created/Modified:**
- `frontend/` (directory structure)
- `frontend/package.json` (npm dependencies)
- `frontend/vite.config.ts` (Vite configuration)
- `frontend/tsconfig.json` (TypeScript strict mode)
- `frontend/tailwind.config.ts` (Tailwind dark theme)
- `frontend/src/main.tsx` (React entry point stub)
- `frontend/src/App.tsx` (Router stub)
- `frontend/index.html` (HTML template)
- `.env.example` (root level, environment variable template)

**Action:**
1. Create `frontend/` directory with structure:
   ```
   frontend/
   ├── src/
   │   ├── main.tsx
   │   ├── App.tsx
   │   ├── pages/
   │   │   ├── SearchPage.tsx (stub)
   │   │   ├── BrowsePage.tsx (stub)
   │   │   └── BatchPage.tsx (stub)
   │   ├── components/
   │   │   └── (empty, populated in Phase 4)
   │   ├── hooks/
   │   │   └── (empty, populated in Phase 2-4)
   │   └── styles/
   ├── public/
   ├── index.html
   ├── vite.config.ts
   ├── tsconfig.json
   ├── tailwind.config.ts
   ├── eslintrc.json
   ├── package.json
   ├── package-lock.json
   └── .env.example (copy from root)
   ```

2. Create `frontend/package.json`:
   ```json
   {
     "name": "cyperf-cve-tracker-frontend",
     "version": "0.1.0",
     "type": "module",
     "scripts": {
       "dev": "vite",
       "build": "tsc && vite build",
       "preview": "vite preview",
       "lint": "eslint src"
     },
     "dependencies": {
       "react": "^18.2.0",
       "react-dom": "^18.2.0",
       "react-router-dom": "^6.20.0",
       "@tanstack/react-query": "^5.28.0",
       "@tanstack/react-table": "^8.13.0",
       "axios": "^1.6.2"
     },
     "devDependencies": {
       "vite": "^5.0.8",
       "typescript": "^5.3.3",
       "@types/react": "^18.2.37",
       "@types/react-dom": "^18.2.15",
       "@vitejs/plugin-react": "^4.2.1",
       "tailwindcss": "^3.4.0",
       "postcss": "^8.4.32",
       "autoprefixer": "^10.4.16",
       "eslint": "^8.55.0",
       "eslint-plugin-react": "^7.33.2"
     }
   }
   ```

3. Create `frontend/vite.config.ts`:
   - React plugin enabled
   - Port 5173 (default)
   - Proxy to `http://localhost:8000/api` for development

4. Create `frontend/tsconfig.json`:
   - `strict: true`
   - `jsx: "react-jsx"`
   - `moduleResolution: "bundler"`
   - `isolatedModules: true`

5. Create `frontend/tailwind.config.ts`:
   - Dark theme base (background: `#0D1117`, text: light gray)
   - Color palette for Shodan aesthetic
   - Dark mode enabled

6. Create `frontend/index.html`:
   - Vite entry point
   - `<div id="root"></div>`
   - Script tag for `src/main.tsx`

7. Create `frontend/src/main.tsx`:
   - React StrictMode
   - Root render

8. Create `frontend/src/App.tsx`:
   - React Router with stubs for `/search`, `/browse`, `/batch`

9. Create `.env.example` in repository root:
   ```bash
   # ============= DATABASE =============
   DATABASE_URL=postgresql://cyperf_dev:cyperf_dev_password@localhost:5432/cyperf_cve_dev

   # ============= REDIS =============
   REDIS_URL=redis://localhost:6379/0

   # ============= NVD API =============
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

**Verify:**
```bash
# .env.example is present and contains all required vars
grep -q "CYPERF_CONTROLLER_IP" .env.example && echo "✓ .env.example valid"

# package.json is valid JSON
python -m json.tool frontend/package.json > /dev/null 2>&1 && echo "✓ package.json valid"

# tsconfig.json is valid
python -m json.tool frontend/tsconfig.json > /dev/null 2>&1 && echo "✓ tsconfig.json valid"
```

**Done:** Frontend skeleton exists with TypeScript strict mode, Tailwind dark theme configured, and React Router stubs. Root `.env.example` is present with all required environment variable keys.

---

### Task 1.4: Docker Compose + Dockerfile Configuration

**Goal:** Define multi-container orchestration for local development (PostgreSQL, Redis, FastAPI API) with health checks and automatic service startup.

**Depends on:** Task 1.2 (backend skeleton with Dockerfile location)

**Files Created/Modified:**
- `Dockerfile` (in `backend/` directory)
- `docker-compose.yml` (in repository root)
- `.dockerignore` (prevent unnecessary context copy)

**Action:**
1. Create `backend/Dockerfile`:
   ```dockerfile
   FROM python:3.12-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       postgresql-client \
       && rm -rf /var/lib/apt/lists/*

   # Install Python package manager
   RUN pip install uv

   # Copy and install Python dependencies
   COPY requirements.txt .
   RUN uv pip install --system -r requirements.txt

   # Copy application code
   COPY . .

   # Health check: API responds to /health
   HEALTHCHECK --interval=5s --timeout=10s --retries=5 \
     CMD curl -f http://localhost:8000/health || exit 1

   # Start Uvicorn
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. Create `.dockerignore`:
   ```
   .git
   .github
   __pycache__
   *.pyc
   *.pyo
   .pytest_cache
   .venv
   venv
   env
   node_modules
   .DS_Store
   .env
   .env.local
   *.db
   *.sqlite
   dist/
   build/
   *.egg-info/
   .coverage
   ```

3. Create `docker-compose.yml`:
   ```yaml
   version: '3.9'

   services:
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

     api:
       build:
         context: ./backend
         dockerfile: Dockerfile
       container_name: cyperf_api_dev
       command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
       ports:
         - "8000:8000"
       environment:
         DATABASE_URL: postgresql://cyperf_dev:cyperf_dev_password@postgres:5432/cyperf_cve_dev
         REDIS_URL: redis://redis:6379/0
         NVD_API_KEY: ${NVD_API_KEY}
         CYPERF_CONTROLLER_IP: ${CYPERF_CONTROLLER_IP}
         CYPERF_USERNAME: ${CYPERF_USERNAME}
         CYPERF_PASSWORD: ${CYPERF_PASSWORD}
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

4. Ensure `requirements.txt` includes `curl` equivalent (use `httpx` or test manually with API calls)

**Verify:**
```bash
# Dockerfile syntax is valid (docker won't build if it's wrong)
docker build -t test-cyperf-api ./backend 2>&1 | head -20

# docker-compose.yml syntax is valid
docker-compose config > /dev/null 2>&1 && echo "✓ docker-compose.yml valid"

# All required env vars are referenced
grep -o '\${[A-Z_]*}' docker-compose.yml | sort -u | while read var; do
  grep -q "${var:2:-1}" .env.example && echo "✓ $var in .env.example"
done
```

**Done:** `docker-compose.yml` can be parsed without errors. `docker-compose up -d` will attempt to start all three services (postgres, redis, api). All environment variables reference keys in `.env.example`.

---

### Task 1.5: Initialize Alembic Migrations + Database Schema

**Goal:** Set up database versioning and create initial migration that defines all Phase 1 tables: `cves`, `cyperf_supported_cves`, `sync_metadata`.

**Depends on:** Task 1.2 (backend structure exists)

**Files Created/Modified:**
- `backend/migrations/` (Alembic directory, auto-generated by alembic init)
- `backend/migrations/env.py` (Alembic environment config, customized)
- `backend/alembic.ini` (Alembic configuration)
- `backend/migrations/versions/001_initial_schema.py` (first migration)
- `backend/db/cve.py` (SQLAlchemy ORM model)
- `backend/db/cyperf_mapping.py` (SQLAlchemy ORM model)
- `backend/db/sync_metadata.py` (SQLAlchemy ORM model)

**Action:**
1. Install alembic: `pip install alembic==1.13.1` (or run in docker)

2. Run `alembic init migrations` to scaffold Alembic directory

3. Modify `backend/alembic.ini`:
   - Set `sqlalchemy.url = driver://user:pass@localhost/dbname` (will be overridden at runtime)
   - Keep other defaults

4. Modify `backend/migrations/env.py`:
   - Import `Base` from `database.py`
   - Import all model definitions (cve, cyperf_mapping, sync_metadata)
   - Set `target_metadata = Base.metadata`
   - Ensure `run_migrations_offline()` and `run_migrations_online()` are correct

5. Create SQLAlchemy ORM models in `backend/db/`:

   **`backend/db/cve.py`:**
   ```python
   from sqlalchemy import Column, VARCHAR, TEXT, DateTime, Numeric, Index
   from sqlalchemy.sql import func
   from database import Base

   class CVE(Base):
       __tablename__ = "cves"

       id = Column(VARCHAR(20), primary_key=True)
       description = Column(TEXT)
       published_date = Column(DateTime(timezone=True))
       last_modified = Column(DateTime(timezone=True))

       cvss_v3_vector = Column(VARCHAR(100))
       cvss_v3_score = Column(Numeric(3, 1))
       cvss_v3_severity = Column(VARCHAR(20))

       cvss_v4_vector = Column(VARCHAR(100))
       cvss_v4_score = Column(Numeric(4, 2))
       cvss_v4_severity = Column(VARCHAR(20))

       references = Column(TEXT)

       first_seen = Column(DateTime, server_default=func.now())
       last_updated = Column(DateTime, server_default=func.now())

       __table_args__ = (
           Index('idx_cve_published', 'published_date'),
           Index('idx_cve_severity', 'cvss_v3_severity'),
       )
   ```

   **`backend/db/cyperf_mapping.py`:**
   ```python
   from sqlalchemy import Column, Integer, VARCHAR, DateTime, Boolean, ForeignKey, Index
   from sqlalchemy.sql import func
   from database import Base

   class CyperfSupportedCVE(Base):
       __tablename__ = "cyperf_supported_cves"

       id = Column(Integer, primary_key=True, autoincrement=True)
       cve_id = Column(VARCHAR(20), ForeignKey('cves.id', ondelete='CASCADE'), unique=True, nullable=False)

       attack_profile_name = Column(VARCHAR(255), nullable=False)
       attack_profile_id = Column(VARCHAR(100))
       profile_version = Column(VARCHAR(50))

       first_synced = Column(DateTime, server_default=func.now())
       last_synced = Column(DateTime)
       is_deprecated = Column(Boolean, default=False)

       __table_args__ = (
           Index('idx_cyperf_cve', 'cve_id'),
           Index('idx_cyperf_profile', 'attack_profile_name'),
       )
   ```

   **`backend/db/sync_metadata.py`:**
   ```python
   from sqlalchemy import Column, Integer, VARCHAR, DateTime, Text, UniqueConstraint, Index
   from sqlalchemy.sql import func
   from database import Base

   class SyncMetadata(Base):
       __tablename__ = "sync_metadata"

       id = Column(Integer, primary_key=True, autoincrement=True)
       job_name = Column(VARCHAR(50), nullable=False, unique=True)

       last_run_at = Column(DateTime)
       last_completed_at = Column(DateTime)

       status = Column(VARCHAR(20))
       error_message = Column(Text)
       profiles_synced = Column(Integer)

       next_scheduled_run = Column(DateTime)
       created_at = Column(DateTime, server_default=func.now())

       __table_args__ = (
           Index('idx_sync_job', 'job_name'),
       )
   ```

6. Create `backend/db/__init__.py` and import all models:
   ```python
   from .cve import CVE
   from .cyperf_mapping import CyperfSupportedCVE
   from .sync_metadata import SyncMetadata

   __all__ = ["CVE", "CyperfSupportedCVE", "SyncMetadata"]
   ```

7. Create `backend/migrations/versions/001_initial_schema.py`:
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
       op.create_index('idx_cve_published', 'cves', ['published_date'])
       op.create_index('idx_cve_severity', 'cves', ['cvss_v3_severity'])

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
       op.create_index('idx_cyperf_cve', 'cyperf_supported_cves', ['cve_id'])
       op.create_index('idx_cyperf_profile', 'cyperf_supported_cves', ['attack_profile_name'])

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
       op.create_index('idx_sync_job', 'sync_metadata', ['job_name'])

   def downgrade():
       op.drop_table('sync_metadata')
       op.drop_table('cyperf_supported_cves')
       op.drop_table('cves')
   ```

**Verify:**
```bash
cd backend

# Can import Alembic without error
python -c "from alembic.config import Config; Config('alembic.ini')"

# Can list migrations
alembic current  # Should show base

# Migration file exists
test -f migrations/versions/001_initial_schema.py && echo "✓ Migration file exists"

# ORM models can be imported
python -c "from db import CVE, CyperfSupportedCVE, SyncMetadata; print('✓ ORM models import')"
```

**Done:** Alembic is initialized and migration `001_initial_schema.py` is ready. Running `alembic upgrade head` will create all three tables.

---

### Task 1.6: Implement Health Check Endpoints + Service Readiness

**Goal:** Create `/health`, `/health/redis`, `/health/db` endpoints that verify all critical services (API, Redis, database) are operational.

**Depends on:** Task 1.5 (database is configured)

**Files Created/Modified:**
- `backend/routes/health.py` (health check route handlers)
- `backend/services/health_service.py` (business logic for health checks)
- `backend/main.py` (register health routes + startup validation)

**Action:**
1. Create `backend/services/health_service.py`:
   ```python
   from typing import Dict, Any
   import redis.asyncio as redis
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import text

   async def check_redis(redis_url: str) -> Dict[str, Any]:
       """Verify Redis connectivity."""
       try:
           r = redis.from_url(redis_url)
           await r.ping()
           await r.close()
           return {"status": "ok", "service": "redis"}
       except Exception as e:
           return {"status": "error", "service": "redis", "error": str(e)}

   async def check_database(db: AsyncSession) -> Dict[str, Any]:
       """Verify database connectivity."""
       try:
           result = await db.execute(text("SELECT 1"))
           return {"status": "ok", "service": "database"}
       except Exception as e:
           return {"status": "error", "service": "database", "error": str(e)}
   ```

2. Create `backend/routes/health.py`:
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from sqlalchemy.ext.asyncio import AsyncSession
   from config import get_settings
   from database import get_db
   from services.health_service import check_redis, check_database

   router = APIRouter(prefix="/health", tags=["health"])

   @router.get("/")
   async def health_check() -> dict:
       """Basic liveness check."""
       return {"status": "ok"}

   @router.get("/redis")
   async def redis_health() -> dict:
       """Check Redis connectivity."""
       settings = get_settings()
       result = await check_redis(settings.redis_url)
       if result["status"] != "ok":
           raise HTTPException(status_code=503, detail=result)
       return result

   @router.get("/db")
   async def db_health(db: AsyncSession = Depends(get_db)) -> dict:
       """Check database connectivity."""
       result = await check_database(db)
       if result["status"] != "ok":
           raise HTTPException(status_code=503, detail=result)
       return result
   ```

3. Update `backend/main.py`:
   ```python
   from fastapi import FastAPI
   from config import get_settings
   from routes.health import router as health_router
   import logging

   # Initialize settings (validates Cyperf credentials at import time)
   settings = get_settings()
   logging.info(f"✓ Configuration loaded ({settings.environment} mode)")
   logging.info(f"✓ Cyperf Controller: {settings.cyperf_controller_ip}")

   app = FastAPI(
       title="Cyperf CVE Tracker API",
       description="Query CVE data and Cyperf testability status"
   )

   # Register routes
   app.include_router(health_router)

   @app.on_event("startup")
   async def startup_event():
       logging.info("✓ Application startup complete")
   ```

4. Update `backend/database.py` to export `get_db` dependency:
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
   from config import get_settings
   from typing import AsyncGenerator

   settings = get_settings()
   engine = create_async_engine(settings.database_url, echo=False)

   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       async with AsyncSession(engine) as session:
           yield session
   ```

**Verify:**
```bash
# Can start API (use timeout; will fail if cyperf vars missing)
cd backend
timeout 5 python -m uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | grep -q "Application startup complete" || true

# Health endpoints are registered
python -c "from main import app; routes = [r.path for r in app.routes]; assert '/health' in routes; print('✓ Health routes registered')"
```

**Done:** Health check endpoints are implemented and registered. Running the API will log startup messages and expose `/health`, `/health/redis`, `/health/db` endpoints.

---

### Task 1.7: Docker Stack Verification + Final Phase 1 Validation

**Goal:** Verify that `docker-compose up -d` starts all services without errors, database migrations run cleanly, and all Phase 1 success criteria are satisfied.

**Depends on:** All previous tasks (1.1-1.6)

**Files Created/Modified:**
- (None — this is verification only)

**Action:**
1. **Environment Setup:**
   ```bash
   # Copy .env.example to .env
   cp .env.example .env

   # Fill in required Cyperf credentials in .env
   # (For development/testing, use placeholder values)
   sed -i '' 's/CYPERF_CONTROLLER_IP=.*/CYPERF_CONTROLLER_IP=192.168.1.100/' .env
   sed -i '' 's/CYPERF_USERNAME=.*/CYPERF_USERNAME=admin/' .env
   sed -i '' 's/CYPERF_PASSWORD=.*/CYPERF_PASSWORD=admin123/' .env
   ```

2. **Docker Stack Startup:**
   ```bash
   # Start services in background
   docker-compose up -d

   # Wait for services to be healthy (max 30 seconds)
   for i in {1..30}; do
       postgres_healthy=$(docker-compose ps postgres | grep -q "healthy" && echo 1 || echo 0)
       redis_healthy=$(docker-compose ps redis | grep -q "healthy" && echo 1 || echo 0)
       api_running=$(docker-compose ps api | grep -q "Up" && echo 1 || echo 0)

       if [[ $postgres_healthy == 1 && $redis_healthy == 1 && $api_running == 1 ]]; then
           echo "✓ All services healthy within 30 seconds"
           break
       fi
       sleep 1
   done
   ```

3. **Database Migration:**
   ```bash
   # Run migrations inside API container
   docker-compose exec api alembic upgrade head

   # Verify tables exist
   docker-compose exec postgres psql -U cyperf_dev -d cyperf_cve_dev -c "\dt"
   # Should output: cves, cyperf_supported_cves, sync_metadata
   ```

4. **Service Health Verification:**
   ```bash
   # Redis connectivity check
   docker-compose exec redis redis-cli ping
   # Expected: PONG

   # Database connectivity check
   docker-compose exec postgres psql -U cyperf_dev -d cyperf_cve_dev -c "SELECT 1"
   # Expected: 1 row

   # API health endpoints
   curl -s http://localhost:8000/health | python -m json.tool
   # Expected: {"status": "ok"}

   curl -s http://localhost:8000/health/redis | python -m json.tool
   # Expected: {"status": "ok", "service": "redis"}

   curl -s http://localhost:8000/health/db | python -m json.tool
   # Expected: {"status": "ok", "service": "database"}
   ```

5. **Credentials Validation Check:**
   ```bash
   # Verify startup logs contain credential validation
   docker-compose logs api | grep -i "cyperf\|credentials\|configuration"

   # Should show "✓ All required credentials configured" or similar
   ```

6. **Pre-Commit Hook Verification:**
   ```bash
   # Test that .env file is rejected by pre-commit
   echo "TEST=value" > test_secret.env
   git add test_secret.env
   pre-commit run --all-files 2>&1 | grep -q "detect-secrets" && echo "✓ Secret detection active"
   git reset HEAD test_secret.env 2>/dev/null
   rm test_secret.env
   ```

7. **Phase 1 Success Criteria Checklist:**
   ```bash
   echo "=== PHASE 1 COMPLETION CHECKLIST ==="

   # 1. Docker compose up starts full stack
   docker-compose ps | grep -q "postgres.*healthy" && echo "✓ PostgreSQL healthy"
   docker-compose ps | grep -q "redis.*healthy" && echo "✓ Redis healthy"
   docker-compose ps | grep -q "api.*Up" && echo "✓ API running"

   # 2. Cyperf credentials validated at startup
   docker-compose logs api | grep -i "configuration loaded" && echo "✓ Config validated"

   # 3. Database schema migrations clean
   docker-compose exec postgres psql -U cyperf_dev -d cyperf_cve_dev -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" | grep -q "3" && echo "✓ All 3 tables exist"

   # 4. Redis reachable + health check works
   curl -s http://localhost:8000/health/redis | grep -q "ok" && echo "✓ Redis health check works"

   # 5. Pre-commit hooks reject .env files
   grep -q ".env" .gitignore && echo "✓ .env in .gitignore"
   test -f .git/hooks/pre-commit && echo "✓ Pre-commit hooks installed"
   ```

8. **Cleanup (if successful):**
   ```bash
   # Optional: stop stack for next developer
   docker-compose down
   # Keep volumes: do NOT use `down -v` (preserves database for testing)
   ```

**Verify:**
```bash
# All success criteria pass (see checklist above)
# All 3 tables exist
# Health endpoints return 200
# Logs show no errors
# Pre-commit hooks are active
```

**Done:** Docker stack successfully starts with all services healthy. Database migrations run without errors. All three tables exist. Health check endpoints return 200. Pre-commit hooks are installed and block credential commits.

---

## Dependency Graph & Wave Structure

```
Wave 1 (Parallel, no dependencies):
  ├── Task 1.1: Git + Pre-commit
  ├── Task 1.2: Backend skeleton
  ├── Task 1.3: Frontend skeleton + .env.example
  └── Task 1.4: Docker Compose + Dockerfile

Wave 2 (Sequential, depends on Wave 1):
  └── Task 1.5: Alembic + Database schema (depends on 1.2)

Wave 3 (Sequential, depends on Wave 2):
  ├── Task 1.6: Health check endpoints (depends on 1.5)
  └── Task 1.7: Final verification (depends on 1.1-1.6)
```

### Critical Dependencies
- **Task 1.5** needs Task 1.2 (backend structure + Dockerfile)
- **Task 1.4** needs Task 1.2 (Dockerfile location)
- **Task 1.6** needs Task 1.5 (database configured)
- **Task 1.7** needs all previous tasks

### Can Run in Parallel
- Tasks 1.1, 1.2, 1.3, 1.4 have no dependencies on each other (create separate files)

---

## Goal-to-Task Mapping

| Phase Success Criteria | Tasks | Verification |
|------------------------|-------|--------------|
| `docker compose up` starts full stack | 1.2, 1.4, 1.7 | `docker-compose ps` shows all healthy |
| Cyperf credentials loaded + validated | 1.2, 1.6, 1.7 | Startup logs show "✓ Credentials configured" |
| Database schema migrations clean | 1.5, 1.7 | `alembic upgrade head` completes; all 3 tables exist |
| Redis reachable + health check works | 1.4, 1.6, 1.7 | `curl http://localhost:8000/health/redis` returns 200 |
| Pre-commit hooks reject .env files | 1.1, 1.7 | `git add .env` followed by `pre-commit run` fails |

---

## Risk Mitigation

| Risk | Mitigation | Task |
|------|-----------|------|
| `.env` accidentally committed | Pre-commit hooks (detect-secrets) + .gitignore | 1.1 |
| Docker image won't build | Test Dockerfile locally before docker-compose | 1.4 |
| Cyperf creds missing at startup | Settings validation in config.py; raise ValueError | 1.2 |
| Database migrations fail | Use Alembic; test on fresh PostgreSQL instance | 1.5 |
| Health endpoints broken | Simple implementations; test manually before Task 1.7 | 1.6 |
| Services can't reach each other | Docker network (bridge mode) + depends_on health checks | 1.4 |

---

## Summary

**Phase 1 Plan:** 7 focused tasks breaking down to 3 execution waves.

**Wave 1** (parallel): Git + pre-commit, backend skeleton, frontend skeleton, docker compose
**Wave 2** (sequential): Alembic + database schema
**Wave 3** (sequential): Health endpoints + verification

**Estimated Effort:** 6-8 hours solo developer (mostly file creation + docker startup time).

**Acceptance:** All 5 phase success criteria satisfied; full stack starts with `docker compose up -d`; credentials validated; schema migrations clean; pre-commit hooks active.

---

*Plan created: 2026-02-22*
*Aligned with RESEARCH.md and ROADMAP.md*
