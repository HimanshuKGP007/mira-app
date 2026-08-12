#!/usr/bin/env bash
# Mira — double-click (or run from a terminal) to start the app and open it
# in your browser. First run bootstraps a virtualenv and downloads the
# acoustic model; every run after that is fast. Ctrl+C / close this window
# to stop the server.
set -euo pipefail
cd "$(dirname "$0")/server"

PORT="${PORT:-8000}"
URL="http://localhost:${PORT}"

open_when_ready() {
  for _ in $(seq 1 240); do
    if curl -s -o /dev/null "$URL/health"; then
      open "$URL"
      return
    fi
    sleep 0.5
  done
}

open_when_ready &
exec ./run.sh
