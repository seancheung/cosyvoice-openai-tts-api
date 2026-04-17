#!/usr/bin/env bash
set -euo pipefail

: "${COSYVOICE_VERSION:=3}"
: "${COSYVOICE_MODEL_DIR:=/models}"
: "${COSYVOICE_VOICES_DIR:=/voices}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${LOG_LEVEL:=info}"

export COSYVOICE_VERSION COSYVOICE_MODEL_DIR COSYVOICE_VOICES_DIR HOST PORT LOG_LEVEL

if [ "$#" -eq 0 ]; then
  exec uvicorn app.server:app --host "$HOST" --port "$PORT" --log-level "$LOG_LEVEL"
fi
exec "$@"
