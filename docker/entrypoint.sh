#!/usr/bin/env bash
set -euo pipefail

: "${COSYVOICE_VERSION:=3}"
: "${COSYVOICE_VOICES_DIR:=/voices}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${LOG_LEVEL:=info}"

# Redirect model caches under the single /root/.cache mount so first-run
# downloads (modelscope main model + whisper + huggingface tokenizers) all
# land in a persistent volume.
: "${MODELSCOPE_CACHE:=/root/.cache/modelscope}"
: "${HF_HOME:=/root/.cache/huggingface}"
: "${XDG_CACHE_HOME:=/root/.cache}"

export COSYVOICE_VERSION COSYVOICE_VOICES_DIR HOST PORT LOG_LEVEL
export MODELSCOPE_CACHE HF_HOME XDG_CACHE_HOME
if [ -n "${COSYVOICE_MODEL:-}" ]; then
  export COSYVOICE_MODEL
fi

if [ "$#" -eq 0 ]; then
  exec uvicorn app.server:app --host "$HOST" --port "$PORT" --log-level "$LOG_LEVEL"
fi
exec "$@"
