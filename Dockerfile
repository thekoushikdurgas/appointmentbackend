FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY gunicorn_conf.py ./gunicorn_conf.py
COPY scripts ./scripts

RUN chmod +x ./scripts/run_gunicorn.sh ./scripts/run_app.sh ./scripts/run_worker.sh

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn_conf.py", "app.main:app"]

