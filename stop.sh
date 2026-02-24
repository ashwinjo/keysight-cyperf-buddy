#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# ── Stop frontend dev server ───────────────────────────────────────────────────
if [[ -f "$SCRIPT_DIR/.frontend.pid" ]]; then
  FRONTEND_PID=$(cat "$SCRIPT_DIR/.frontend.pid")
  if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "==> Stopping frontend dev server (PID $FRONTEND_PID)..."
    kill "$FRONTEND_PID" 2>/dev/null || true
  else
    echo "    Frontend process $FRONTEND_PID not found (already stopped)."
  fi
  rm "$SCRIPT_DIR/.frontend.pid"
else
  echo "    No .frontend.pid found; frontend may not be running."
fi

# ── Stop backend containers ────────────────────────────────────────────────────
echo "==> Stopping backend containers..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" down

echo "All services stopped."
