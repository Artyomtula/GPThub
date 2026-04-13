#!/usr/bin/env sh

# Load repo-level .env for local development runs.
# This keeps backend/dev.sh behavior aligned with docker-compose env usage.
if [ -f "../.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "../.env"
  set +a
fi

export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:8080"
PORT="${PORT:-8080}"
uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" --reload
