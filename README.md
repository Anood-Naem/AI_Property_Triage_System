# AI Property Triage System

AI Property Triage System receives a property listing, validates it, enriches it with RAG + image analysis, and returns a structured report for triage and routing.

## Repository Structure

- `webui/` - Streamlit UI (listing form + assistant)
- `services/` - backend microservices (RAG, image, guardrails, LangGraph)
- `n8n_workflows/` - importable n8n workflow JSON
- `docs/` - model and run documentation
- `models/` - optional local GGUF location (no weights in git)
- `docker-compose.backend.yml` - run all backend services

## Architecture (4 layers)

1. **Layer 1 - WebUI** (`webui/`)
2. **Layer 2 - n8n orchestration** (`n8n_workflows/`)
3. **Layer 3 - FastAPI services** (`services/`)
4. **Layer 4 - models/data** (Chroma embeddings, image checkpoint release, optional GGUF)

## Quick Start (Windows)

### 1) Clone and prepare env

```powershell
cd C:\Users\Musta\AI_Property_Triage_System
copy .env.example .env
```

### 2) Image model checkpoint (required for non-mock image analysis)

- Download release: [image-model-v1](https://github.com/Anood-Naem/AI_Property_Triage_System/releases/tag/image-model-v1)
- Unzip `property_room_model.zip` to:

`services/image_analyser_service/checkpoints/property_room_model.pt`

### 3) Start backend services

```powershell
docker compose -f docker-compose.backend.yml up --build -d
```

Backend health endpoints:

- `http://localhost:8001/health` (RAG)
- `http://localhost:8002/health` (Image)
- `http://localhost:8003/health` (Guardrails)
- `http://localhost:8004/health` (LangGraph)

### 4) Import and activate n8n workflow

- Open n8n UI
- Import `n8n_workflows/ai_property_triage_workflow.json`
- Rebind credentials (Gemini/OpenAI) in your n8n instance
- Activate workflow

### 5) Run WebUI

```powershell
cd webui
copy .env.example .env
pip install -r requirements.txt
streamlit run app.py
```

## Notes

- `.pt`, `.pth`, `.gguf`, dataset archives are intentionally excluded from git.
- n8n workflow includes node IDs/credential references from authoring environment; credentials must be reselected after import.
- For full layer details, see `services/README.md` and `docs/IMAGE_MODEL_TRAINING.md`.

## Run from GitHub (no manual unzip)

```powershell
cd C:\Users\Musta\AI_Property_Triage_System
powershell -ExecutionPolicy Bypass -File .\run_from_github.ps1
```

This script automatically:
- creates `.env` files from examples
- downloads + extracts `image-model-v1` checkpoint
- starts backend services
- populates RAG data
- starts n8n container (if enabled)
- installs WebUI dependencies and starts Streamlit

