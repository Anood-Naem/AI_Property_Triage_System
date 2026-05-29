# Image Analyser Service

Multi-task ResNet-50 classifier for room type and condition score (1–5).

## Endpoints

- `GET /health`
- `POST /analyse` — one image (URL **or** base64 upload)
- `POST /analyse/batch` — multiple images (mixed URL and base64)

## Input modes

### 1) Remote URL (unchanged)

```json
{
  "image_url": "https://example.com/kitchen_good.jpg"
}
```

### 2) Upload from PC (base64)

```json
{
  "image_base64": "<base64 bytes>",
  "mime_type": "image/jpeg",
  "filename": "kitchen.jpg"
}
```

- `mime_type` is **required** for raw base64 (or use a `data:image/jpeg;base64,...` URI).
- `filename` is optional (helps mock mode and logging).
- Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/bmp`, `image/tiff`.
- Max decoded size: **10 MB**.

### Batch (mixed)

```json
{
  "images": [
    { "image_url": "https://example.com/a.jpg" },
    {
      "image_base64": "...",
      "mime_type": "image/png",
      "filename": "bathroom.png"
    }
  ]
}
```

Legacy batch (URLs only) still works:

```json
{ "image_urls": ["https://example.com/a.jpg"] }
```

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

## Test (PowerShell)

URL:

```powershell
$body = '{"image_url": "https://example.com/kitchen_good.jpg"}'
Invoke-RestMethod -Uri http://localhost:8002/analyse -Method POST -ContentType "application/json" -Body $body
```

Base64 (encode a local file):

```powershell
$bytes = [IO.File]::ReadAllBytes("C:\path\to\kitchen.jpg")
$b64 = [Convert]::ToBase64String($bytes)
$payload = @{
  image_base64 = $b64
  mime_type = "image/jpeg"
  filename = "kitchen.jpg"
} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8002/analyse -Method POST -ContentType "application/json" -Body $payload
```
