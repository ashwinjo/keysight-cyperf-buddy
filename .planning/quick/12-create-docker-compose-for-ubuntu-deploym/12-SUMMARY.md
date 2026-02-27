---
phase: quick-12
plan: "01"
subsystem: deployment
tags: [docker, nginx, production, ubuntu, deploy]
dependency_graph:
  requires: []
  provides: [ubuntu-server-deployment, production-compose, frontend-nginx-service]
  affects: [docker-compose.yml, nginx.conf, OneClickStart.sh]
tech_stack:
  added: [nginx:alpine frontend container]
  patterns: [nginx SPA proxy, docker compose prod, guard-clause shell scripts]
key_files:
  created:
    - docker-compose.yml (rewritten in-place for production)
    - nginx.conf
    - OneClickStart.sh
  modified:
    - docker-compose.yml (from dev → prod)
    - deleted info_fetch.py
    - deleted openapispec.json.save
decisions:
  - CYPERF_* env vars use shell variable expansion with empty defaults — operator sets real values via .env or host env
  - postgres and redis host ports removed — internal-only access via Docker bridge network
  - nginx:alpine for frontend — minimal image, SPA fallback, proxies /api/ and /admin/ to api:8000
  - OneClickStart.sh uses npm ci (not npm install) — reproducible builds from package-lock.json
  - apps_cyperf.py and cyperf_cve.db were untracked in git — only filesystem removal needed (no git rm)
metrics:
  duration: "~8 minutes"
  completed: "2026-02-27T17:13:16Z"
  tasks_completed: 2
  files_changed: 5
---

# Quick Task 12: Ubuntu Deployment Setup Summary

**One-liner:** Production docker-compose.yml with Nginx frontend on :5174, OneClickStart.sh with Docker/npm guards, and repo root cleaned of all prototype artifacts.

---

## What Was Built

### Task 1: Production docker-compose.yml + nginx.conf

Rewrote the development-mode compose file to production-grade:

**docker-compose.yml changes:**
- `cyperf_db_dev` -> `cyperf_db`, dev credentials -> production credentials (`cyperf`/`cyperf_password`/`cyperf_cve`)
- Removed host port exposure from postgres (5432) and redis (6379) — internal network only
- `cyperf_api_dev` -> `cyperf_api`, dropped `command: uvicorn ... --reload`, removed `./backend:/app` source mount
- CYPERF_* environment variables use `${VAR:-}` expansion — no hardcoded credentials in compose file
- `ENVIRONMENT: production` set explicitly
- `restart: unless-stopped` on all four services
- New `frontend` service: `nginx:alpine`, port `5174:80`, mounts `./frontend/dist` read-only and `./nginx.conf`

**nginx.conf (new file at repo root):**
- Proxies `/api/` -> `http://api:8000/` with Host and X-Real-IP headers
- Proxies `/admin/` -> `http://api:8000/admin/`
- SPA fallback: `try_files $uri $uri/ /index.html` for React Router

**Verification:** `docker compose config --quiet` exits 0.

---

### Task 2: OneClickStart.sh + repo root cleanup

**OneClickStart.sh (new, chmod +x):**

Three guard clauses at the top (each exits 1 with an actionable message):
1. `docker info` — Docker daemon check; instructs `sudo systemctl start docker`
2. `docker compose version` — plugin check; instructs `sudo apt install docker-compose-plugin`
3. `command -v npm` — Node.js check; points to nodejs.org

Execution flow:
1. `npm ci --silent && npm run build` in `frontend/` -> produces `frontend/dist/`
2. `docker compose up -d --build --wait` starts all four services
3. Health poll: 10 attempts with 2s sleep, curls `http://localhost:8000/health`; on failure dumps last 30 lines of api logs and exits 1
4. Success banner printed with API (:8000), docs (:8000/docs), Frontend (:5174) URLs and stop instruction

**Stray files removed:**
| File | Was tracked? | Removal |
|------|-------------|---------|
| `info_fetch.py` | Yes | `git rm` |
| `openapispec.json.save` | Yes | `git rm` |
| `apps_cyperf.py` | No (untracked) | `rm -f` |
| `cyperf_cve.db` | No (untracked) | `rm -f` |
| `__init__.py` | Not present | N/A |
| `__pycache__/` | Not present | N/A |

---

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Compose valid | `docker compose config --quiet` | PASS (exit 0) |
| Script syntax | `bash -n OneClickStart.sh` | PASS |
| No stray files | `ls /repo/root/` | PASS — only intentional files |
| No --reload | `grep -- '--reload' docker-compose.yml` | PASS — none found |
| restart present | `grep 'restart' docker-compose.yml` | PASS — 4 occurrences |
| nginx.conf exists | `ls nginx.conf` | PASS |

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `93b4ee8` | feat(quick-12): rewrite docker-compose.yml for production Ubuntu deployment |
| Task 2 | `f29b031` | feat(quick-12): add OneClickStart.sh and clean repo root of stray files |

---

## Deviations from Plan

None — plan executed exactly as written.

**Note:** `__init__.py` and `__pycache__/` listed in Task 2 as targets did not exist at the repo root — no action required.

`apps_cyperf.py` and `cyperf_cve.db` were untracked files (never committed to git), so `rm -f` on the filesystem was sufficient. `git rm` was only needed for `info_fetch.py` and `openapispec.json.save`.

---

## Self-Check: PASSED

- [x] `/Users/ashwin.joshi/claudeExp/docker-compose.yml` — exists, validates
- [x] `/Users/ashwin.joshi/claudeExp/nginx.conf` — exists
- [x] `/Users/ashwin.joshi/claudeExp/OneClickStart.sh` — exists, executable, passes bash -n
- [x] Commit `93b4ee8` — confirmed in git log
- [x] Commit `f29b031` — confirmed in git log
- [x] Root clean: no .py, .db, .save, __pycache__
