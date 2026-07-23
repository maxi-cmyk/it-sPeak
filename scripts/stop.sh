#!/usr/bin/env bash
# Stops the backend, the frontend, and the Redis container started by start.sh.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

kill_pid_tree() {
  local label="$1" pid_file="$2"
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if [ -n "$pid" ]; then
      echo "Stopping $label (PID $pid)..."
      taskkill //F //T //PID "$pid" >/dev/null 2>&1
    fi
    rm -f "$pid_file"
  else
    echo "No PID file for $label, skipping."
  fi
}

kill_pid_tree "backend" "$RUN_DIR/backend.pid"
kill_pid_tree "frontend" "$RUN_DIR/frontend.pid"

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -qx "itspeak-redis"; then
  echo "Stopping Redis container..."
  docker stop itspeak-redis >/dev/null
fi

echo "Done."
