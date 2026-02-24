# Plan: Create Unified Startup Script

**Type:** quick
**Goal:** Single script users run from the repo root to start all backend containers and the frontend dev server.

---

## Context

- **Backend:** `docker-compose.yml` at repo root — services: `postgres` (cyperf_db_dev), `redis` (cyperf_cache_dev), `api` (cyperf_api_dev on port 8000). Compose already has healthchecks defined.
- **Frontend:** React + Vite in `./frontend/`, started with `npm run dev` (port 5173 by default).
- **Integrations:** API container connects out to NVD and CyPerf controller at startup via scheduler.

---

## Tasks

### Task 1 — Write `start.sh` at repo root

Create `start.sh` (executable) that:

1. Runs `docker compose up -d --build` from repo root.
2. Waits for the API healthcheck to pass (poll `http://localhost:8000/health` or use `docker compose ps` exit codes).
3. Starts the frontend in the background (`npm run dev` inside `./frontend/`), capturing its PID.
4. Tails relevant logs or prints access URLs.

Key decisions:
- Use `--wait` flag on `docker compose up` (Compose v2.1+) to block until all healthchecks pass before proceeding — eliminates manual polling.
- Frontend is started with `&` and PID written to `.frontend.pid` for a clean `stop.sh` companion.
- Script must `cd` to its own directory (use `SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)`) so it works from any cwd.

Skeleton:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "==> Starting backend containers..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build --wait

echo "==> Backend healthy. Starting frontend dev server..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$SCRIPT_DIR/.frontend.pid"

echo ""
echo "Services running:"
echo "  API:      http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Stop with: ./stop.sh"

wait "$FRONTEND_PID"
```

Companion `stop.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

if [[ -f "$SCRIPT_DIR/.frontend.pid" ]]; then
  kill "$(cat "$SCRIPT_DIR/.frontend.pid")" 2>/dev/null || true
  rm "$SCRIPT_DIR/.frontend.pid"
fi

docker compose -f "$SCRIPT_DIR/docker-compose.yml" down
echo "All services stopped."
```

---

### Task 2 — Add basic health check verification

Before printing "Services running", add explicit endpoint verification so startup failures are surfaced clearly rather than silently continuing.

```bash
echo "==> Verifying API health endpoint..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "    API responded OK"
    break
  fi
  if [[ $i -eq 10 ]]; then
    echo "ERROR: API did not respond after 10 attempts. Check logs:"
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" logs api --tail=30
    exit 1
  fi
  sleep 2
done
```

Note: Confirm `/health` exists in `backend/main.py`. If only `/` or `/docs` responds, use that endpoint instead.

---

### Task 3 — Make it discoverable

- `chmod +x start.sh stop.sh` committed to repo.
- Add a brief "Quick Start" section to the top of `backend/QUICK_START.md` (already exists) pointing to `start.sh`.
- Or add to the existing `ARCHITECTURE.md` under a "Development" section.

No new README files needed — reuse existing docs.

---

## File Targets

| File | Action |
|---|---|
| `/start.sh` | Create |
| `/stop.sh` | Create |
| `/backend/QUICK_START.md` | Edit — add one-liner pointing to `start.sh` |

---

## Failure Modes to Handle

| Scenario | Mitigation |
|---|---|
| Docker daemon not running | `docker info` guard at top of script |
| Port 5173 or 8000 already bound | Script will fail fast via `--wait`; add port pre-check if needed |
| `node_modules` missing | `npm install` included before `npm run dev` |
| CyPerf controller unreachable | API container still starts; scheduler logs the error — not a startup blocker |
| Compose version < 2.1 (no `--wait`) | Fall back to polling loop in Task 2 |
