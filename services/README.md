# Backend Services (Layer 3 & 4)

Microservices for the AI Property Triage System. Consumed by **n8n** (layer 2) and optionally the **WebUI** (layer 1) in direct mode.

## Services

| Folder | Port | Health | Primary API |
|--------|------|--------|-------------|
| `rag_service/` | 8001 | `GET /health` | `POST /query` |
| `image_analyser_service/` | 8002 | `GET /health` | `POST /analyse`, `POST /analyse/batch` |
| `guardrails_service/` | 8003 | `GET /health` | `POST /check/input`, `POST /check/output` |
| `langgraph_agent_service/` | 8004 | `GET /health` | `POST /agent/run` |
| `common/` | — | shared utils | logging, HTTP retry, CORS |

## Docker (from repo root)

```bash
docker compose build rag_service
docker compose up -d rag_service
curl http://localhost:8001/health
```

## n8n integration (Docker network hostnames)

| Call | URL |
|------|-----|
| RAG | `http://rag_service:8001/query` |
| Images | `http://image_analyser_service:8002/analyse/batch` |
| Guardrails in | `http://guardrails_service:8003/check/input` |
| Guardrails out | `http://guardrails_service:8003/check/output` |
| Agent | `http://langgraph_agent_service:8004/agent/run` |

## n8n on host (Windows/Mac)

Replace hostnames with `http://localhost:8001` etc.

## Environment

See root `.env.example`. Never commit `.env` or model weights.

## Layer 4 (models)

- **RAG:** ChromaDB + `sentence-transformers/all-MiniLM-L6-v2`; optional GGUF via `GGUF_MODEL_PATH`
- **Images:** PyTorch ResNet-50; `MOCK_INFERENCE=true` for demo without checkpoint
- **Guardrails:** Rule engine; optional NeMo via `USE_NEMO_GUARDRAILS=true`
- **Agent:** LangGraph; calls RAG + Image over HTTP

Each subfolder has its own `README.md` with curl examples.
