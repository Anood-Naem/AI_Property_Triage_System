import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/ai-property-analysis"

GROQ_TEXT_MODEL = "llama-3.1-8b-instant"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_HISTORY_MESSAGES = 12

DB_PATH = BASE_DIR / "chat_history.db"
UPLOAD_DIR = BASE_DIR / "chat_uploads"
CSS_PATH = BASE_DIR / "styles.css"

UPLOAD_DIR.mkdir(exist_ok=True)


def get_groq_api_key():
    return os.environ.get("GROQ_API_KEY")