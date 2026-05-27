"""Image Analyser Service - FastAPI."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from common.fastapi_app import add_standard_middleware
from common.logging_config import configure_logging
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
    description="Room type and condition scoring from property images",
    version="1.1.0",
    lifespan=lifespan,
)
add_standard_middleware(app)


class AnalyseRequest(BaseModel):
    image_url: str = Field(..., min_length=5, max_length=2048)

    @field_validator("image_url")
    @classmethod
    def validate_url_scheme(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("image_url must be http or https")
        return value.strip()


class BatchAnalyseRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=20)


class AnalyseResponse(BaseModel):
    room_type: str
    condition_score: int | None = None
    confidence: float
    status: str
    image_url: str | None = None


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "image_analyser_service",
        "model_loaded": bool(engine and engine.model is not None),
        "mock_mode": bool(engine and engine.model is None),
    }


@app.post("/analyse", response_model=AnalyseResponse)
async def analyse_image(request: AnalyseRequest) -> AnalyseResponse:
    if not engine:
        raise HTTPException(status_code=503, detail="Inference engine not ready")
    try:
        result = engine.analyse(request.image_url)
        return AnalyseResponse(**result)
    except Exception as exc:
        logger.exception("Analysis failed for %s", request.image_url)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/analyse/batch")
async def analyse_batch(request: BatchAnalyseRequest) -> dict[str, Any]:
    if not engine:
        raise HTTPException(status_code=503, detail="Inference engine not ready")
    results = []
    for url in request.image_urls:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            results.append(
                {
                    "image_url": url,
                    "room_type": "uncertain",
                    "condition_score": None,
                    "confidence": 0.0,
                    "status": "invalid_url",
                }
            )
            continue
        try:
            row = engine.analyse(url)
            row["image_url"] = url
            results.append(row)
        except Exception as exc:
            logger.warning("Batch item failed %s: %s", url, exc)
            results.append(
                {
                    "image_url": url,
                    "room_type": "uncertain",
                    "condition_score": None,
                    "confidence": 0.0,
                    "status": "error",
                }
            )
    return {"image_results": results, "count": len(results)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
