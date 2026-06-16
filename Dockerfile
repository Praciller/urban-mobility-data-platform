FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    DUCKDB_PATH=/data/processed/urban_mobility.duckdb \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps

RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

USER appuser
VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
