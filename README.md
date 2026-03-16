# CyperfBuddy

> CVE intelligence platform that maps NIST NVD vulnerabilities to Ixia CyPerf attack simulation profiles — so you know exactly which CVEs you can test right now.

---

## What It Does

Security teams know which CVEs matter. The harder question is: **do you have a test profile ready to simulate it?**

CyperfBuddy cross-references the [NVD vulnerability database](https://nvd.nist.gov/) against your CyPerf Controller's attack profile library in real time. Search a CVE ID, get back whether CyPerf can simulate it and which profile to use — no manual cross-referencing required.

It also ships with **L4-7 Test Advisor**, an AI assistant (powered by Google Gemini) that takes a plain-English description of your test scenario and recommends the most relevant CyPerf profiles ranked by relevance.

---

## Features

- **CVE Search** — search by CVE ID against NVD; results show CyPerf profile coverage instantly
- **Browse** — paginated table of all CVEs with mapped CyPerf strikes
- **AI Strikes** — AI-curated CVE suggestions based on threat patterns
- **Apps Catalog** — browse CyPerf application profiles
- **L4-7 Test Advisor** — describe your scenario in plain English, get ranked profile recommendations
- **Live Sync** — pull latest attack profiles from your CyPerf Controller on demand
- **CyPerf Automation 101** — quick-start hub: docs, deployment guides, SDK links, video tutorials
- **CyPerf Deployment Guide** — in-portal reference for deploying CyPerf infrastructure

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack React Query |
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, APScheduler |
| Agent Service | FastAPI + Google Gemini (L4-7 Test Advisor) |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Infrastructure | Docker Compose, nginx |

---

## Architecture

```
Browser
  └─ nginx :80                          (Docker — production)
  └─ Vite dev server :5174              (host — development)
       ├─ /api/l47/*  ──▶  Agent Service  (FastAPI :8001)
       ├─ /api/*      ──▶  Backend API    (FastAPI :8000)
       └─ /admin/*    ──▶  Backend API    (FastAPI :8000)
                                │
                          PostgreSQL 15 + Redis 7
                                │
                    CyPerf Controller  ·  NVD API
                       (external)         (external)
```

In production, everything runs as Docker containers. nginx serves the compiled React app and proxies API traffic — no Node.js required on the server.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- Node.js 20+ *(dev only — not needed for production)*

### Run locally

```bash
git clone <repo-url> cyperfbuddy
cd cyperfbuddy

cp .env.example .env
# Edit .env — set CYPERF_CONTROLLER_IP, CYPERF_USERNAME, CYPERF_PASSWORD, GEMINI_API_KEY

./start.sh
```

Open `http://localhost:5174`.

Then run DB migrations (first time only):

```bash
docker exec cyperf_api alembic upgrade head
```

### Deploy to a server (VPS)

```bash
# On your server (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh

git clone <repo-url> cyperfbuddy
cd cyperfbuddy

cp .env.example .env && nano .env

docker compose up -d --build
docker exec cyperf_api alembic upgrade head
```

Open `http://YOUR_SERVER_IP`. Containers run in the background and auto-restart on reboot.

> See [Getting_Started.md](Getting_Started.md) for the full setup guide including environment variables, domain + HTTPS setup, development workflow, and troubleshooting.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `CYPERF_CONTROLLER_IP` | Yes | IP address of your CyPerf Controller |
| `CYPERF_USERNAME` | Yes | CyPerf login username |
| `CYPERF_PASSWORD` | Yes | CyPerf login password |
| `GEMINI_API_KEY` | Yes | Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey)) |
| `NVD_API_KEY` | No | NVD API key — removes rate limiting ([request here](https://nvd.nist.gov/developers/request-an-api-key)) |
| `LOG_LEVEL` | No | `INFO` (default) or `DEBUG` |

---

## Project Structure

```
cyperfbuddy/
├── backend/            # FastAPI — CVE search, sync, admin (:8000)
├── agent-service/      # FastAPI + Gemini — L4-7 Test Advisor (:8001)
├── frontend/           # React SPA + Vite dev server (:5174)
├── nginx.conf          # Production reverse proxy config
├── docker-compose.yml  # Orchestrates all services
├── .env.example        # Environment variable template
├── start.sh            # Dev startup script
├── stop.sh             # Dev shutdown script
└── Getting_Started.md  # Full setup + deployment guide
```

---

## API Reference

Interactive Swagger UI is available at `http://localhost:8000/docs` when running locally.

| Prefix | Purpose |
|--------|---------|
| `GET /health` | Health check (DB + Redis status) |
| `GET /cves` | CVE search and browse |
| `POST /admin/sync-cyperf-now` | Trigger manual CyPerf profile sync |
| `GET /admin/sync-status` | Poll sync job status |
| `POST /admin/config/cyperf-endpoint` | Set CyPerf Controller IP at runtime |
| `POST /api/l47/recommend` | L4-7 Test Advisor — get profile recommendations |
| `GET /cyperf-apps` | CyPerf application profile catalog |

---

## License

Internal / proprietary — not for public distribution.
