#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ── Guard: Docker daemon must be running ───────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker is not running. On Ubuntu: sudo systemctl start docker"
  exit 1
fi

# ── Guard: docker compose plugin must be available ────────────────────────────
if ! docker compose version > /dev/null 2>&1; then
  echo "ERROR: docker compose plugin not found. Install: sudo apt install docker-compose-plugin"
  exit 1
fi

# ── Guard: npm must be available ──────────────────────────────────────────────
if ! command -v npm > /dev/null 2>&1; then
  echo "ERROR: npm not found. Install Node.js: https://nodejs.org"
  exit 1
fi

# ── Build frontend ────────────────────────────────────────────────────────────
echo "==> Building frontend..."
cd "$SCRIPT_DIR/frontend" && npm ci --silent && npm run build
echo "    Frontend built -> frontend/dist/"

# ── Start containers ──────────────────────────────────────────────────────────
echo "==> Starting containers (postgres, redis, api, frontend)..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --build --wait
echo "    Backend containers started."

# ── Health poll ───────────────────────────────────────────────────────────────
echo "==> Verifying API health endpoint..."
for i in $(seq 1 10); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "    API healthy (attempt $i)"
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

# ── Success banner ────────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo " CyPerf CVE Tracker -- Running"
echo "================================================"
echo " API:       http://localhost:8000"
echo " API docs:  http://localhost:8000/docs"
echo " Frontend:  http://localhost:5174"
echo ""
echo " Stop: docker compose down"
echo "================================================"
echo ""
