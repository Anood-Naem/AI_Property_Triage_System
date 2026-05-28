FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY langgraph_agent_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY langgraph_agent_service /app

ENV RAG_SERVICE_URL=http://rag_service:8001
ENV IMAGE_ANALYSER_URL=http://image_analyser_service:8002
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8004
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"]
