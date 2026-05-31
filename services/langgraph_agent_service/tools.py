"""LangGraph tools: RAG and Image Analyser HTTP clients with retries."""

import logging
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.http_utils import post_json_with_retry
from common.image_sources import ImageSource

logger = logging.getLogger(__name__)

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
IMAGE_ANALYSER_URL = os.getenv("IMAGE_ANALYSER_URL", "http://localhost:8002")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))


def call_rag(description: str) -> dict[str, Any]:
    """Query RAG service for similar listings."""
    try:
        return post_json_with_retry(
            f"{RAG_SERVICE_URL.rstrip('/')}/query",
            {"description": description},
            timeout=HTTP_TIMEOUT,
            retries=HTTP_RETRIES,
        )
    except Exception as exc:
        logger.warning("RAG service unavailable: %s", exc)
        return {
            "similar_listings": [],
            "insight": (
                f"RAG service unavailable ({exc}). "
                "Comparison based on submission text only; verify with live market data."
            ),
        }


def call_image_analyser(source: ImageSource) -> dict[str, Any]:
    """Analyse one image (URL or base64 upload)."""
    label = source.display_label()
    try:
        return post_json_with_retry(
            f"{IMAGE_ANALYSER_URL.rstrip('/')}/analyse",
            source.to_analyse_payload(),
            timeout=HTTP_TIMEOUT,
            retries=HTTP_RETRIES,
        )
    except Exception as exc:
        logger.warning("Image analyser unavailable for %s: %s", label, exc)
        return _keyword_fallback(label)


def call_image_batch(
    image_urls: list[str],
    images: list[ImageSource],
) -> list[dict[str, Any]]:
    """Batch image analysis (mixed URLs and uploads)."""
    clean_urls = [u.strip() for u in image_urls if u.strip()]
    if not clean_urls and not images:
        return []
    body: dict[str, Any] = {}
    if clean_urls:
        body["image_urls"] = clean_urls
    if images:
        body["images"] = [img.to_analyse_payload() for img in images]
    try:
        data = post_json_with_retry(
            f"{IMAGE_ANALYSER_URL.rstrip('/')}/analyse/batch",
            body,
            timeout=HTTP_TIMEOUT,
            retries=HTTP_RETRIES,
        )
        return data.get("image_results", [])
    except Exception as exc:
        logger.warning("Batch image API unavailable: %s", exc)
        return []


def _keyword_fallback(label: str) -> dict[str, Any]:
    url_lower = label.lower()
    room, cond = "other", 3
    if "kitchen" in url_lower:
        room, cond = "kitchen", 4
    elif "bath" in url_lower:
        room, cond = "bathroom", 2
    elif "bedroom" in url_lower or "bed" in url_lower:
        room, cond = "bedroom", 3
    elif "living" in url_lower:
        room, cond = "living_room", 3
    elif "exterior" in url_lower:
        room, cond = "exterior", 4
    if "renovation" in url_lower or "needs" in url_lower:
        cond = 2
    return {
        "room_type": room,
        "condition_score": cond,
        "confidence": 0.75,
        "status": "fallback",
        "image_url": label if label.startswith("http") else None,
        "filename": None if label.startswith("http") else label,
        "source": "url" if label.startswith("http") else "base64",
    }


def analyse_all_images(
    image_urls: list[str],
    images: list[ImageSource] | None = None,
) -> list[dict[str, Any]]:
    uploads = list(images or [])
    clean_urls = [u.strip() for u in image_urls if u.strip()]
    total = len(clean_urls) + len(uploads)
    if total == 0:
        return []

    if total > 1 or (clean_urls and uploads):
        batch = call_image_batch(clean_urls, uploads)
        if batch:
            return batch

    results: list[dict[str, Any]] = []
    for url in clean_urls:
        src = ImageSource(image_url=url)
        row = call_image_analyser(src)
        row.update(src.to_result_meta())
        results.append(row)
    for src in uploads:
        row = call_image_analyser(src)
        row.update(src.to_result_meta())
        results.append(row)
    return results
