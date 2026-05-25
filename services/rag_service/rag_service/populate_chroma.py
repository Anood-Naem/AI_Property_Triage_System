"""Populate ChromaDB with synthetic property listings."""

import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
)
COLLECTION_NAME = "property_listings"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LISTINGS_PATH = os.path.join(SCRIPT_DIR, "synthetic_listings.json")


def main() -> int:
    if not os.path.isfile(LISTINGS_PATH):
        logger.error("Missing %s", LISTINGS_PATH)
        return 1

    with open(LISTINGS_PATH, encoding="utf-8") as f:
        listings = json.load(f)

    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        logger.error("Install chromadb: pip install chromadb")
        return 1

    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )

    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Deleted existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []
    for item in listings:
        doc_text = (
            f"{item['title']}. {item['property_type']} in {item['location']}. "
            f"Price: {item['price']}. Features: {', '.join(item['features'])}. "
            f"{item.get('description', '')}"
        )
        ids.append(item["id"])
        documents.append(doc_text)
        metadatas.append(
            {
                "title": item["title"],
                "property_type": item["property_type"],
                "location": item["location"],
                "price": item["price"],
                "features": json.dumps(item["features"]),
            }
        )

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Indexed %d listings into ChromaDB at %s", len(ids), CHROMA_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
