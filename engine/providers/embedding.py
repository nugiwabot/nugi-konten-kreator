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
        self._cache: Dict[str, List[float]] = {}

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

        # Return cached vectors where available
        uncached_indices = []
        uncached_texts = []
        results: List[Optional[List[float]]] = [None] * len(texts)

        for idx, t in enumerate(texts):
            t_key = t.strip()
            if t_key in self._cache:
                results[idx] = self._cache[t_key]
            else:
                uncached_indices.append(idx)
                uncached_texts.append(t)

        if not uncached_texts:
            return [r for r in results if r is not None]

        if self._is_available is False:
            if self.enable_fallback:
                fallback_embs = self.fallback.get_embeddings(uncached_texts)
                for idx, emb in zip(uncached_indices, fallback_embs):
                    results[idx] = emb
                return [r for r in results if r is not None]
            raise ConnectionError(
                f"Embedding server unreachable at {self.endpoint_url} and ALLOW_FALLBACK is False."
            )
        
        embs: List[List[float]] = []
        batch_size = 2
        try:
            for i in range(0, len(texts), batch_size):
                chunk = texts[i:i + batch_size]
                payload = {
                    "model": self.model_name,
                    "input": chunk
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self.endpoint_url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    data_list = sorted(result.get("data", []), key=lambda x: x.get("index", 0))
                    chunk_embs = [item["embedding"] for item in data_list]
                    embs.extend(chunk_embs)
                    for orig_text, emb in zip(chunk, chunk_embs):
                        self._cache[orig_text.strip()] = emb

            self._is_available = True
            if embs and not self._detected_dimension:
                self._detected_dimension = len(embs[0])
            for idx, emb in zip(uncached_indices, embs):
                results[idx] = emb
            return [r for r in results if r is not None]
        except Exception as e:
            self._is_available = False
            logger.warning(
                f"Local embedding endpoint {self.endpoint_url} failed: {e}. "
                f"Fallback status: {self.enable_fallback}"
            )
            if self.enable_fallback:
                logger.warning(f"Degrading to deterministic FallbackEmbeddingProvider: {e}")
                fallback_embs = self.fallback.get_embeddings(uncached_texts)
                for idx, emb in zip(uncached_indices, fallback_embs):
                    results[idx] = emb
                return [r for r in results if r is not None]
            raise ConnectionError(
                f"Embedding server unreachable at {self.endpoint_url}: {e} (ALLOW_FALLBACK=False)"
            )
