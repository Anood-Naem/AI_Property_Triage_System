"""Train multi-task property room/condition model."""

import argparse
import logging
import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset_utils import PropertyImageDataset, create_synthetic_batch
from model import PropertyRoomModel, ROOM_CLASSES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_epoch(model, loader, optimizer, criterion, device) -> float:
    model.train()
    total_loss = 0.0
    for images, room_labels, cond_labels in loader:
        images = images.to(device)
        room_labels = room_labels.to(device)
        cond_labels = cond_labels.to(device)
        optimizer.zero_grad()
        room_logits, cond_logits = model(images)
        loss = criterion(room_logits, room_labels) + criterion(cond_logits, cond_labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / max(len(loader), 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="./data", help="Training image root")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--output", default="./checkpoints/property_room_model.pt")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PropertyRoomModel(pretrained=True).to(device)
    optimizer = torch.optim.Adam(
        list(model.room_head.parameters()) + list(model.condition_head.parameters()),
        lr=1e-4,
    )
    criterion = nn.CrossEntropyLoss()

    dataset = PropertyImageDataset(args.data_dir)
    if len(dataset) == 0:
        logger.warning("No images in %s — running synthetic demo training", args.data_dir)

        class SyntheticLoader:
            def __init__(self, batch_size, steps=10):
                self.batch_size = batch_size
                self.steps = steps

            def __len__(self):
                return self.steps

            def __iter__(self):
                for _ in range(self.steps):
                    yield create_synthetic_batch(self.batch_size)

        loader = SyntheticLoader(args.batch_size)
    else:
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    for epoch in range(args.epochs):
        loss = train_epoch(model, loader, optimizer, criterion, device)
        logger.info("Epoch %d/%d — loss: %.4f", epoch + 1, args.epochs, loss)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    torch.save(model.state_dict(), args.output)
    logger.info("Saved checkpoint to %s", args.output)


if __name__ == "__main__":
    main()
