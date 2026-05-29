# Image model — trained weights

## Quick start (presentation)

1. **Download** release [image-model-v1](https://github.com/Anood-Naem/AI_Property_Triage_System/releases/tag/image-model-v1) → `property_room_model.zip`
2. **Unzip** to `services/image_analyser_service/checkpoints/property_room_model.pt`
3. **Run:**

```powershell
cp .env.example .env
docker compose -f docker-compose.backend.yml up --build -d
curl.exe http://localhost:8002/health
```

Expect `"mock_mode": false` when the checkpoint is loaded.

## Dataset (course Google Drive)

Use the **2.1GB zip** (single file), not the docs-only folder. Extract to `dataset_extracted/train/<class>/`.

## Train locally

```powershell
cd services/image_analyser_service
pip install -r requirements.txt
python train.py --data-dir ../../dataset_extracted --split train --epochs 5 --batch-size 32 --max-samples 4000 --output ./checkpoints/property_room_model.pt
```

Weights are published as **ZIP on GitHub Releases** (`.pt` files are too large for git). Layer 4 overview: `services/README.md`.
