# Belle — AI-ассистент на фреймворке mia.
# Все зависимости (mia, модули db/auth) клонируются с GitHub при КАЖДОЙ сборке —
# обновил код в репозитории, пересобрал образ, получил свежее.

FROM python:3.10-slim

# Инструменты: git (клон репозиториев при сборке), curl (healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Ядро mia ────────────────────────────────────────────────
RUN git clone --depth 1 https://github.com/Dek1m/mia.git /app/mia

# ── Модули: db и auth ───────────────────────────────────────
RUN mkdir -p /app/modules \
    && git clone --depth 1 https://github.com/Dek1m/mia-db.git /app/modules/db \
    && git clone --depth 1 https://github.com/Dek1m/mia-auth.git /app/modules/auth

# ── Код belle (из build context) ─────────────────────────────
COPY . /app

# ── Зависимости Python ──────────────────────────────────────
# argenta-logging — внутренний пакет Argenta Team, ставится с GitHub
RUN pip install --no-cache-dir \
    git+https://github.com/Dek1m/argenta-logging.git \
    asyncpg \
    pydantic

ENV PYTHONPATH=/app/mia:/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]