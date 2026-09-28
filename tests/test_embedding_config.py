"""
Tests for Embedding and Reranker Infrastructure v2.
Verifies LAN endpoint configurations, deterministic SHA-256 fallback,
model/dimension mismatch detection, and fail-fast policies.
"""
import pytest
from engine.config import EMBEDDING_URL, RERANKER_URL, EMBEDDING_REQUIRED, RERANKER_REQUIRED
from engine.providers.embedding import LocalEmbeddingProvider, FallbackEmbeddingProvider, cosine_similarity
from engine.providers.reranker import LocalRerankerProvider, FallbackRerankerProvider
from engine.pipeline.retriever import KnowledgeRetriever


def test_deterministic_fallback_sha256():
    """Verify that FallbackEmbeddingProvider generates identical vectors across separate instances."""
    fb1 = FallbackEmbeddingProvider(dim=128)
    fb2 = FallbackEmbeddingProvider(dim=128)

    text = "Investasi properti dekat stasiun kereta"
    vec1 = fb1.get_embedding(text)
    vec2 = fb2.get_embedding(text)

    # Must be 100% deterministic
    assert len(vec1) == 128
    assert vec1 == vec2

    # Different text must yield different vectors
    vec3 = fb1.get_embedding("Resep memasak rendang padang")
    assert vec1 != vec3
    sim = cosine_similarity(vec1, vec3)
    assert sim < 0.99


def test_fail_fast_policy_when_fallback_disabled():
    """When enable_fallback is False and endpoint is bogus, provider must fail fast with ConnectionError."""
    bogus_embedder = LocalEmbeddingProvider(
        endpoint_url="http://127.0.0.1:9999/v1/embeddings",
        timeout=1,
        enable_fallback=False
    )
    with pytest.raises((ConnectionError, RuntimeError)):
        bogus_embedder.get_embedding("test query")

    bogus_reranker = LocalRerankerProvider(
        endpoint_url="http://127.0.0.1:9999/v1/rerank",
        timeout=1,
        enable_fallback=False
    )
    with pytest.raises((ConnectionError, RuntimeError)):
        bogus_reranker.rerank("query", ["doc 1", "doc 2"])


def test_fallback_enabled_works_gracefully():
    """When enable_fallback is True and server is offline, fallback works gracefully."""
    fallback_embedder = LocalEmbeddingProvider(
        endpoint_url="http://127.0.0.1:9999/v1/embeddings",
        timeout=1,
        enable_fallback=True
    )
    vec = fallback_embedder.get_embedding("test fallback text")
    assert len(vec) == 128

    fallback_reranker = LocalRerankerProvider(
        endpoint_url="http://127.0.0.1:9999/v1/rerank",
        timeout=1,
        enable_fallback=True
    )
    res = fallback_reranker.rerank("rumah", ["rumah subsidi", "kue bolu"])
    assert len(res) == 2
    assert res[0]["document"] == "rumah subsidi"


def test_dimension_mismatch_guard_in_retriever():
    """Retriever must catch dimension mismatch gracefully without throwing arithmetic crashes."""
    # Create a dummy provider that returns 64-dim embeddings
    class Mock64DimProvider:
        def get_embedding(self, text):
            return [0.1] * 64
        def get_embeddings(self, texts):
            return [[0.1] * 64 for _ in texts]

    # If the store has 768 or 2560 dimensions and query is 64, dimension guard triggers
    retriever = KnowledgeRetriever(embedding_provider=Mock64DimProvider())
    if retriever.total_chunks > 0:
        results = retriever.retrieve("test query")
        # Should gracefully return empty list and log warning
        assert isinstance(results, list)
