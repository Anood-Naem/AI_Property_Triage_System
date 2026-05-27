"""Multi-task ResNet-50: room type + condition score classification."""

import torch
import torch.nn as nn
from torchvision import models

ROOM_CLASSES = ["kitchen", "bathroom", "living_room", "bedroom", "exterior", "other"]
NUM_ROOMS = len(ROOM_CLASSES)
NUM_CONDITIONS = 5  # scores 1-5


class PropertyRoomModel(nn.Module):
    """ResNet-50 backbone with frozen features and dual classification heads."""

    def __init__(self, pretrained: bool = True) -> None:
        super().__init__()
        weights = models.ResNet50_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = models.resnet50(weights=weights)
        self.features = nn.Sequential(*list(backbone.children())[:-1])
        feature_dim = 2048

        for param in self.features.parameters():
            param.requires_grad = False

        self.room_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, NUM_ROOMS),
        )
        self.condition_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(feature_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, NUM_CONDITIONS),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        feat = self.features(x)
        return self.room_head(feat), self.condition_head(feat)
