import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from engine.config import KNOWLEDGE_STORE_PATH
from engine.providers.embedding import LocalEmbeddingProvider, EmbeddingProvider, cosine_similarity
from engine.providers.reranker import LocalRerankerProvider, RerankerProvider

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    Two-stage knowledge retrieval pipeline:
    Stage 1: Vector/Semantic Retrieval via EmbeddingProvider (Top-N candidates)
    Stage 2: Precision Reranking via RerankerProvider (Top-K relevant chunks)
    """

    def __init__(
        self,
        store_path: Path = KNOWLEDGE_STORE_PATH,
        embedding_provider: Optional[EmbeddingProvider] = None,
        reranker_provider: Optional[RerankerProvider] = None
    ):
        self.store_path = store_path
        self.embedding_provider = embedding_provider or LocalEmbeddingProvider()
        self.reranker_provider = reranker_provider or LocalRerankerProvider()
        self._chunks: List[Dict[str, Any]] = []
        self._load_store()

    def _load_store(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._chunks = data.get("chunks", [])
            except Exception as e:
                logger.error(f"Error loading knowledge store from {self.store_path}: {e}")
                self._chunks = []
        else:
            logger.warning(f"Knowledge store not found at {self.store_path}")
            self._chunks = []

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    def retrieve(
        self,
        query: str,
        top_k_candidates: int = 15,
        top_k_reranked: int = 5,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes 2-stage retrieval for the given query.
        """
        if not self._chunks:
            self._load_store()
            if not self._chunks:
                return []

        # 1. Generate query embedding
        query_emb = self.embedding_provider.get_embedding(query)
        if not query_emb:
            return []

        # 2. Stage 1: Cosine similarity vector search
        scored_candidates = []
        for chunk in self._chunks:
            if category_filter and category_filter.lower() not in chunk.get("book", "").lower():
                continue
            chunk_emb = chunk.get("embedding", [])
            sim = cosine_similarity(query_emb, chunk_emb)
            scored_candidates.append({
                "chunk": chunk,
                "similarity_score": sim
            })

        # Sort by similarity descending
        scored_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_candidates = scored_candidates[:top_k_candidates]

        if not top_candidates:
            return []

        # 3. Stage 2: Rerank top candidates
        candidate_texts = [c["chunk"]["text"] for c in top_candidates]
        
        try:
            rerank_results = self.reranker_provider.rerank(
                query=query,
                documents=candidate_texts,
                top_n=top_k_reranked
            )
            
            final_results = []
            for r in rerank_results:
                orig_candidate = top_candidates[r["index"]]
                res = dict(orig_candidate["chunk"])
                # Remove large embedding vector from output payload for efficiency
                res.pop("embedding", None)
                res["similarity_score"] = orig_candidate["similarity_score"]
                res["rerank_score"] = r["relevance_score"]
                final_results.append(res)
            return final_results

        except Exception as e:
            logger.warning(f"Reranking failed ({e}), falling back to Stage 1 vector ranking.")
            final_results = []
            for item in top_candidates[:top_k_reranked]:
                res = dict(item["chunk"])
                res.pop("embedding", None)
                res["similarity_score"] = item["similarity_score"]
                res["rerank_score"] = item["similarity_score"]
                final_results.append(res)
            return final_results
