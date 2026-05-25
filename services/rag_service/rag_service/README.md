# RAG Service

FastAPI service for similar listing retrieval using ChromaDB and HuggingFace sentence-transformers.

## Endpoints

- `GET /health` — Service health and document count
- `POST /query` — Retrieve similar listings and generate insight

## Environment

| Variable | Default |
|----------|---------|
| `CHROMA_DIR` | `./chroma_data` |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` |
| `GGUF_MODEL_PATH` | (empty = mock insight) |
| `TOP_K` | `3` |

## Populate ChromaDB

```bash
cd services/rag_service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python populate_chroma.py
```

## Run locally

```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

## Test

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"description": "Beautiful 3-room apartment in Haifa with renovated kitchen, balcony, parking, and sea view. Asking price 1,850,000 ILS."}'
```

```bash
curl http://localhost:8001/health
```
