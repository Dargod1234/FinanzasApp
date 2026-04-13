# ── Stage 1: Base ──
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: App ──
FROM base AS app

COPY backend/ .

RUN DJANGO_SECRET_KEY=build-static-key \
    DJANGO_DEBUG=False \
    DATABASE_URL=sqlite:///tmp/build.db \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "finanzas.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
