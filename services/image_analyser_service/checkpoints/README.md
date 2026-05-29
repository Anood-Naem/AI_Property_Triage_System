# Model checkpoint (not in git)

Download **property_room_model.zip** from GitHub Release **image-model-v1**, unzip here as `property_room_model.pt`.

Then:

```powershell
docker compose -f docker-compose.backend.yml up --build -d image_analyser_service
```

Set `MOCK_INFERENCE=false` in `.env` (see `.env.example`).

## Train your own

```powershell
cd services/image_analyser_service
python train.py --data-dir ../../dataset_extracted --split train --epochs 5 --output ./checkpoints/property_room_model.pt
```

See [docs/IMAGE_MODEL_TRAINING.md](../../../docs/IMAGE_MODEL_TRAINING.md).
