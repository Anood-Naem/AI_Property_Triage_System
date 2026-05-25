FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY rag_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY rag_service /app

ENV CHROMA_DIR=/data/chroma
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Populate at build time (runtime also auto-populates if empty via app lifespan)
RUN python populate_chroma.py || true

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
