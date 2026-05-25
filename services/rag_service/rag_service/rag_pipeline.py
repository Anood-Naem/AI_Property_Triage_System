"""RAG pipeline: ChromaDB retrieval + LangChain prompt + llama-cpp fallback."""

import json
import logging
import os
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from prompts import RAG_INSIGHT_PROMPT, RAG_MOCK_INSIGHT_TEMPLATE

logger = logging.getLogger(__name__)

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
)
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", "")
TOP_K = int(os.getenv("TOP_K", "3"))
COLLECTION_NAME = "property_listings"


class RAGPipeline:
    """Vector retrieval and insight generation."""

    def __init__(self) -> None:
        self._chroma = None
        self._collection = None
        self._embeddings = None
        self._llm = None
        self._init_chroma()
        self._init_llm()

    def _init_chroma(self) -> None:
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            os.makedirs(CHROMA_DIR, exist_ok=True)
            self._chroma = chromadb.PersistentClient(path=CHROMA_DIR)
            self._embeddings = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME
            )
            self._collection = self._chroma.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embeddings,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialized at %s (count=%s)", CHROMA_DIR, self._collection.count())
        except Exception as exc:
            logger.warning("ChromaDB init failed: %s", exc)
            self._collection = None

    def _init_llm(self) -> None:
        if GGUF_MODEL_PATH and os.path.isfile(GGUF_MODEL_PATH):
            try:
                from langchain_community.llms import LlamaCpp

                self._llm = LlamaCpp(
                    model_path=GGUF_MODEL_PATH,
                    temperature=0.1,
                    max_tokens=512,
                    verbose=False,
                )
                logger.info("LlamaCpp model loaded from %s", GGUF_MODEL_PATH)
            except Exception as exc:
                logger.warning("LlamaCpp load failed: %s", exc)
        else:
            logger.info("No GGUF model; using template insight generation")

    def retrieve(self, description: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = top_k or TOP_K
        if not self._collection:
            return self._mock_retrieval(description, k)
        try:
            doc_count = self._collection.count()
            if doc_count == 0:
                return self._mock_retrieval(description, k)
            results = self._collection.query(
                query_texts=[description],
                n_results=min(k, doc_count),
            )
            if not results.get("ids") or not results["ids"][0]:
                return self._mock_retrieval(description, k)

            similar: list[dict[str, Any]] = []
            for i, doc_id in enumerate(results["ids"][0]):
                meta = (results.get("metadatas") or [[]])[0][i] or {}
                dist = (results.get("distances") or [[1.0]])[0][i]
                similarity = round(max(0.0, 1.0 - float(dist)), 2)
                features_raw = meta.get("features", "[]")
                try:
                    features = json.loads(features_raw) if isinstance(features_raw, str) else features_raw
                except json.JSONDecodeError:
                    features = []
                similar.append(
                    {
                        "id": str(doc_id),
                        "title": meta.get("title", ""),
                        "property_type": meta.get("property_type", ""),
                        "location": meta.get("location", ""),
                        "price": meta.get("price", ""),
                        "features": features if isinstance(features, list) else [],
                        "similarity_score": similarity,
                    }
                )
            return similar
        except Exception as exc:
            logger.error("Retrieval error: %s", exc)
            return self._mock_retrieval(description, k)

    def _mock_retrieval(self, description: str, k: int) -> list[dict[str, Any]]:
        desc_lower = description.lower()
        mocks = [
            {
                "id": "L001",
                "title": "Renovated 3-Room Apartment Haifa",
                "property_type": "apartment",
                "location": "Haifa",
                "price": "1,850,000 ILS",
                "features": ["sea view", "balcony", "parking", "renovated kitchen"],
                "similarity_score": 0.88 if "haifa" in desc_lower else 0.62,
            },
            {
                "id": "L011",
                "title": "3-Room Apartment Haifa Hadar",
                "property_type": "apartment",
                "location": "Haifa, Hadar",
                "price": "1,720,000 ILS",
                "features": ["renovated", "parking"],
                "similarity_score": 0.84 if "haifa" in desc_lower else 0.58,
            },
            {
                "id": "L002",
                "title": "Luxury Villa Herzliya Pituach",
                "property_type": "villa",
                "location": "Herzliya Pituach",
                "price": "8,500,000 ILS",
                "features": ["pool", "garden"],
                "similarity_score": 0.55,
            },
        ]
        return sorted(mocks, key=lambda x: x["similarity_score"], reverse=True)[:k]

    def _format_context(self, listings: list[dict[str, Any]]) -> str:
        lines = []
        for item in listings:
            lines.append(
                f"ID: {item['id']} | {item['title']} | Type: {item['property_type']} | "
                f"Location: {item['location']} | Price: {item['price']} | "
                f"Features: {', '.join(item.get('features', []))} | Score: {item['similarity_score']}"
            )
        return "\n".join(lines)

    def generate_insight(self, description: str, similar_listings: list[dict[str, Any]]) -> str:
        context = self._format_context(similar_listings)
        if self._llm:
            try:
                prompt = PromptTemplate.from_template(RAG_INSIGHT_PROMPT)
                chain = prompt | self._llm | StrOutputParser()
                return str(chain.invoke({"context": context, "description": description})).strip()
            except Exception as exc:
                logger.warning("LLM insight failed: %s", exc)
        return self._template_insight(similar_listings)

    def _template_insight(self, similar_listings: list[dict[str, Any]]) -> str:
        if not similar_listings:
            return "No similar listings retrieved. Similarity is limited based on available data."
        ids = ", ".join(item["id"] for item in similar_listings)
        scores = ", ".join(str(item["similarity_score"]) for item in similar_listings)
        locations = ", ".join(
            sorted({item["location"] for item in similar_listings if item.get("location")})
        )
        features = ", ".join(
            dict.fromkeys(
                f for item in similar_listings for f in (item.get("features") or [])[:2]
            )
        ) or "general residential features"
        avg_score = sum(item["similarity_score"] for item in similar_listings) / len(
            similar_listings
        )
        insight = RAG_MOCK_INSIGHT_TEMPLATE.format(
            ids=ids,
            scores=scores,
            locations=locations or "various",
            features=features,
        )
        if avg_score < 0.5:
            insight += " Similarity is limited based on available data."
        return insight

    def query(self, description: str) -> dict[str, Any]:
        similar = self.retrieve(description)
        insight = self.generate_insight(description, similar)
        return {"similar_listings": similar, "insight": insight}
