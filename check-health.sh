#!/usr/bin/env bash
# check-health.sh — Validates CyperfBuddy backend health across all layers.
# Usage: ./check-health.sh [host] [backend-port] [agent-port]
# Defaults: localhost 8000 8001

set -euo pipefail

HOST="${1:-localhost}"
PORT="${2:-8000}"
AGENT_PORT="${3:-8001}"
BASE_URL="http://${HOST}:${PORT}"
AGENT_URL="http://${HOST}:${AGENT_PORT}"
PASS="✓"
FAIL="✗"
EXIT_CODE=0

check() {
  local label="$1"
  local url="$2"
  local http_code
  local body

  body=$(curl -sf --max-time 5 -w '\n%{http_code}' "$url" 2>/dev/null) || {
    printf "  %s  %-12s  %s\n" "$FAIL" "$label" "unreachable (connection refused or timeout)"
    EXIT_CODE=1
    return
  }

  http_code=$(echo "$body" | tail -n1)
  body=$(echo "$body" | head -n -1)

  if [[ "$http_code" == "200" ]]; then
    printf "  %s  %-12s  %s\n" "$PASS" "$label" "$body"
  else
    printf "  %s  %-12s  HTTP %s — %s\n" "$FAIL" "$label" "$http_code" "$body"
    EXIT_CODE=1
  fi
}

echo ""
echo "CyperfBuddy Health Check"
echo "──────────────────────────────────────────"
echo "  Backend   ${BASE_URL}"
check "API"       "${BASE_URL}/health/"
check "Database"  "${BASE_URL}/health/db"
check "Redis"     "${BASE_URL}/health/redis"
echo ""
echo "  Agent     ${AGENT_URL}"
check "L47 Agent" "${AGENT_URL}/health"
echo "──────────────────────────────────────────"

if [[ "$EXIT_CODE" -eq 0 ]]; then
  echo "  All systems healthy."
else
  echo "  One or more checks failed."
fi

echo ""
exit "$EXIT_CODE"
