import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Embedding Configuration v2 (LAN / Local)
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://192.168.0.114:1234/v1/embeddings")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen3-Embedding-4B-Q4_K_M.gguf")
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", "30"))
EMBEDDING_REQUIRED = os.getenv("EMBEDDING_REQUIRED", "true").lower() in ("true", "1", "yes")

# Reranker Configuration v2 (LAN / Local)
RERANKER_URL = os.getenv("RERANKER_URL", "http://192.168.0.114:8080/v1/rerank")
RERANKER_TIMEOUT = int(os.getenv("RERANKER_TIMEOUT", "30"))
RERANKER_REQUIRED = os.getenv("RERANKER_REQUIRED", "true").lower() in ("true", "1", "yes")

# Fallback Safety Policy
ALLOW_FALLBACK = os.getenv("ALLOW_FALLBACK", "false").lower() in ("true", "1", "yes")

# Local Storage Configuration
KNOWLEDGE_STORE_PATH = Path(os.getenv("KNOWLEDGE_STORE_PATH", str(BASE_DIR / "engine" / "data" / "knowledge_store.json")))
DEFAULT_PDF_DIR = Path(os.getenv("PDF_DIR", str(BASE_DIR / "data" / "books")))

# Web Research Configuration
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "6"))

# Media Retrieval Configuration
MEDIA_ASSETS_DIR = Path(os.getenv("MEDIA_ASSETS_DIR", str(BASE_DIR / "assets" / "media")))
MEDIA_SEARCH_MAX_RESULTS = int(os.getenv("MEDIA_SEARCH_MAX_RESULTS", "20"))
MEDIA_DOWNLOAD_TIMEOUT = int(os.getenv("MEDIA_DOWNLOAD_TIMEOUT", "60"))
MEDIA_MAX_FILE_SIZE_MB = int(os.getenv("MEDIA_MAX_FILE_SIZE_MB", "500"))
WIKIMEDIA_API_URL = os.getenv("WIKIMEDIA_API_URL", "https://commons.wikimedia.org/w/api.php")
INTERNET_ARCHIVE_API_URL = os.getenv("INTERNET_ARCHIVE_API_URL", "https://archive.org")
PEXAFY_MCP_URL = os.getenv("PEXAFY_MCP_URL", "https://mcp.pexafy.com/mcp")
PEXAFY_API_KEY = os.getenv("PEXAFY_API_KEY", "")

# Optional public-catalog API credentials. Providers with missing required
# credentials remain available as empty, non-blocking fallbacks.
DPLA_API_KEY = os.getenv("DPLA_API_KEY", "")
EUROPEANA_API_KEY = os.getenv("EUROPEANA_API_KEY", "")
DVIDS_API_KEY = os.getenv("DVIDS_API_KEY", "")
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
NCBI_TOOL = os.getenv("NCBI_TOOL", "NugiContentIntelligence")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")

# RSS / discovery intelligence. All feeds are optional, cached in-process, and
# discovery-only; an unavailable source does not block research or production.
RSS_DISCOVERY_ENABLED = os.getenv("RSS_DISCOVERY_ENABLED", "true").lower() in ("true", "1", "yes")
RSS_FEED_REGISTRY_PATH = Path(os.getenv("RSS_FEED_REGISTRY_PATH", str(BASE_DIR / "engine" / "data" / "feed_registry.json")))
RSSHUB_BASE_URL = os.getenv("RSSHUB_BASE_URL", "")
RSSHUB_FALLBACK_URL = os.getenv("RSSHUB_FALLBACK_URL", "")
RSS_CACHE_TTL_SECONDS = int(os.getenv("RSS_CACHE_TTL_SECONDS", "900"))
RSS_FETCH_TIMEOUT_SECONDS = int(os.getenv("RSS_FETCH_TIMEOUT_SECONDS", "8"))
RSS_MAX_FEED_BYTES = int(os.getenv("RSS_MAX_FEED_BYTES", str(2 * 1024 * 1024)))
RSS_MAX_SOURCES_PER_QUERY = int(os.getenv("RSS_MAX_SOURCES_PER_QUERY", "5"))
MEDIA_REUSABLE_LICENSES = tuple(
    item.strip().upper()
    for item in os.getenv(
        "MEDIA_REUSABLE_LICENSES",
        "PUBLIC_DOMAIN,CC0,CC_BY,CC_BY_SA,COMMERCIAL_ALLOWED,FREE_WITH_ATTRIBUTION",
    ).split(",") if item.strip()
)
