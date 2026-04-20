FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY pytest.ini .
COPY migrate_util.py .
COPY tests ./tests

RUN mkdir -p /app/uploads

ENTRYPOINT ["/bin/sh", "-c", "set -e; cd /app && alembic upgrade head && exec \"$@\"", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
