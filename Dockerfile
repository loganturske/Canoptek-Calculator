FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/data/canoptek.sqlite3 \
    FIXTURES_DIR=/app/fixtures/wahapedia/wh40k10ed

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY fixtures ./fixtures
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN pip install --upgrade pip && \
    pip install .

RUN chmod +x /app/docker/entrypoint.sh && \
    mkdir -p /app/data

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "canoptek_calculator.main:app", "--host", "0.0.0.0", "--port", "8000"]
