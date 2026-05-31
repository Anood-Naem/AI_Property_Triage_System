"""LangGraph Agent Service - FastAPI."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from common.fastapi_app import add_standard_middleware
from common.image_sources import ImageSource
from common.logging_config import configure_logging
from graph import run_agent

logger = configure_logging("langgraph_agent_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LangGraph agent service ready")
    yield


app = FastAPI(
    title="LangGraph Property Agent",
    description="Multi-step property analysis agent",
    version="1.2.0",
    lifespan=lifespan,
)
add_standard_middleware(app)


class AgentRunRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=5000)
    description: str = Field(default="", max_length=10000)
    image_urls: list[str] = Field(default_factory=list, max_length=20)
    images: list[ImageSource] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_image_count(self) -> AgentRunRequest:
        if len(self.image_urls) + len(self.images) > 20:
            raise ValueError("Maximum 20 images total (image_urls + images)")
        return self


class AgentRunResponse(BaseModel):
    answer: str
    tools_used: list[str]
    reasoning_steps: list[str]
    rag_result: dict[str, Any] = Field(default_factory=dict)
    image_results: list[dict[str, Any]] = Field(default_factory=list)
    recommended_team: str = "manual_review"


@app.get("/health")
async def health() -> dict:
    import os

    return {
        "status": "ok",
        "service": "langgraph_agent_service",
        "rag_url": os.getenv("RAG_SERVICE_URL", "http://localhost:8001"),
        "image_url": os.getenv("IMAGE_ANALYSER_URL", "http://localhost:8002"),
        "image_input_modes": ["image_urls", "images (base64 + mime_type)"],
    }


@app.post("/agent/run", response_model=AgentRunResponse)
async def agent_run(request: AgentRunRequest) -> AgentRunResponse:
    try:
        result = run_agent(
            query=request.query.strip(),
            description=request.description.strip(),
            image_urls=[u.strip() for u in request.image_urls if u.strip()],
            images=list(request.images),
        )
        return AgentRunResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
