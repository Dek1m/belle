# Belle — AI-ассистент на фреймворке mia.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    git+https://github.com/Dek1m/argenta-logging.git

# Свежие клоны ядра и модулей (CACHEBUST сбрасывает слой)
ARG CACHEBUST=1
RUN echo "$CACHEBUST" \
    && git clone --depth 1 https://github.com/Dek1m/mia.git /app/mia \
    && git clone --depth 1 https://github.com/Dek1m/mia-db.git /app/mia/modules/db \
    && git clone --depth 1 https://github.com/Dek1m/mia-auth.git /app/mia/modules/auth \
    && git clone --depth 1 https://github.com/Dek1m/mia-log.git /app/mia/modules/log \
    && git clone --depth 1 https://github.com/Dek1m/mia-worker.git /app/mia/modules/worker \
    && git clone --depth 1 https://github.com/Dek1m/mia-workspace.git /app/mia/modules/workspace \
    && git clone --depth 1 https://github.com/Dek1m/mia-llm.git /app/mia/modules/llm \
    && git clone --depth 1 https://github.com/Dek1m/mia-apiproxy.git /app/mia/modules/apiproxy \
    && git clone --depth 1 https://github.com/Dek1m/mia-rest.git /app/mia/modules/rest

# Код belle
RUN echo "$CACHEBUST" \
    && git clone --depth 1 https://github.com/Dek1m/belle.git /tmp/belle \
    && cp /tmp/belle/main.py /tmp/belle/app.py /tmp/belle/migrate.py /tmp/belle/pyproject.toml /app/ \
    && cp -a /tmp/belle/config /app/config \
    && mkdir -p /app/certs \
    && cp /tmp/belle/certs/argentaca.crt /app/certs/argentaca.crt \
    && cp /tmp/belle/certs/argentaca.crt /usr/local/share/ca-certificates/argentaca.crt \
    && rm -rf /tmp/belle \
    && update-ca-certificates

RUN pip install --upgrade pip setuptools wheel hatchling \
    && pip install --no-cache-dir \
        "celery[redis]>=5.5,<6" \
        "psycopg[binary,pool]>=3.2" \
        cryptography \
        pydantic prometheus-client argon2-cffi pyjwt httpx \
        "fastapi>=0.115" "uvicorn[standard]>=0.32" \
    && pip install --no-deps --no-cache-dir -e /app/mia

ENV PYTHONPATH=/app/mia:/app
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=belle
ENV BELLE_MODULES_DIR=/app/mia/modules
ENV MIA_REST_BIND=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
