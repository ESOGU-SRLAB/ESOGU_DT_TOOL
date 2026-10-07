FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
RUN mkdir -p /app/data/artifacts /app/data/uploads && \
    useradd --create-home --uid 10001 stlc && \
    chown -R stlc:stlc /app

USER stlc
WORKDIR /app/backend

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('APP_PORT', '8100') + '/health', timeout=2)" || exit 1

# One worker is intentional: background job state is process-local. Scale-out
# requires replacing JobService with shared durable storage/queueing.
CMD ["sh", "-c", "exec uvicorn app:app --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8100} --log-level ${LOG_LEVEL:-info}"]
