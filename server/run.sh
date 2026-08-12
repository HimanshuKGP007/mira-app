#!/usr/bin/env bash
# Mira scorer — bootstrap and serve.
#   ./run.sh            start on http://localhost:8000
#   PORT=9000 ./run.sh  start elsewhere
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
VENV=".venv"
REQ_HASH_FILE="$VENV/.requirements.sha256"

if [ ! -d "$VENV" ]; then
  echo "[mira] creating virtualenv (this pulls ~2 GB of wheels, once)"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
fi

# Reinstall dependencies only when requirements.txt has actually changed,
# so a normal launch after `git pull` stays fast unless deps moved.
NEW_HASH="$(shasum -a 256 requirements.txt | awk '{print $1}')"
OLD_HASH="$(cat "$REQ_HASH_FILE" 2>/dev/null || true)"
if [ "$NEW_HASH" != "$OLD_HASH" ]; then
  echo "[mira] requirements.txt changed, installing..."
  "$VENV/bin/pip" install -r requirements.txt
  echo "$NEW_HASH" > "$REQ_HASH_FILE"
fi

# If the acoustic model is already in the local HF cache, force fully
# offline loading — no "check for updates" call to the Hub, so a demo never
# depends on the network being up. Only skipped on a genuinely first run,
# when the initial download still needs to happen.
MODEL_ID="${MIRA_MODEL_ID:-facebook/wav2vec2-lv-60-espeak-cv-ft}"
CACHE_NAME="models--${MODEL_ID//\//--}"
if [ -d "$HOME/.cache/huggingface/hub/$CACHE_NAME" ]; then
  export HF_HUB_OFFLINE=1
  echo "[mira] acoustic model already cached — running fully offline, no network needed"
else
  echo "[mira] first run downloads the acoustic model (~1.26 GB) to ~/.cache/huggingface"
fi

echo "[mira] starting on http://localhost:${PORT}"
exec "$VENV/bin/uvicorn" app:app --host 127.0.0.1 --port "$PORT"
