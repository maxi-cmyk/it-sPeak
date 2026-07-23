#!/usr/bin/env bash
# Starts Redis (Docker), the backend (API + Celery worker + beat), and the frontend dev server.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
mkdir -p "$RUN_DIR"

echo "Starting Redis..."
if command -v docker >/dev/null 2>&1; then
  if docker ps -a --format '{{.Names}}' | grep -qx "itspeak-redis"; then
    docker start itspeak-redis >/dev/null
  else
    docker run -d --name itspeak-redis -p 6379:6379 redis:7 >/dev/null
  fi
else
  echo "Warning: docker not found on PATH; make sure Redis is reachable at localhost:6379." >&2
fi

echo "Starting backend (API, worker, beat)..."
: > "$RUN_DIR/backend.log"
node "$ROOT_DIR/scripts/launch.mjs" "$RUN_DIR/backend.pid" "$RUN_DIR/backend.log" "$ROOT_DIR/backend" \
  node "$ROOT_DIR/scripts/run-backend.mjs"

echo "Starting frontend..."
: > "$RUN_DIR/frontend.log"
node "$ROOT_DIR/scripts/launch.mjs" "$RUN_DIR/frontend.pid" "$RUN_DIR/frontend.log" "$ROOT_DIR/frontend" \
  node "$ROOT_DIR/frontend/node_modules/next/dist/bin/next" dev

sleep 2
echo
echo "Backend  PID $(cat "$RUN_DIR/backend.pid")  -> log: $RUN_DIR/backend.log   (API: http://127.0.0.1:8000)"
echo "Frontend PID $(cat "$RUN_DIR/frontend.pid") -> log: $RUN_DIR/frontend.log  (http://localhost:3000)"
echo
echo "Run scripts/stop.sh to stop everything."
