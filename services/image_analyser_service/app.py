"""Image Analyser Service - FastAPI."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from common.fastapi_app import add_standard_middleware
from common.logging_config import configure_logging
from image_sources import ImageSource
from inference import ImageInferenceEngine

logger = configure_logging("image_analyser_service")
engine: ImageInferenceEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = ImageInferenceEngine()
    yield


app = FastAPI(
    title="Property Image Analyser",
    description="Room type and condition scoring from property images (URL or base64 upload)",
    version="1.2.0",
    lifespan=lifespan,
)
add_standard_middleware(app)


class AnalyseRequest(ImageSource):
    """Single image: provide image_url OR image_base64 (+ mime_type, optional filename)."""


class BatchAnalyseRequest(BaseModel):
    """Batch analysis. Use `images` for mixed URL/base64, or legacy `image_urls`."""

    image_urls: list[str] | None = Field(default=None, max_length=20)
    images: list[ImageSource] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_batch(self) -> "BatchAnalyseRequest" :
        urls = [u.strip() for u in (self.image_urls or []) if u and u.strip()]
        items = list(self.images or [])
        total = len(urls) + len(items)
        if total == 0:
            raise ValueError("Provide image_urls and/or images")
        if total > 20:
            raise ValueError("Maximum 20 images per batch")
        self.image_urls = urls or None
        self.images = items or None
        return self

    def iter_sources(self) -> list[ImageSource]:
        out: list[ImageSource] = []
        for url in self.image_urls or []:
            out.append(ImageSource(image_url=url))
        out.extend(self.images or [])
        return out


class AnalyseResponse(BaseModel):
    room_type: str
    condition_score: int | None = None
    confidence: float
    status: str
    image_url: str | None = None
    filename: str | None = None
    source: str | None = None


def _error_row(source: ImageSource, status: str, detail: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {
        "room_type": "uncertain",
        "condition_score": None,
        "confidence": 0.0,
        "status": status,
        **source.to_result_meta(),
    }
    if detail:
        row["detail"] = detail
    return row


def _run_analyse(source: ImageSource) -> dict[str, Any]:
    if not engine:
        raise HTTPException(status_code=503, detail="Inference engine not ready")
    try:
        result = engine.analyse(source)
        result.update(source.to_result_meta())
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analysis failed for %s", source.display_label())
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "image_analyser_service",
        "model_loaded": bool(engine and engine.model is not None),
        "mock_mode": bool(engine and engine.model is None),
        "input_modes": ["image_url", "image_base64"],
    }


@app.post("/analyse", response_model=AnalyseResponse)
async def analyse_image(request: AnalyseRequest) -> AnalyseResponse:
    result = _run_analyse(request)
    return AnalyseResponse(**result)


@app.post("/analyse/batch")
async def analyse_batch(request: BatchAnalyseRequest) -> dict[str, Any]:
    if not engine:
        raise HTTPException(status_code=503, detail="Inference engine not ready")

    results: list[dict[str, Any]] = []
    for source in request.iter_sources():
        try:
            if source.image_url and not source.image_url.startswith(("http://", "https://")):
                results.append(_error_row(source, "invalid_url"))
                continue
            row = engine.analyse(source)
            row.update(source.to_result_meta())
            results.append(row)
        except ValueError as exc:
            logger.warning("Batch item invalid %s: %s", source.display_label(), exc)
            results.append(_error_row(source, "invalid_input", str(exc)))
        except Exception as exc:
            logger.warning("Batch item failed %s: %s", source.display_label(), exc)
            results.append(_error_row(source, "error", str(exc)))

    return {"image_results": results, "count": len(results)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
