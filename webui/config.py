import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


N8N_WEBHOOK_URL = "http://localhost:5678/webhook/ai-property-analysis"

# Groq models
GROQ_TEXT_MODEL = "llama-3.1-8b-instant"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Perplexity Sonar realtime web model
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
SONAR_MODEL = "sonar-pro"

MAX_HISTORY_MESSAGES = 12

DB_PATH = BASE_DIR / "chat_history.db"
UPLOAD_DIR = BASE_DIR / "chat_uploads"
CSS_PATH = BASE_DIR / "styles.css"

UPLOAD_DIR.mkdir(exist_ok=True)


# Pinecone Knowledge Base
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "property-reports")
PINECONE_CLOUD = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.environ.get("PINECONE_REGION", "us-east-1")
PINECONE_NAMESPACE = os.environ.get("PINECONE_NAMESPACE", "reports")

# Local embedding model
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "384"))

RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))


def get_groq_api_key():
    return os.environ.get("GROQ_API_KEY")


def get_perplexity_api_key():
    return os.environ.get("PERPLEXITY_API_KEY")