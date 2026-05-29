"""Dataset utilities for property room/condition training."""

import os
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from model import ROOM_CLASSES

ROOM_TO_IDX = {r: i for i, r in enumerate(ROOM_CLASSES)}

# Maps folder names from course Drive dataset (train/<folder>/*.jpg)
DRIVE_CLASS_MAP: dict[str, str | None] = {
    "kitchen_dining": "kitchen",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "living_room": "living_room",
    "bedroom": "bedroom",
    "building_exterior": "exterior",
    "exterior": "exterior",
    "garden": "exterior",
    "balcony": "other",
    "other": "other",
    "not_real_estate": None,  # skip non-listing images
}


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

    def __init__(self, root_dir: str, transform=None, split: str | None = None) -> None:
        self.root = Path(root_dir)
        self.transform = transform or default_transform()
        self.samples: list[tuple[str, int, int]] = []

        if self._load_drive_split_layout(split):
            pass
        elif self._load_nested_condition_layout():
            pass
        else:
            self._load_flat_class_layout()

    def _image_extensions(self) -> set[str]:
        return {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    def _is_image(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in self._image_extensions()

    def _parse_condition_from_name(self, stem: str) -> int:
        """Return condition class index 0-4 (scores 1-5). Default: average (3)."""
        lower = stem.lower()
        if "_cond" in lower:
            try:
                score = int(lower.split("_cond")[-1][:1])
                if 1 <= score <= 5:
                    return score - 1
            except ValueError:
                pass
        for name, val in self.CONDITION_MAP.items():
            if name in lower:
                return val - 1
        return self.CONDITION_MAP["average"] - 1

    def _load_drive_split_layout(self, split: str | None) -> bool:
        """data_root/train/kitchen_dining/*.jpg (course Google Drive zip)."""
        split_name = split or "train"
        split_dir = self.root / split_name
        if not split_dir.is_dir():
            return False
        found = False
        for class_dir in sorted(split_dir.iterdir()):
            if not class_dir.is_dir():
                continue
            mapped = DRIVE_CLASS_MAP.get(class_dir.name, class_dir.name)
            if mapped is None or mapped not in ROOM_TO_IDX:
                continue
            room_idx = ROOM_TO_IDX[mapped]
            for img_path in class_dir.iterdir():
                if self._is_image(img_path):
                    cond_idx = self._parse_condition_from_name(img_path.stem)
                    self.samples.append((str(img_path), room_idx, cond_idx))
                    found = True
        return found

    def _load_nested_condition_layout(self) -> bool:
        """data_root/kitchen/good/*.jpg"""
        loaded = False
        for room in ROOM_CLASSES:
            room_path = self.root / room
            if not room_path.exists():
                continue
            for cond_name, cond_val in self.CONDITION_MAP.items():
                cond_path = room_path / cond_name
                if not cond_path.exists():
                    continue
                for img_path in cond_path.iterdir():
                    if self._is_image(img_path):
                        self.samples.append(
                            (str(img_path), ROOM_TO_IDX[room], cond_val - 1)
                        )
                        loaded = True
        return loaded

    def _load_flat_class_layout(self) -> None:
        """data_root/kitchen/*.jpg (no condition subfolders)."""
        for class_dir in sorted(self.root.iterdir()):
            if not class_dir.is_dir():
                continue
            mapped = DRIVE_CLASS_MAP.get(class_dir.name, class_dir.name)
            if mapped is None or mapped not in ROOM_TO_IDX:
                continue
            room_idx = ROOM_TO_IDX[mapped]
            for img_path in class_dir.iterdir():
                if self._is_image(img_path):
                    cond_idx = self._parse_condition_from_name(img_path.stem)
                    self.samples.append((str(img_path), room_idx, cond_idx))

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
