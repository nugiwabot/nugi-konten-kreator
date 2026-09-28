import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from engine.config import RERANKER_URL, RERANKER_TIMEOUT, ALLOW_FALLBACK

logger = logging.getLogger(__name__)


class RerankerProvider:
    """Abstract interface for reranking candidate documents against a query."""
    
    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError


class FallbackRerankerProvider(RerankerProvider):
    """
    Token-overlap fallback reranker.
    Used when the local reranker server is offline during development/testing.
    """
    
    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        query_words = set(query.lower().split())
        scored_results = []
        for idx, doc in enumerate(documents):
            doc_words = set(doc.lower().split())
            overlap = len(query_words.intersection(doc_words))
            # Basic jaccard-like score as fallback
            score = overlap / max(1, len(query_words.union(doc_words)))
            scored_results.append({
                "index": idx,
                "relevance_score": float(score),
                "document": doc
            })
        
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        if top_n is not None:
            scored_results = scored_results[:top_n]
        return scored_results


class LocalRerankerProvider(RerankerProvider):
    """
    Calls local TEI/vLLM/LM Studio compatible rerank API endpoint.
    Default: http://192.168.0.114:8080/v1/rerank
    Enforces fail-fast policy when ALLOW_FALLBACK is False.
    """
    
    def __init__(
        self,
        endpoint_url: str = RERANKER_URL,
        timeout: int = RERANKER_TIMEOUT,
        enable_fallback: Optional[bool] = None
    ):
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.enable_fallback = enable_fallback if enable_fallback is not None else ALLOW_FALLBACK
        self.fallback = FallbackRerankerProvider()
        self._is_available: Optional[bool] = None

    def is_alive(self) -> bool:
        """Pings reranker service with a lightweight test query."""
        try:
            res = self.rerank("test", ["test doc 1", "test doc 2"], top_n=1)
            self._is_available = bool(res)
            return self._is_available
        except Exception:
            self._is_available = False
            return False

    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        if not documents:
            return []
            
        if self._is_available is False:
            if self.enable_fallback:
                return self.fallback.rerank(query, documents, top_n)
            raise ConnectionError(
                f"Reranker server unreachable at {self.endpoint_url} and ALLOW_FALLBACK is False."
            )
            
        batch_size = 5
        formatted = []
        try:
            for b_idx in range(0, len(documents), batch_size):
                chunk = documents[b_idx:b_idx + batch_size]
                payload = {
                    "query": query,
                    "documents": chunk
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self.endpoint_url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    results = result.get("results", [])
                    for item in results:
                        orig_idx = b_idx + item["index"]
                        formatted.append({
                            "index": orig_idx,
                            "relevance_score": float(item.get("relevance_score", 0.0)),
                            "document": documents[orig_idx] if orig_idx < len(documents) else ""
                        })

            formatted.sort(key=lambda x: x["relevance_score"], reverse=True)
            if top_n is not None:
                formatted = formatted[:top_n]
            self._is_available = True
            return formatted
        except Exception as e:
            self._is_available = False
            logger.warning(
                f"Local reranker endpoint {self.endpoint_url} failed: {e}. "
                f"Fallback status: {self.enable_fallback}"
            )
            if self.enable_fallback:
                return self.fallback.rerank(query, documents, top_n)
            raise ConnectionError(
                f"Reranker server unreachable at {self.endpoint_url}: {e} (ALLOW_FALLBACK=False)"
            )
