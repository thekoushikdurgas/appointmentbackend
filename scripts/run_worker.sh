#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

celery -A app.tasks.celery_app worker --loglevel=info

