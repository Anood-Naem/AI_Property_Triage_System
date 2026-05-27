"""Inference engine with checkpoint loading and mock fallback."""

import logging
import os
from typing import Any
from urllib.parse import urlparse

import torch
from PIL import Image

from model import ROOM_CLASSES, PropertyRoomModel

logger = logging.getLogger(__name__)

CHECKPOINT_PATH = os.getenv("MODEL_CHECKPOINT_PATH", "./checkpoints/property_room_model.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
MOCK_INFERENCE = os.getenv("MOCK_INFERENCE", "true").lower() in ("1", "true", "yes")


class ImageInferenceEngine:
    """Property room/condition inference with graceful mock fallback."""

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model: PropertyRoomModel | None = None
        self.transform = None
        self._load_model()

    def _load_model(self) -> None:
        if MOCK_INFERENCE or not os.path.isfile(CHECKPOINT_PATH):
            logger.info("Mock inference enabled (checkpoint missing or MOCK_INFERENCE=true)")
            return
        try:
            from torchvision import transforms

            self.transform = transforms.Compose(
                [
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )
            self.model = PropertyRoomModel(pretrained=False)
            state = torch.load(CHECKPOINT_PATH, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Loaded checkpoint from %s", CHECKPOINT_PATH)
        except TypeError:
            state = torch.load(CHECKPOINT_PATH, map_location=self.device)
            self.model.load_state_dict(state)
            self.model.to(self.device)
            self.model.eval()
        except Exception as exc:
            logger.warning("Model load failed: %s — using mock", exc)
            self.model = None

    def _mock_from_url(self, image_url: str) -> dict[str, Any]:
        path = urlparse(image_url).path.lower()
        name = os.path.basename(path)
        full = image_url.lower()

        room = "other"
        if "kitchen" in name or "kitchen" in full:
            room = "kitchen"
        elif "bath" in name or "bathroom" in full:
            room = "bathroom"
        elif "bedroom" in name or "bed" in name:
            room = "bedroom"
        elif "living" in name:
            room = "living_room"
        elif "exterior" in name or "outside" in full:
            room = "exterior"

        condition = 3
        if "excellent" in name:
            condition = 5
        elif "good" in name:
            condition = 4
        elif "average" in name:
            condition = 3
        elif any(k in name for k in ("poor", "renovation", "needs")):
            condition = 2

        confidence = 0.88 if room != "other" else 0.62
        return self._format_result(room, condition, confidence)

    def _format_result(
        self, room_type: str, condition_score: int | None, confidence: float
    ) -> dict[str, Any]:
        if confidence < CONFIDENCE_THRESHOLD:
            return {
                "room_type": "uncertain",
                "condition_score": None,
                "confidence": round(confidence, 2),
                "status": "low_confidence",
            }
        return {
            "room_type": room_type,
            "condition_score": condition_score,
            "confidence": round(confidence, 2),
            "status": "ok",
        }

    def _load_image_from_url(self, image_url: str) -> Image.Image | None:
        try:
            import httpx

            resp = httpx.get(image_url, timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            from io import BytesIO

            content_type = resp.headers.get("content-type", "")
            if content_type and not content_type.startswith("image/"):
                logger.warning("Non-image content-type for %s: %s", image_url, content_type)
            return Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception as exc:
            logger.warning("Could not download image %s: %s", image_url, exc)
            return None

    @torch.inference_mode()
    def analyse(self, image_url: str) -> dict[str, Any]:
        if not self.model:
            return self._mock_from_url(image_url)

        image = self._load_image_from_url(image_url)
        if image is None:
            return self._mock_from_url(image_url)

        assert self.transform is not None
        tensor = self.transform(image).unsqueeze(0).to(self.device)
        room_logits, cond_logits = self.model(tensor)
        room_probs = torch.softmax(room_logits, dim=1)[0]
        cond_probs = torch.softmax(cond_logits, dim=1)[0]
        room_conf, room_idx = torch.max(room_probs, dim=0)
        cond_conf, cond_idx = torch.max(cond_probs, dim=0)
        confidence = float((room_conf + cond_conf) / 2)
        room_type = ROOM_CLASSES[int(room_idx)]
        condition_score = int(cond_idx) + 1
        return self._format_result(room_type, condition_score, confidence)
