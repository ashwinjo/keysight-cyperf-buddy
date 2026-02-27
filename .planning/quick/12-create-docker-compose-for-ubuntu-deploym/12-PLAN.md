---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docker-compose.yml
  - OneClickStart.sh
autonomous: true
requirements: [DEPLOY-01]
must_haves:
  truths:
    - "Single command starts all services (backend + frontend) on Ubuntu Server"
    - "docker-compose.yml targets production: no --reload, no volume-mounted source code"
    - "Root-level stray files (apps_cyperf.py, info_fetch.py, __init__.py, openapispec.json.save, cyperf_cve.db) are removed"
    - "OneClickStart.sh exits non-zero with a clear message if Docker is not running"
    - "All services reachable after script completes: API :8000, Frontend :5174"
  artifacts:
    - path: "docker-compose.yml"
      provides: "Production-mode compose with built frontend served via Nginx"
    - path: "OneClickStart.sh"
      provides: "Single-command startup script for Ubuntu Server"
  key_links:
    - from: "OneClickStart.sh"
      to: "docker-compose.yml"
      via: "docker compose -f docker-compose.yml up"
      pattern: "docker compose.*up"
    - from: "docker-compose.yml api service"
      to: "backend/Dockerfile"
      via: "build context ./backend"
      pattern: "build:.*context.*backend"
---

<objective>
Prepare the project for Ubuntu Server deployment: rewrite docker-compose.yml for production
(no source-mount hot-reload), add a Nginx-based frontend container serving the Vite build,
write OneClickStart.sh as the single entry point, and delete stray root-level files that have
no place in a deployed repository.

Purpose: A developer or ops person on a fresh Ubuntu Server can clone the repo and run one
command to have the full stack running.

