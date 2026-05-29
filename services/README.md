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

## Layer 4 (models & data)

Intelligence lives **inside** layer 3 services (not a separate app). Weights are **not** in git.

| Component | Technology | Setup |
|-----------|------------|--------|
| **RAG** | ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` | Run `populate_chroma.py` once (see `rag_service/README.md`) |
| **RAG insight** | Optional GGUF in `models/` | See `models/README.md` |
| **Images** | ResNet-50 checkpoint | [Release `image-model-v1`](https://github.com/Anood-Naem/AI_Property_Triage_System/releases/tag/image-model-v1) → `image_analyser_service/checkpoints/property_room_model.pt` |
| **Guardrails** | Rule engine | Default; optional NeMo: `USE_NEMO_GUARDRAILS=true` |
| **Agent** | LangGraph | No local weights; calls RAG + Image over HTTP |
| **WebUI chat** | Ollama (host) | `OLLAMA_BASE_URL` in `.env.example` |
| **n8n LLMs** | OpenAI/Gemini | Keys in n8n UI only |

### One-time before demo

```powershell
copy .env.example .env
# Image weights: download property_room_model.zip from Release image-model-v1, unzip to checkpoints/
docker compose -f docker-compose.backend.yml up -d
docker compose -f docker-compose.backend.yml exec rag_service python populate_chroma.py
```

Copy `.env.example` → `.env`, set `MOCK_INFERENCE=false` after adding the image checkpoint.

Each service folder has a `README.md` with API examples.
