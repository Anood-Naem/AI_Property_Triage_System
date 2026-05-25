"""RAG Service - FastAPI application."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.fastapi_app import add_standard_middleware
from common.logging_config import configure_logging
from rag_pipeline import RAGPipeline

logger = configure_logging("rag_service")
pipeline: RAGPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    pipeline = RAGPipeline()
    if pipeline._collection is not None:
        try:
            if pipeline._collection.count() == 0:
                logger.warning("Chroma empty — running populate_chroma")
                import subprocess
                import sys

                subprocess.run([sys.executable, "populate_chroma.py"], check=False)
                pipeline = RAGPipeline()
        except Exception as exc:
            logger.warning("Startup chroma check failed: %s", exc)
    yield


app = FastAPI(
    title="Property RAG Service",
    description="Similar listing retrieval and market insights",
    version="1.1.0",
    lifespan=lifespan,
)
add_standard_middleware(app)


class QueryRequest(BaseModel):
    description: str = Field(..., min_length=10, max_length=10000)


class SimilarListing(BaseModel):
    id: str
    title: str
    property_type: str
    location: str
    price: str
    features: list[str]
    similarity_score: float


class QueryResponse(BaseModel):
    similar_listings: list[SimilarListing]
    insight: str


@app.get("/health")
async def health() -> dict:
    count = 0
    ready = pipeline is not None
    if pipeline and pipeline._collection:
        try:
            count = pipeline._collection.count()
        except Exception:
            pass
    return {
        "status": "ok" if ready else "degraded",
        "service": "rag_service",
        "chroma_documents": count,
        "llm_loaded": bool(pipeline and pipeline._llm),
    }


@app.post("/query", response_model=QueryResponse)
async def query_listings(request: QueryRequest) -> QueryResponse:
    if not pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    try:
        result = pipeline.query(request.description.strip())
        return QueryResponse(**result)
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
