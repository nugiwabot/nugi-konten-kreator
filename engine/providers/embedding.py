import json
import logging
import math
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from engine.config import EMBEDDING_URL, EMBEDDING_MODEL, EMBEDDING_TIMEOUT

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
    Lightweight deterministic fallback embedding provider.
    Used when local embedding servers (e.g., LM Studio) are unavailable.
    Generates a normalized 128-dimensional frequency-hash embedding.
    """
    
    def __init__(self, dim: int = 128):
        self.dim = dim

    def _hash_embed(self, text: str) -> List[float]:
        tokens = re.findall(r"\w+", text.lower())
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        for token in tokens:
            idx = abs(hash(token)) % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    def get_embedding(self, text: str) -> List[float]:
        return self._hash_embed(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_embed(t) for t in texts]


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Calls local OpenAI-compatible embedding API (e.g., LM Studio).
    Automatically falls back to FallbackEmbeddingProvider if offline.
    """
    
    def __init__(
        self,
        endpoint_url: str = EMBEDDING_URL,
        model_name: str = EMBEDDING_MODEL,
        timeout: int = EMBEDDING_TIMEOUT,
        enable_fallback: bool = True
    ):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout = timeout
        self.enable_fallback = enable_fallback
        self.fallback = FallbackEmbeddingProvider()
        self._is_available: Optional[bool] = None

    def get_embedding(self, text: str) -> List[float]:
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else []

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        if self._is_available is False and self.enable_fallback:
            return self.fallback.get_embeddings(texts)
        
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
                return [item["embedding"] for item in data_list]
        except Exception as e:
            self._is_available = False
            logger.warning(
                f"Local embedding endpoint {self.endpoint_url} failed: {e}. "
                f"Fallback status: {self.enable_fallback}"
            )
            if self.enable_fallback:
                return self.fallback.get_embeddings(texts)
            raise ConnectionError(f"Embedding server unreachable: {e}")
