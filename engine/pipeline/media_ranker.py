"""
engine/pipeline/media_ranker.py
================================
Semantic media ranking pipeline using existing EmbeddingProvider and
RerankerProvider from engine/providers/.

Ranking is multi-stage:
  1. Deduplicate candidates by download_url
  2. Compute embedding similarity (query emb vs metadata text emb)
  3. Reranker precision pass (original request vs metadata text)
  4. Combine scores → final_rank

If local embedding / reranker services are offline:
  - Gracefully fall back to keyword overlap scoring
  - Report which services were unavailable (fallback_reason)

IMPORTANT:
  - Semantic representation is TEXT-ONLY from metadata fields.
  - We do NOT claim to do visual (pixel-level) embedding.
  - Embedding cache prevents re-computing the same metadata string.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from engine.providers.embedding import (
    EmbeddingProvider,
    FallbackEmbeddingProvider,
    LocalEmbeddingProvider,
    cosine_similarity,
)
from engine.providers.media import MediaItem
from engine.providers.reranker import (
    FallbackRerankerProvider,
    LocalRerankerProvider,
    RerankerProvider,
)

logger = logging.getLogger(__name__)


class MediaRanker:
    """
    Multi-stage semantic ranker for MediaItem candidates.

    Reuses existing EmbeddingProvider + RerankerProvider without modification.
    Maintains a simple in-memory embedding cache to avoid re-embedding the
    same metadata representation.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        reranker_provider: Optional[RerankerProvider] = None,
    ):
        self.embedder: EmbeddingProvider = embedding_provider or LocalEmbeddingProvider()
        self.reranker: RerankerProvider = reranker_provider or LocalRerankerProvider()
        self._embedding_cache: Dict[str, List[float]] = {}
        self._embedding_ok: Optional[bool] = None   # None = not yet checked
        self._reranker_ok: Optional[bool] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def rank(
        self,
        original_request: str,
        candidates: List[MediaItem],
        top_n: int = 10,
    ) -> Tuple[List[MediaItem], str]:
        """
        Rank candidates against the original user request.

        Returns:
            (ranked_items, fallback_reason)
            - ranked_items: sorted by final_rank, highest relevance first
            - fallback_reason: empty string if full pipeline ran;
                               description of what was skipped otherwise.
        """
        if not candidates:
            return [], ""

        # Stage 1: Deduplicate
        candidates = self._deduplicate(candidates)
        logger.info(f"MediaRanker: {len(candidates)} candidates after dedup")

        # Stage 2: Embedding similarity
        candidates, emb_ok, emb_reason = self._apply_embedding(
            original_request, candidates
        )

        # Stage 3: Reranker
        candidates, rer_ok, rer_reason = self._apply_reranker(
            original_request, candidates
        )

        # Stage 4: Combine scores into final_rank
        candidates = self._compute_final_rank(candidates, emb_ok, rer_ok)

        fallback_reason = ""
        if not emb_ok and not rer_ok:
            fallback_reason = (
                "Semantic ranking unavailable: local embedding and reranker services "
                "were not reachable. Keyword/metadata fallback ranking was used."
            )
        elif not emb_ok:
            fallback_reason = f"Embedding service unavailable ({emb_reason}). Reranker was used alone."
        elif not rer_ok:
            fallback_reason = f"Reranker service unavailable ({rer_reason}). Embedding similarity was used alone."

        return candidates[:top_n], fallback_reason

    def get_status(self) -> Dict[str, str]:
        """
        Quick health check — probe embedding + reranker services.
        Returns status dict compatible with `media doctor` command.
        """
        emb_status = self._probe_embedding()
        rer_status = self._probe_reranker()
        return {
            "embedding": "OK" if emb_status else "OFFLINE",
            "reranker": "OK" if rer_status else "OFFLINE",
        }

    # ------------------------------------------------------------------
    # Stage 1: Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(candidates: List[MediaItem]) -> List[MediaItem]:
        """Remove duplicate items by dedup_key (download_url or provider:id)."""
        seen: set = set()
        result: List[MediaItem] = []
        for item in candidates:
            key = item.dedup_key()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    # ------------------------------------------------------------------
    # Stage 2: Embedding similarity
    # ------------------------------------------------------------------

    def _apply_embedding(
        self,
        query: str,
        candidates: List[MediaItem],
    ) -> Tuple[List[MediaItem], bool, str]:
        """
        Compute cosine similarity between query embedding and each
        candidate's metadata text embedding.

        Returns: (updated_candidates, success_bool, error_reason_str)
        """
        try:
            # Embed the query
            query_emb = self._cached_embed(query)
            if not query_emb:
                return candidates, False, "empty embedding response"

            # Embed each candidate's text representation
            texts = [item.build_text_representation() for item in candidates]
            candidate_embs = self._get_embeddings_cached(texts)

            if not candidate_embs or len(candidate_embs) != len(candidates):
                return candidates, False, "candidate embedding count mismatch"

            for item, emb in zip(candidates, candidate_embs):
                sim = cosine_similarity(query_emb, emb)
                item.embedding_similarity = round(sim, 4)

            return candidates, True, ""

        except Exception as e:
            logger.warning(f"MediaRanker embedding stage failed: {e}")
            # Apply keyword-based fallback score to embedding field
            candidates = self._keyword_score_fallback(query, candidates)
            return candidates, False, str(e)

    def _cached_embed(self, text: str) -> List[float]:
        """Embed text with in-memory cache."""
        cache_key = text[:300]  # Key by first 300 chars
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        embeddings = self.embedder.get_embeddings([text])
        emb = embeddings[0] if embeddings else []
        if emb:
            self._embedding_cache[cache_key] = emb
        return emb

    def _get_embeddings_cached(self, texts: List[str]) -> List[List[float]]:
        """Batch embed with cache."""
        to_embed_indices: List[int] = []
        to_embed_texts: List[str] = []
        results: List[List[float]] = [[] for _ in texts]

        for i, text in enumerate(texts):
            key = text[:300]
            if key in self._embedding_cache:
                results[i] = self._embedding_cache[key]
            else:
                to_embed_indices.append(i)
                to_embed_texts.append(text)

        if to_embed_texts:
            new_embs = self.embedder.get_embeddings(to_embed_texts)
            for idx, emb in zip(to_embed_indices, new_embs):
                key = texts[idx][:300]
                self._embedding_cache[key] = emb
                results[idx] = emb

        return results

    # ------------------------------------------------------------------
    # Stage 3: Reranker
    # ------------------------------------------------------------------

    def _apply_reranker(
        self,
        original_request: str,
        candidates: List[MediaItem],
    ) -> Tuple[List[MediaItem], bool, str]:
        """
        Run reranker with the ORIGINAL user request (not expanded keywords)
        against each candidate's text representation.

        Returns: (updated_candidates, success_bool, error_reason_str)
        """
        if not candidates:
            return candidates, True, ""

        try:
            texts = [item.build_text_representation() for item in candidates]
            rerank_results = self.reranker.rerank(
                query=original_request,
                documents=texts,
            )
            # Map reranker scores back to items
            score_map: Dict[int, float] = {
                r["index"]: float(r.get("relevance_score", 0.0))
                for r in rerank_results
            }
            for i, item in enumerate(candidates):
                item.reranker_score = round(score_map.get(i, 0.0), 4)

            return candidates, True, ""

        except Exception as e:
            logger.warning(f"MediaRanker reranker stage failed: {e}")
            # Reranker failed — reranker_score stays 0.0, handled in final rank
            return candidates, False, str(e)

    # ------------------------------------------------------------------
    # Stage 4: Final rank computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_final_rank(
        candidates: List[MediaItem],
        emb_ok: bool,
        rer_ok: bool,
    ) -> List[MediaItem]:
        """
        Combine available scores into a sortable composite.

        Priority logic:
          Both available   → 0.4 * embedding + 0.6 * reranker
          Only embedding   → embedding_similarity (as final score)
          Only reranker    → reranker_score (as final score)
          Neither          → keyword_score (set by fallback) or 0
        """
        for item in candidates:
            if emb_ok and rer_ok:
                composite = 0.4 * item.embedding_similarity + 0.6 * item.reranker_score
            elif emb_ok:
                composite = item.embedding_similarity
            elif rer_ok:
                composite = item.reranker_score
            else:
                composite = item.keyword_score

            # Store composite back in reranker_score for transparency in output
            item.reranker_score = round(composite, 4)

        # Sort descending by composite score
        candidates.sort(key=lambda x: x.reranker_score, reverse=True)

        # Assign final_rank (1-indexed)
        for rank_idx, item in enumerate(candidates, 1):
            item.final_rank = rank_idx

        return candidates

    # ------------------------------------------------------------------
    # Keyword fallback (when embedding offline)
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_score_fallback(
        query: str, candidates: List[MediaItem]
    ) -> List[MediaItem]:
        """
        Assign embedding_similarity based on keyword overlap as a fallback.
        Uses title + description text vs query words.
        """
        import re
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        if not query_words:
            return candidates

        for item in candidates:
            combined = f"{item.title} {item.description} {item.creator} {item.date}".lower()
            doc_words = set(re.findall(r"\b\w+\b", combined))
            overlap = len(query_words & doc_words)
            score = overlap / max(1, len(query_words))
            item.embedding_similarity = round(score, 4)
            item.keyword_score = item.embedding_similarity

        return candidates

    # ------------------------------------------------------------------
    # Health probes
    # ------------------------------------------------------------------

    def _probe_embedding(self) -> bool:
        """Return True if embedding service responds."""
        try:
            embs = self.embedder.get_embeddings(["test"])
            # A non-empty embedding from LocalEmbeddingProvider means service is up
            # FallbackEmbeddingProvider also returns non-empty — distinguish by type
            from engine.providers.embedding import LocalEmbeddingProvider as LEP
            if isinstance(self.embedder, LEP):
                # If we get a 128-dim vector, it's the fallback (service offline)
                # If service is up, vector should match model dimension (usually >128)
                return bool(embs and len(embs[0]) > 128)
            return bool(embs and embs[0])
        except Exception:
            return False

    def _probe_reranker(self) -> bool:
        """Return True if reranker service responds."""
        try:
            from engine.providers.reranker import LocalRerankerProvider as LRP, FallbackRerankerProvider as FRP
            if isinstance(self.reranker, (FRP,)):
                return False
            results = self.reranker.rerank("test query", ["test document"], top_n=1)
            # FallbackRerankerProvider always returns results — check if it's a fallback
            if isinstance(self.reranker, LRP):
                # If reranker is LocalRerankerProvider and it fell back silently,
                # we can't easily distinguish here; assume OK if no exception
                return True
            return bool(results)
        except Exception:
            return False
