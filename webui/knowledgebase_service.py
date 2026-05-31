from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from functools import lru_cache

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_CLOUD,
    PINECONE_REGION,
    PINECONE_NAMESPACE,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSION,
    RAG_TOP_K,
)


def is_knowledgebase_configured():
    return bool(PINECONE_API_KEY)


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def get_pinecone_client():
    if not PINECONE_API_KEY:
        raise RuntimeError("Missing PINECONE_API_KEY in .env file.")

    return Pinecone(api_key=PINECONE_API_KEY)


def get_index_names(client):
    indexes = client.list_indexes()

    if hasattr(indexes, "names"):
        return indexes.names()

    return [index["name"] for index in indexes]


def is_index_ready(index_description):
    status = getattr(index_description, "status", None)

    if isinstance(status, dict):
        return bool(status.get("ready"))

    return bool(getattr(status, "ready", False))


@lru_cache(maxsize=1)
def get_pinecone_index():
    client = get_pinecone_client()
    index_names = get_index_names(client)

    if PINECONE_INDEX_NAME not in index_names:
        client.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=PINECONE_CLOUD,
                region=PINECONE_REGION,
            ),
        )

        while True:
            description = client.describe_index(PINECONE_INDEX_NAME)

            if is_index_ready(description):
                break

            time.sleep(1)

    return client.Index(PINECONE_INDEX_NAME)


def embed_texts(texts):
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
    )

    return [embedding.tolist() for embedding in embeddings]


def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def chunk_text(text, max_chars=1200, overlap=180):
    text = str(text or "").strip()

    if not text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in text.splitlines()
        if paragraph.strip()
    ]

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 <= max_chars:
            current_chunk = f"{current_chunk}\n{paragraph}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    final_chunks = []

    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
            continue

        start = 0

        while start < len(chunk):
            end = start + max_chars
            final_chunks.append(chunk[start:end])

            next_start = end - overlap

            if next_start <= start:
                break

            start = next_start

    return final_chunks


def get_report_value(report, label):
    patterns = [
        rf"\*\*{re.escape(label)}:\*\*\s*(.+)",
        rf"{re.escape(label)}:\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, str(report or ""), re.IGNORECASE)

        if match:
            value = clean_text(match.group(1))
            return value if value else "—"

    return "—"


def get_report_header(report):
    for line in str(report or "").splitlines():
        clean_line = line.strip()

        if clean_line.startswith("🏠"):
            return clean_line.replace("🏠", "").strip()

    return "Property Report"


def safe_metadata_value(value, max_length=500):
    if value is None:
        return ""

    if isinstance(value, (int, float, bool)):
        return value

    return str(value)[:max_length]


def build_report_document(result):
    report = str(result.get("report") or "").strip()
    source_description = str(result.get("_source_description") or "").strip()
    agent_name = str(result.get("_source_agent_name") or "").strip()

    return f"""
Saved Property Report

Agent Name:
{agent_name}

Original Listing Description:
{source_description}

Generated Report:
{report}
""".strip()


def build_report_metadata(result, report_id):
    report = str(result.get("report") or "")

    return {
        "report_id": report_id,
        "created_at": datetime.utcnow().isoformat(),
        "agent_name": safe_metadata_value(result.get("_source_agent_name")),
        "team": safe_metadata_value(result.get("team")),
        "property_type": safe_metadata_value(result.get("property_type")),
        "title": safe_metadata_value(get_report_header(report)),
        "location": safe_metadata_value(get_report_value(report, "Location")),
        "price": safe_metadata_value(get_report_value(report, "Price")),
        "rooms": safe_metadata_value(get_report_value(report, "Rooms")),
        "confidence": safe_metadata_value(get_report_value(report, "Report confidence")),
    }


def store_report_in_knowledgebase(result):
    if not is_knowledgebase_configured():
        return {
            "stored": False,
            "message": "Knowledge Base is disabled because PINECONE_API_KEY is missing.",
        }

    report = str(result.get("report") or "").strip()

    if not report:
        return {
            "stored": False,
            "message": "No report found to store.",
        }

    try:
        document_text = build_report_document(result)
        report_hash = hashlib.sha256(document_text.encode("utf-8")).hexdigest()[:16]
        report_id = f"report-{report_hash}"

        chunks = chunk_text(document_text)

        if not chunks:
            return {
                "stored": False,
                "message": "Report text is empty after chunking.",
            }

        vectors = embed_texts(chunks)
        index = get_pinecone_index()
        base_metadata = build_report_metadata(result, report_id)

        pinecone_vectors = []

        for chunk_index, vector in enumerate(vectors):
            metadata = {
                **base_metadata,
                "chunk_index": chunk_index,
                "text": chunks[chunk_index][:3500],
            }

            pinecone_vectors.append(
                {
                    "id": f"{report_id}-chunk-{chunk_index}",
                    "values": vector,
                    "metadata": metadata,
                }
            )

        index.upsert(
            vectors=pinecone_vectors,
            namespace=PINECONE_NAMESPACE,
        )

        return {
            "stored": True,
            "report_id": report_id,
            "chunks": len(chunks),
            "message": "Report saved to Knowledge Base.",
        }

    except Exception as error:
        return {
            "stored": False,
            "message": f"Knowledge Base error: {error}",
        }


def search_reports(user_text, top_k=None, min_score=0.25):
    if not is_knowledgebase_configured():
        return []

    if not str(user_text or "").strip():
        return []

    try:
        index = get_pinecone_index()
        query_vector = embed_texts([user_text])[0]

        response = index.query(
            vector=query_vector,
            top_k=top_k or RAG_TOP_K,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE,
        )

        matches = getattr(response, "matches", None)

        if matches is None and isinstance(response, dict):
            matches = response.get("matches", [])

        results = []

        for match in matches or []:
            score = getattr(match, "score", None)
            metadata = getattr(match, "metadata", None)

            if isinstance(match, dict):
                score = match.get("score")
                metadata = match.get("metadata", {})

            if score is None or score < min_score:
                continue

            results.append(
                {
                    "score": score,
                    "metadata": metadata or {},
                }
            )

        return results

    except Exception:
        return []


def build_rag_context(user_text):
    matches = search_reports(user_text)

    if not matches:
        return ""

    context_blocks = []

    for index, match in enumerate(matches, start=1):
        metadata = match["metadata"]

        context_blocks.append(
            f"""
[Saved Report Match {index}]
Score: {match["score"]}
Title: {metadata.get("title", "—")}
Location: {metadata.get("location", "—")}
Price: {metadata.get("price", "—")}
Rooms: {metadata.get("rooms", "—")}
Property Type: {metadata.get("property_type", "—")}
Team: {metadata.get("team", "—")}
Report Text:
{metadata.get("text", "")}
""".strip()
        )

    return "\n\n---\n\n".join(context_blocks)