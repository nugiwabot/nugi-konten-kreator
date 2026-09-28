import hashlib
import json
import logging
import math
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from engine.config import EMBEDDING_URL, EMBEDDING_MODEL, EMBEDDING_TIMEOUT, ALLOW_FALLBACK

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingProvider:
    """Abstract interface for embedding generation."""
    
    def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class FallbackEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic SHA-256 fallback embedding provider.
    Used when local embedding servers (e.g., LM Studio) are unavailable during development/testing.
    Generates a normalized, cross-platform deterministic embedding vector without Python hash randomization.
    """
    
    def __init__(self, dim: int = 128):
        self.dim = dim

    def _sha256_embed(self, text: str) -> List[float]:
        tokens = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            # Sign from next byte to prevent positive distribution bias
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    def get_embedding(self, text: str) -> List[float]:
        return self._sha256_embed(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._sha256_embed(t) for t in texts]


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Calls local OpenAI-compatible embedding API (e.g., LM Studio).
    Enforces fail-fast policy in production when ALLOW_FALLBACK is False.
    """
    
    def __init__(
        self,
        endpoint_url: str = EMBEDDING_URL,
        model_name: str = EMBEDDING_MODEL,
        timeout: int = EMBEDDING_TIMEOUT,
        enable_fallback: Optional[bool] = None
    ):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout = timeout
        self.enable_fallback = enable_fallback if enable_fallback is not None else ALLOW_FALLBACK
        self.fallback = FallbackEmbeddingProvider()
        self._is_available: Optional[bool] = None
        self._detected_dimension: Optional[int] = None

    def is_alive(self) -> bool:
        """Pings embedding service with a lightweight test vector."""
        try:
            emb = self.get_embedding("ping")
            self._is_available = bool(emb)
            if emb:
                self._detected_dimension = len(emb)
            return self._is_available
        except Exception:
            self._is_available = False
            return False

    def get_embedding(self, text: str) -> List[float]:
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else []

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self._is_available is False:
            if self.enable_fallback:
                return self.fallback.get_embeddings(texts)
            raise ConnectionError(
                f"Embedding server unreachable at {self.endpoint_url} and ALLOW_FALLBACK is False."
            )
        
        payload = {
            "model": self.model_name,
            "input": texts
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                # OpenAI format: {"data": [{"embedding": [...], "index": 0}, ...]}
                data_list = sorted(result.get("data", []), key=lambda x: x.get("index", 0))
                embs = [item["embedding"] for item in data_list]
                self._is_available = True
                if embs and not self._detected_dimension:
                    self._detected_dimension = len(embs[0])
                return embs
        except Exception as e:
            self._is_available = False
            logger.warning(
                f"Local embedding endpoint {self.endpoint_url} failed: {e}. "
                f"Fallback status: {self.enable_fallback}"
            )
            if self.enable_fallback:
                return self.fallback.get_embeddings(texts)
            raise ConnectionError(
                f"Embedding server unreachable at {self.endpoint_url}: {e} (ALLOW_FALLBACK=False)"
            )
