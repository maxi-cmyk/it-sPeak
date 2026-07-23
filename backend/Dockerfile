FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    ITSPEAK_ENVIRONMENT=production \
    ITSPEAK_ARTIFACT_DIR=/data/itspeak-sessions \
    MPLCONFIGDIR=/tmp/itspeak-matplotlib \
    CELERY_WORKER_CONCURRENCY=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .
RUN chmod +x /app/deploy/entrypoint.sh \
    && useradd --create-home --shell /usr/sbin/nologin itspeak \
    && mkdir -p /data/itspeak-sessions /tmp/itspeak-matplotlib \
    && chown -R itspeak:itspeak /app /data/itspeak-sessions /tmp/itspeak-matplotlib

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD ["python", "/app/deploy/healthcheck.py"]

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
