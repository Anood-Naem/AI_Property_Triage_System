# Image Analyser Service

Multi-task ResNet-50 classifier for room type and condition score (1–5).

## Endpoints

- `GET /health`
- `POST /analyse` — `{"image_url": "https://example.com/kitchen_good.jpg"}`

## Room classes

`kitchen`, `bathroom`, `living_room`, `bedroom`, `exterior`, `other`

## Training

```bash
python train.py --data-dir ./data --epochs 5 --output ./checkpoints/property_room_model.pt
```

Without a dataset, `train.py` runs synthetic demo training.

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8002
```

## Test

```bash
curl -X POST http://localhost:8002/analyse \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/kitchen_good.jpg"}'

curl -X POST http://localhost:8002/analyse \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/bathroom_needs_renovation.jpg"}'
```
