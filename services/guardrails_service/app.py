"""Guardrails Service - FastAPI."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.fastapi_app import add_standard_middleware
from common.logging_config import configure_logging
from guardrails_engine import GuardrailsEngine

logger = configure_logging("guardrails_service")
engine: GuardrailsEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = GuardrailsEngine()
    yield


app = FastAPI(
    title="Property Guardrails Service",
    description="Input/output safety checks for listing triage",
    version="1.1.0",
    lifespan=lifespan,
)
add_standard_middleware(app)


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)


class CheckResponse(BaseModel):
    pass_: bool = Field(..., serialization_alias="pass")
    reason: str = ""
    safe_text: str = ""

    model_config = {"populate_by_name": True}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "guardrails_service",
        "nemo_enabled": bool(engine and engine._nemo),
        "engine": "rules+ nemo" if engine and engine._nemo else "rules",
    }


@app.post("/check/input", response_model=CheckResponse)
async def check_input(request: CheckRequest) -> dict:
    if not engine:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")
    result = engine.check_input(request.text)
    return {"pass": result["pass"], "reason": result["reason"], "safe_text": result["safe_text"]}


@app.post("/check/output", response_model=CheckResponse)
async def check_output(request: CheckRequest) -> dict:
    if not engine:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")
    result = engine.check_output(request.text)
    return {"pass": result["pass"], "reason": result["reason"], "safe_text": result["safe_text"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