Output: docker-compose.yml (prod), OneClickStart.sh, cleaned repo root.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@docker-compose.yml
@backend/Dockerfile
@frontend/vite.config.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite docker-compose.yml for production Ubuntu deployment</name>
  <files>docker-compose.yml</files>
  <action>
    Replace the current development-mode docker-compose.yml with a production compose file.
    Key differences from current file:

    1. postgres service — keep as-is (image, healthcheck, network, volume). Change container
       name to `cyperf_db` (drop _dev suffix). Change env vars to use production names:
       POSTGRES_USER: cyperf, POSTGRES_PASSWORD: cyperf_password, POSTGRES_DB: cyperf_cve.
       Do NOT expose port 5432 on host (remove ports section — only internal access needed).

    2. redis service — keep image/healthcheck/network/volume. Change container name to
       `cyperf_cache`. Remove host port exposure (remove ports section).

    3. api service — change container name to `cyperf_api`. Remove the `command:` override
       (Dockerfile CMD runs uvicorn without --reload for prod). Remove the source-code volume
       mount (`- ./backend:/app`) so the image runs from baked-in code. Keep `build: context:
       ./backend`. Update env vars: DATABASE_URL uses new prod DB name/user/password. Set
       ENVIRONMENT: production. Keep CYPERF_* vars (operator must set real values via .env
       file or shell env). Keep port 8000:8000. Add `restart: unless-stopped`.

    4. Add a new `frontend` service:
       - image: nginx:alpine
       - container_name: cyperf_frontend
       - ports: "5174:80"
       - volumes: `- ./frontend/dist:/usr/share/nginx/html:ro`
       - depends_on: [api]
       - networks: [cyperf_network]
       - restart: unless-stopped
       - Add an inline nginx config via a named volume or a simple command override. Use a
         `command` to write a minimal nginx.conf that proxies /api and /admin to
         http://api:8000 and serves static files otherwise. Use the `volumes` approach with a
         local nginx config file: create `nginx.conf` in the repo root (see below).

    5. Keep volumes (postgres_data, redis_data) and networks (cyperf_network bridge) sections.

    Nginx config to create at repo root as `nginx.conf`:
    ```
    server {
        listen 80;
        root /usr/share/nginx/html;
        index index.html;

        location /api/ {
            proxy_pass http://api:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /admin/ {
            proxy_pass http://api:8000/admin/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
    ```

    Mount nginx.conf in the frontend service:
    `- ./nginx.conf:/etc/nginx/conf.d/default.conf:ro`

    Final docker-compose.yml structure (5 services: postgres, redis, api, frontend).
  </action>
  <verify>
    docker compose -f /Users/ashwin.joshi/claudeExp/docker-compose.yml config --quiet
    (must exit 0 with no errors)
  </verify>
  <done>
    `docker compose config` validates cleanly. No --reload flag anywhere. No source-code
    volume mounts on api. frontend service present referencing ./frontend/dist and nginx.conf.
    All services have restart: unless-stopped.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write OneClickStart.sh and remove stray root-level files</name>
  <files>
    OneClickStart.sh
  </files>
  <action>
    Part A — Create OneClickStart.sh at repo root:

    Script logic (bash, set -euo pipefail):

    1. Resolve SCRIPT_DIR (cd dirname $0 && pwd).

    2. Guard: check `docker info > /dev/null 2>&1` — if fails, print actionable message
       "ERROR: Docker is not running. On Ubuntu: sudo systemctl start docker" and exit 1.

    3. Guard: check `docker compose version > /dev/null 2>&1` — if fails, print
       "ERROR: docker compose plugin not found. Install: sudo apt install docker-compose-plugin"
       and exit 1.

    4. Build frontend:
       - Check if node/npm available: `command -v npm` — if missing, print
         "ERROR: npm not found. Install Node.js: https://nodejs.org" and exit 1.
       - `cd "$SCRIPT_DIR/frontend" && npm ci --silent && npm run build`
       - Print "Frontend built -> frontend/dist/"

    5. Start containers:
       `docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build --wait`
       Print "Backend containers started."

    6. Health poll (same pattern as existing start.sh — 10 attempts, 2s sleep, check
       http://localhost:8000/health with curl -sf):
       - Success: print "API healthy."
       - Failure after 10 attempts: print last 30 lines of api logs, exit 1.

    7. Print success banner:
       ```
       ================================================
        CyPerf CVE Tracker — Running
       ================================================
        API:       http://localhost:8000
        API docs:  http://localhost:8000/docs
        Frontend:  http://localhost:5174

        Stop: docker compose down
       ================================================
       ```

    chmod +x OneClickStart.sh.

    Part B — Delete stray root-level files that are not part of the application:
    - /Users/ashwin.joshi/claudeExp/apps_cyperf.py  (prototype/scratch script)
    - /Users/ashwin.joshi/claudeExp/info_fetch.py   (prototype/scratch script)
    - /Users/ashwin.joshi/claudeExp/__init__.py      (empty, not a package)
    - /Users/ashwin.joshi/claudeExp/openapispec.json.save  (scratch artifact)
    - /Users/ashwin.joshi/claudeExp/cyperf_cve.db   (empty dev SQLite artifact)
    - /Users/ashwin.joshi/claudeExp/__pycache__/     (compiled bytecache, not source)

    Do NOT delete: docker-compose.yml, nginx.conf, OneClickStart.sh, start.sh, stop.sh,
    ARCHITECTURE.md, DEPLOYMENT_GUIDE.md, skills-lock.json, backend/, frontend/, .planning/.

    Use `rm -rf` for __pycache__ directory, `rm -f` for individual files.
  </action>
  <verify>
    bash -n /Users/ashwin.joshi/claudeExp/OneClickStart.sh
    (syntax check must pass)

    ls /Users/ashwin.joshi/claudeExp/apps_cyperf.py 2>/dev/null && echo "FILE EXISTS - FAIL" || echo "Deleted OK"
    ls /Users/ashwin.joshi/claudeExp/info_fetch.py 2>/dev/null && echo "FILE EXISTS - FAIL" || echo "Deleted OK"
  </verify>
  <done>
    OneClickStart.sh exists, is executable, passes bash -n.
    apps_cyperf.py, info_fetch.py, __init__.py, openapispec.json.save, cyperf_cve.db,
    __pycache__/ are all absent from repo root.
    ls /Users/ashwin.joshi/claudeExp/ shows a clean root with only intentional files.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

1. `docker compose -f /Users/ashwin.joshi/claudeExp/docker-compose.yml config` — exits 0
2. `bash -n /Users/ashwin.joshi/claudeExp/OneClickStart.sh` — exits 0
3. `ls /Users/ashwin.joshi/claudeExp/` — no stray .py, .db, .save, __pycache__ at root
4. `cat /Users/ashwin.joshi/claudeExp/docker-compose.yml | grep -- '--reload'` — returns nothing
5. `cat /Users/ashwin.joshi/claudeExp/docker-compose.yml | grep 'restart'` — shows unless-stopped for api and frontend
6. nginx.conf exists at repo root
</verification>

<success_criteria>
- docker-compose.yml is production-grade: no hot-reload, no source mounts, frontend served via Nginx on :5174, api on :8000
- OneClickStart.sh exists, is executable, has guard clauses for Docker/npm/docker-compose availability
- Repo root is clean of prototype artifacts and empty files
- A developer can run `./OneClickStart.sh` on a fresh Ubuntu Server clone and reach the app
</success_criteria>

<output>
After completion, create `.planning/quick/12-create-docker-compose-for-ubuntu-deploym/12-SUMMARY.md`
with what was built, files changed, and any decisions made.
</output>
