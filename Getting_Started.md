# Getting Started — CyperfBuddy

A guide for setting up the project locally (dev) and deploying it to a production server.

---

## What Is This?

**CyperfBuddy** is a CVE intelligence platform that cross-references NVD vulnerability data with Ixia CyPerf attack simulation profiles. It shows you which CVEs have ready-made CyPerf test profiles so you can prioritize your testing. It also includes the **L4-7 Test Advisor**, an AI-assisted scenario-to-profile recommendation engine powered by Google Gemini.

---

## Architecture

### Development Mode

```
Browser
  └─ Vite dev server (:5174)
       ├─ /api/l47/* ──proxy──▶ Agent Service (FastAPI :8001)  ← Docker
       ├─ /api/*     ──proxy──▶ Backend API  (FastAPI :8000)   ← Docker
       └─ /admin/*   ──proxy──▶ Backend API  (FastAPI :8000)   ← Docker
                                     │
                               PostgreSQL 15 + Redis 7         ← Docker
                                     │
                         CyPerf Controller + NVD API (external)
```

The Vite dev server handles the proxy in development. The frontend runs on the host; all backend services run in Docker.

### Production Mode

```
Browser
  └─ nginx (:80)                                               ← Docker
       ├─ /api/l47/* ──proxy──▶ Agent Service (FastAPI :8001)  ← Docker
       ├─ /api/*     ──proxy──▶ Backend API  (FastAPI :8000)   ← Docker
       ├─ /admin/*   ──proxy──▶ Backend API  (FastAPI :8000)   ← Docker
       └─ /*         ──serve──▶ React SPA (built dist/)
                                     │
                               PostgreSQL 15 + Redis 7         ← Docker
```

In production, nginx replaces the Vite proxy. The React app is compiled into static files and served directly by nginx. Everything runs in Docker Compose — no Node.js required on the host.

### Service Summary

| Service | Container | Port | Role |
|---------|-----------|------|------|
| Frontend (prod) | `cyperf_frontend` | 80 | nginx — serves SPA + proxies API calls |
| Backend API | `cyperf_api` | 8000 | FastAPI — CVE search, sync, admin |
| Agent Service | `cyperf_agent_l47` | 8001 | FastAPI + Gemini — L4-7 Test Advisor |
| PostgreSQL | `cyperf_db` | 5432 | Primary database |
| Redis | `cyperf_cache` | 6379 | Cache + rate limiting |

---

## Prerequisites

Install these on your machine before anything else.

### 1. Docker + Docker Compose

```bash
# Install Docker Engine (Debian/Ubuntu)
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow running docker without sudo (log out and back in after this)
sudo usermod -aG docker $USER
```

Verify:
```bash
docker --version          # Docker version 24+
docker compose version    # Docker Compose version v2+
```

### 2. Node.js 20+ (dev only — not needed for production)

```bash
# Using nvm (recommended — avoids system conflicts)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
node --version   # v20.x.x
npm --version    # 10.x.x
```

### 3. Python 3.12 (optional — only needed to run backend tests locally)

The backend runs inside Docker, so Python on the host is only needed for running `pytest` or `ruff` locally.

```bash
sudo apt-get install -y python3.12 python3.12-venv python3-pip
python3.12 --version
```

---

## Local Development Setup

### Step 1 — Clone the Repo

```bash
git clone <repo-url> cyperfbuddy
cd cyperfbuddy
```

### Step 2 — Set Up Environment Variables

```bash
cp .env.example .env
nano .env
```

#### Required Fields

