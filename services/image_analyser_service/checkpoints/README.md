# Model checkpoint (not in git)

Train locally:

```powershell
cd services/image_analyser_service
.\.venv\Scripts\python train.py --data-dir ..\..\dataset_extracted --split train --epochs 5 --output ./checkpoints/property_room_model.pt
```

Dataset: extract `dataset.zip` from Google Drive (course file) to `dataset_extracted/train/`.

Publish weights via **GitHub Release** — do not commit `*.pt` to the repo.
