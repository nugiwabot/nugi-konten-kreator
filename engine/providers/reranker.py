import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from engine.config import RERANKER_URL, RERANKER_TIMEOUT

logger = logging.getLogger(__name__)


class RerankerProvider:
    """Abstract interface for reranking candidate documents against a query."""
    
    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError


class FallbackRerankerProvider(RerankerProvider):
    """
    Pass-through / token-overlap fallback reranker.
    Used when the local reranker server is offline.
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
    Default: http://127.0.0.1:8080/v1/rerank
    Automatically falls back to FallbackRerankerProvider if offline.
    """
    
    def __init__(
        self,
        endpoint_url: str = RERANKER_URL,
        timeout: int = RERANKER_TIMEOUT,
        enable_fallback: bool = True
    ):
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.enable_fallback = enable_fallback
        self.fallback = FallbackRerankerProvider()

    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        if not documents:
            return []
            
        payload = {
            "query": query,
            "documents": documents
        }
        if top_n is not None:
            payload["top_n"] = top_n
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                # Format: {"results": [{"index": int, "relevance_score": float}, ...]}
                results = result.get("results", [])
                formatted = []
                for item in results:
                    idx = item["index"]
                    formatted.append({
                        "index": idx,
                        "relevance_score": float(item.get("relevance_score", 0.0)),
                        "document": documents[idx] if idx < len(documents) else ""
                    })
                formatted.sort(key=lambda x: x["relevance_score"], reverse=True)
                if top_n is not None:
                    formatted = formatted[:top_n]
                return formatted
        except Exception as e:
            logger.warning(
                f"Local reranker endpoint {self.endpoint_url} failed: {e}. "
                f"Fallback status: {self.enable_fallback}"
            )
            if self.enable_fallback:
                return self.fallback.rerank(query, documents, top_n)
            raise ConnectionError(f"Reranker server unreachable: {e}")
