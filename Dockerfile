# Host-agnostic image: works on Northflank, Oracle Cloud, a home Pi, or any
# Docker host. Set STORAGE_BACKEND=telegram|github|local and the matching env
# vars; no persistent volume is needed for the telegram/github backends.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/app/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system app >/dev/null 2>&1 || true; \
    adduser --system --ingroup app app >/dev/null 2>&1 || true; \
    mkdir -p /app/data/tmp && chown -R app:app /app/data

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000'), timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn bridge:app --host 0.0.0.0 --port ${PORT} --workers 1"]
