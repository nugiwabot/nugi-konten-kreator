import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Embedding Configuration
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://localhost:1234/v1/embeddings")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", "10"))

# Reranker Configuration
RERANKER_URL = os.getenv("RERANKER_URL", "http://127.0.0.1:8080/v1/rerank")
RERANKER_TIMEOUT = int(os.getenv("RERANKER_TIMEOUT", "10"))

# Local Storage Configuration
KNOWLEDGE_STORE_PATH = Path(os.getenv("KNOWLEDGE_STORE_PATH", str(BASE_DIR / "engine" / "data" / "knowledge_store.json")))
DEFAULT_PDF_DIR = Path(os.getenv("PDF_DIR", r"C:\Users\Nugi\Downloads"))

# Web Research Configuration
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "6"))

# Media Retrieval Configuration
MEDIA_ASSETS_DIR = Path(os.getenv("MEDIA_ASSETS_DIR", str(BASE_DIR / "assets" / "media")))
MEDIA_SEARCH_MAX_RESULTS = int(os.getenv("MEDIA_SEARCH_MAX_RESULTS", "20"))
MEDIA_DOWNLOAD_TIMEOUT = int(os.getenv("MEDIA_DOWNLOAD_TIMEOUT", "60"))
MEDIA_MAX_FILE_SIZE_MB = int(os.getenv("MEDIA_MAX_FILE_SIZE_MB", "500"))
WIKIMEDIA_API_URL = os.getenv("WIKIMEDIA_API_URL", "https://commons.wikimedia.org/w/api.php")
INTERNET_ARCHIVE_API_URL = os.getenv("INTERNET_ARCHIVE_API_URL", "https://archive.org")
