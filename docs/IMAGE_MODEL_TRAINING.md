# Image model training (presentation)

## Which data to use

| Source | Use? |
|--------|------|
| **Google Drive single file** (`1il4Tv4S-...`) | **Yes** — 2.1GB zip with `train/` + `test/` (~14k training images) |
| Google Drive folder (docs/video) | No — guidelines only, not images |
| zbeedatm GitHub mock `dataset.py` | No — synthetic squares, not for demo |

Extract zip to: `dataset_extracted/train/<class>/*.jpg`

## Train (already scripted in repo)

```powershell
cd services\image_analyser_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\python train.py --data-dir ..\..\dataset_extracted --split train --epochs 5 --batch-size 32 --output ./checkpoints/property_room_model.pt
```

## Run with real weights

```powershell
cd <repo root>
$env:MOCK_INFERENCE="false"
docker compose build image_analyser_service
docker compose up -d image_analyser_service
```

Mount checkpoint in compose (see `docker-compose.yml` `image_checkpoints` volume).

## GitHub (you do this)

1. **Do not** commit `property_room_model.pt` (in `.gitignore`).
2. Push code changes: `dataset_utils.py`, `train.py`, `checkpoints/README.md`, this doc.
3. Upload `property_room_model.pt` to a **GitHub Release** on the partner repo.
4. In README / `.env.example`, tell Anood to download the release file into `checkpoints/` and set `MOCK_INFERENCE=false`.
