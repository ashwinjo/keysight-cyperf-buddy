#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ── Guard: Docker daemon must be running ───────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker daemon is not running. Start Docker and retry."
  exit 1
fi

# ── Backend ────────────────────────────────────────────────────────────────────
echo "==> Starting backend containers (postgres, redis, api)..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build --wait

# ── Health verification ────────────────────────────────────────────────────────
echo "==> Verifying API health endpoint..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "    API responded OK (attempt $i)"
    break
  fi
  if [[ $i -eq 10 ]]; then
    echo "ERROR: API did not respond after 10 attempts. Last 30 log lines:"
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" logs api --tail=30
    exit 1
  fi
  echo "    Waiting for API... attempt $i/10"
  sleep 2
done

# ── Frontend ───────────────────────────────────────────────────────────────────
echo "==> Starting frontend dev server..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$SCRIPT_DIR/.frontend.pid"

echo ""
echo "Services running:"
echo "  API:      http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Frontend: http://localhost:5174"
echo ""
echo "Stop with: ./stop.sh"
echo ""

wait "$FRONTEND_PID"
