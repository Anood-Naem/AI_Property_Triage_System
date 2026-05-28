"""LangGraph tools: RAG and Image Analyser HTTP clients with retries."""

import logging
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.http_utils import post_json_with_retry

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


def call_image_analyser(image_url: str) -> dict[str, Any]:
    """Analyse a single property image."""
    try:
        return post_json_with_retry(
            f"{IMAGE_ANALYSER_URL.rstrip('/')}/analyse",
            {"image_url": image_url},
            timeout=HTTP_TIMEOUT,
            retries=HTTP_RETRIES,
        )
    except Exception as exc:
        logger.warning("Image analyser unavailable for %s: %s", image_url, exc)
        return _keyword_fallback(image_url)


def call_image_batch(image_urls: list[str]) -> list[dict[str, Any]]:
    """Batch image analysis when service supports /analyse/batch."""
    clean = [u.strip() for u in image_urls if u.strip()]
    if not clean:
        return []
    try:
        data = post_json_with_retry(
            f"{IMAGE_ANALYSER_URL.rstrip('/')}/analyse/batch",
            {"image_urls": clean},
            timeout=HTTP_TIMEOUT,
            retries=HTTP_RETRIES,
        )
        return data.get("image_results", [])
    except Exception as exc:
        logger.warning("Batch image API unavailable, falling back per-URL: %s", exc)
        return analyse_all_images(clean)


def _keyword_fallback(image_url: str) -> dict[str, Any]:
    url_lower = image_url.lower()
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
        "image_url": image_url,
    }


def analyse_all_images(image_urls: list[str]) -> list[dict[str, Any]]:
    if len(image_urls) > 1:
        batch = call_image_batch(image_urls)
        if batch:
            return batch
    results = []
    for url in image_urls:
        row = call_image_analyser(url.strip())
        row.setdefault("image_url", url.strip())
        results.append(row)
    return results