| Variable | What to put | Where to get it |
|----------|-------------|--------------------|
| `CYPERF_CONTROLLER_IP` | IP of your CyPerf Controller | Your lab / Keysight |
| `CYPERF_USERNAME` | CyPerf login username | Your lab / Keysight |
| `CYPERF_PASSWORD` | CyPerf login password | Your lab / Keysight |
| `GEMINI_API_KEY` | Google Gemini API key | [aistudio.google.com](https://aistudio.google.com/app/apikey) |

#### Optional Fields

| Variable | Default | Notes |
|----------|---------|-------|
| `NVD_API_KEY` | *(empty)* | Free key from [nvd.nist.gov](https://nvd.nist.gov/developers/request-an-api-key). Without it, NVD rate-limits to 5 req/30s. |
| `SMTP_*` | *(empty)* | Only needed if you want the contact form to send emails. |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` during development. |

> **Note:** `DATABASE_URL` and `REDIS_URL` in `.env` point to `localhost` — these are for running the backend outside Docker. Inside Docker Compose, services communicate over `cyperf_network` using service names (`postgres`, `redis`).

### Step 3 — Start All Services

```bash
chmod +x start.sh stop.sh
./start.sh
```

This script:
1. Verifies Docker daemon is running
2. Starts `postgres`, `redis`, `api`, and `agent` containers via Docker Compose (`--build`)
3. Waits for `GET /health` to respond — up to 10 attempts with 2s delay
4. Runs `npm install` in `frontend/` and starts the Vite dev server on port 5174

When ready:
```
Services running:
  API:      http://localhost:8000
  API docs: http://localhost:8000/docs
  Agent:    http://localhost:8001
  Frontend: http://localhost:5174

Stop with: ./stop.sh
```

> The Vite dev server runs in the foreground. Open a second terminal for further commands.

### Step 4 — Run Database Migrations

On a fresh database, run migrations inside the API container:

```bash
docker exec cyperf_api alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_create_cves, create cves table
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002_create_sync_metadata, ...
...
INFO  [alembic.runtime.migration] Running upgrade 005 -> 006_create_system_config, ...
```

### Step 5 — Verify Everything Is Working

```bash
# Backend health
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

```bash
# Agent health
curl -s http://localhost:8001/health

# All containers
docker compose ps
```

All containers (`cyperf_db`, `cyperf_cache`, `cyperf_api`, `cyperf_agent_l47`) should show `healthy` or `running`.

Open `http://localhost:5174` — you should see the CVE search page.

### Step 6 — Configure CyPerf Endpoint and Sync

The CyPerf Controller IP can be set at runtime through the UI:

1. Open `http://localhost:5174`
2. Click the **Settings** gear icon in the right-side sync widget
3. Enter your CyPerf Controller IP and click **Save**
4. Click **Sync Data** to pull attack profiles and map them to CVEs

A full sync takes 30–120 seconds. Status is polled automatically; a toast appears on completion.

---

## Production Deployment

### Recommended: VPS with Docker Compose

The entire stack (nginx, FastAPI, agent, PostgreSQL, Redis) runs via a single `docker compose up`. No Node.js is needed on the server — the React app is compiled inside Docker during the build.

**Recommended server specs:** 2 vCPU, 4 GB RAM minimum. Suggested providers:

| Provider | Tier | Cost |
|----------|------|------|
| [Hetzner Cloud CX22](https://www.hetzner.com/cloud) | 2 vCPU / 4 GB | ~$4/mo |
| [DigitalOcean Droplet](https://digitalocean.com) | 2 vCPU / 4 GB | ~$12/mo |
| [AWS EC2 t3.medium](https://aws.amazon.com) | 2 vCPU / 4 GB | ~$15/mo |

### Step 1 — Provision the Server

```bash
# SSH into your VPS
ssh root@YOUR_SERVER_IP

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, then verify:
docker compose version
```

### Step 2 — Clone the Repo

```bash
git clone <repo-url> cyperfbuddy
cd cyperfbuddy
```

### Step 3 — Configure Environment

```bash
cp .env.example .env
nano .env   # fill in all required secrets
```

All the same variables as development apply. Make sure `GEMINI_API_KEY` is set — the agent service exits on startup without it.

### Step 4 — Build and Start Everything

> **⚠ Important:** On the server, always use `docker compose up -d --build` directly.
> **Never run `./start.sh` on a production server** — that script starts the Vite dev server
> as a foreground process that will die the moment you close your SSH session.

```bash
docker compose up -d --build
```

The `-d` flag (detached) runs all containers in the background. Your SSH session can be
closed immediately after — the containers keep running. Every service in `docker-compose.yml`
has `restart: unless-stopped`, which means:

- SSH disconnect → **no effect on containers**
- Server reboot → **all containers auto-restart automatically**
- Manual `docker compose down` → containers stop (data preserved in volumes)

To confirm everything is still running after reconnecting to SSH:

```bash
docker compose ps   # all 5 should show "running" or "healthy"
```

What this builds and starts:

| Container | Built from | What happens |
|-----------|-----------|------|
| `cyperf_frontend` | `frontend/Dockerfile` | Node 20 compiles the React app, copies `dist/` into nginx |
| `cyperf_api` | `backend/Dockerfile` | Python 3.12 installs deps, starts uvicorn on :8000 |
| `cyperf_agent_l47` | `agent-service/Dockerfile` | Python 3.12 installs deps, starts uvicorn on :8001 |
| `cyperf_db` | `postgres:15-alpine` | PostgreSQL with persistent volume |
| `cyperf_cache` | `redis:7-alpine` | Redis with persistent volume |

nginx (inside `cyperf_frontend`) proxies:
- `/api/l47/*` → `http://agent:8001/api/l47/` (L4-7 Advisor)
- `/api/*` → `http://api:8000/` (main backend, prefix stripped)
- `/admin/*` → `http://api:8000/admin/` (admin routes)
- `/*` → React SPA (`index.html` fallback for client-side routing)

### Step 5 — Run Database Migrations

```bash
docker exec cyperf_api alembic upgrade head
```

This must be run once on a fresh database. Re-running on an already-migrated database is safe (Alembic is idempotent).

### Step 6 — Verify

```bash
# All 5 containers should be healthy/running
docker compose ps

# Backend responds
curl -s http://YOUR_SERVER_IP/api/health

# Agent responds
curl -s http://YOUR_SERVER_IP/api/l47/health  # if health endpoint exists

# Open in browser
http://YOUR_SERVER_IP
```

### Step 7 — (Optional) Add a Domain + HTTPS

Use [Caddy](https://caddyserver.com/) as a reverse proxy in front of nginx — it handles SSL certificates automatically via Let's Encrypt:

```bash
# Install Caddy
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install caddy

# Point your domain at the server IP first, then:
caddy reverse-proxy --from cyperfbuddy.yourdomain.com --to localhost:80
```

Your app is now available at `https://cyperfbuddy.yourdomain.com`.

---

## Stopping Services

### Development

```bash
./stop.sh
```

Stops the Vite dev server and `redis`, `api`, `agent` containers. PostgreSQL is intentionally left running to preserve data.

```bash
# Also stop Postgres
docker compose stop postgres

# Tear down everything including volumes (wipes the database)
docker compose down -v
```

### Production

```bash
docker compose down          # stop and remove containers (data preserved in volumes)
docker compose down -v       # also wipe volumes (destroys the database)
```

---

## Development Workflow

### Backend changes

The `api` container does **not** hot-reload by default. After editing Python files:

```bash
docker compose up -d --build api
```

Or run the backend directly on the host for hot-reload:

```bash
docker compose up -d postgres redis   # keep DB and cache in Docker

cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Agent service changes

```bash
docker compose up -d --build agent
docker compose logs agent --tail=30
```

### Frontend changes

The Vite dev server hot-reloads on save. No restart needed.

To preview the production build locally:
```bash
cd frontend
npm run build
docker compose up -d --build frontend  # rebuild the nginx container
```

---

## Running Tests

### Backend tests

```bash
# Inside container
docker exec cyperf_api pytest tests/ -v

# Or locally with venv active
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Frontend tests

```bash
cd frontend
npm run test          # single run
npm run test:watch    # watch mode
npm run test:ui       # browser-based Vitest UI
```

---

## Project Layout

```
cyperfbuddy/
├── backend/
│   ├── main.py              # FastAPI app entry, router registration
│   ├── routes/              # HTTP handlers only (no business logic)
│   ├── services/            # Business logic (CVE, Sync, Cache, NVD, Email...)
│   ├── db/                  # SQLAlchemy ORM models
│   ├── migrations/          # Alembic migration scripts
│   ├── Dockerfile           # Python 3.12-slim → uvicorn :8000
│   └── requirements.txt
├── agent-service/           # Gemini-powered L4-7 Test Advisor
│   ├── main.py              # FastAPI entry point → uvicorn :8001
│   ├── recommendation_agent.py
│   ├── Dockerfile           # Python 3.12-slim → uvicorn :8001
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # Route-level page components
│   │   ├── components/      # Reusable UI components
│   │   └── hooks/useAPI.ts  # All React Query hooks + API calls
│   ├── public/              # Static assets (images served at root path)
│   ├── Dockerfile           # Node 20 build → nginx:alpine (prod only)
│   └── vite.config.ts       # Dev proxy config (/api, /admin, /api/l47 → local ports)
├── nginx.conf               # Production nginx: SPA serving + API proxy rules
├── docker-compose.yml       # Orchestrates all 5 services
├── netlify.toml             # Netlify config (frontend-only static deploy option)
├── .env.example             # Copy to .env and fill in secrets
├── start.sh                 # Start all services (dev mode)
└── stop.sh                  # Stop all services (dev mode)
```

---

## Common Issues

### `docker: permission denied`
```bash
sudo usermod -aG docker $USER
# Log out and log back in, then retry
```

### `API did not respond after 10 attempts`
```bash
docker compose logs api --tail=50
```
Common causes: missing env vars, migration not run, port 8000 in use.

### Agent service exits immediately
`GEMINI_API_KEY` is missing or invalid:
```bash
docker compose logs agent --tail=20
docker compose up -d --build agent   # after fixing .env
```

### `alembic upgrade head` — `relation does not exist`
```bash
docker exec cyperf_api alembic upgrade head
```

### Frontend shows blank page or API errors
```bash
curl http://localhost:8000/health    # dev
curl http://YOUR_SERVER_IP/api/health  # prod
```

### L4-7 Advisor returns no results / 502
The agent service on :8001 may be down:
```bash
docker compose ps          # check cyperf_agent_l47 status
docker compose logs agent  # check for GEMINI_API_KEY errors
```

### CyPerf sync fails immediately
- Verify `CYPERF_CONTROLLER_IP`, `CYPERF_USERNAME`, `CYPERF_PASSWORD` in `.env` or via Settings UI
- Test connectivity:
```bash
curl -k https://<CYPERF_CONTROLLER_IP>/api/v2/profiles
```

---

## Quick Reference

| Task | Command |
|------|---------|
| **Dev** | |
| Start everything | `./start.sh` |
| Stop everything | `./stop.sh` |
| **Production** | |
| Build + start all (survives SSH close) | `docker compose up -d --build` |
| Check still running after reconnect | `docker compose ps` |
| Stop (preserve data) | `docker compose down` |
| Wipe everything | `docker compose down -v` |
| ⚠ DO NOT use on server | `./start.sh` — dev only, dies on SSH close |
| **Operations** | |
| Check service health | `docker compose ps` |
| View API logs | `docker logs -f cyperf_api` |
| View agent logs | `docker logs -f cyperf_agent_l47` |
| View nginx logs | `docker logs -f cyperf_frontend` |
| Run DB migrations | `docker exec cyperf_api alembic upgrade head` |
| Run backend tests | `docker exec cyperf_api pytest tests/ -v` |
| Rebuild one service | `docker compose up -d --build <service>` |
| **URLs (dev)** | |
| Frontend | http://localhost:5174 |
| API Swagger UI | http://localhost:8000/docs |
| Agent health | http://localhost:8001/health |
| **URLs (prod)** | |
| Frontend | http://YOUR_SERVER_IP |
| API (via nginx) | http://YOUR_SERVER_IP/api/... |
| Agent (via nginx) | http://YOUR_SERVER_IP/api/l47/... |
