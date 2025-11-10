#!/usr/bin/env bash
set -euo pipefail

# Ensure we execute from the repository root so relative paths resolve.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

export PYTHONUNBUFFERED=1

APP_MODULE="${APP_MODULE:-app.main:app}"
GUNICORN_CONF="${GUNICORN_CONF:-${PROJECT_ROOT}/gunicorn_conf.py}"

exec gunicorn --config "${GUNICORN_CONF}" "${APP_MODULE}"

