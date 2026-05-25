"""HTTP client helpers with retries."""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def post_json_with_retry(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float = 30.0,
    retries: int = 3,
    backoff: float = 0.5,
) -> dict[str, Any]:
    """POST JSON with exponential backoff retries."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            # Do not retry client errors (4xx) — e.g. old image service without /analyse/batch
            if 400 <= exc.response.status_code < 500:
                raise
            logger.warning("HTTP POST %s attempt %d failed: %s", url, attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
        except Exception as exc:
            last_error = exc
            logger.warning("HTTP POST %s attempt %d failed: %s", url, attempt + 1, exc)
            if attempt < retries - 1:
                time.sleep(backoff * (2**attempt))
    raise RuntimeError(f"Request failed after {retries} attempts: {last_error}") from last_error
