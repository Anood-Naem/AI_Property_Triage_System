"""Dataset utilities for property room/condition training."""

import os
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from model import ROOM_CLASSES

ROOM_TO_IDX = {r: i for i, r in enumerate(ROOM_CLASSES)}


def default_transform(image_size: int = 224) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


class PropertyImageDataset(Dataset):
    """
    Expects directory structure:
    data/
      kitchen/
        good/img1.jpg
        poor/img2.jpg
      bathroom/
        ...
    Condition inferred from subfolder: poor=1, below_average=2, average=3, good=4, excellent=5
    """

    CONDITION_MAP = {
        "poor": 1,
        "below_average": 2,
        "average": 3,
        "good": 4,
        "excellent": 5,
    }

    def __init__(self, root_dir: str, transform=None) -> None:
        self.root = Path(root_dir)
        self.transform = transform or default_transform()
        self.samples: list[tuple[str, int, int]] = []

        for room in ROOM_CLASSES:
            room_path = self.root / room
            if not room_path.exists():
                continue
            for cond_name, cond_val in self.CONDITION_MAP.items():
                cond_path = room_path / cond_name
                if not cond_path.exists():
                    continue
                for img_path in cond_path.glob("*"):
                    if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                        self.samples.append(
                            (str(img_path), ROOM_TO_IDX[room], cond_val - 1)
                        )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        path, room_idx, cond_idx = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, room_idx, cond_idx


def create_synthetic_batch(batch_size: int = 4) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Synthetic batch for demo training when no dataset exists."""
    images = torch.randn(batch_size, 3, 224, 224)
    rooms = torch.randint(0, len(ROOM_CLASSES), (batch_size,))
    conditions = torch.randint(0, 5, (batch_size,))
    return images, rooms, conditions
