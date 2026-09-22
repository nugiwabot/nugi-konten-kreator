import pytest
from engine.providers.embedding import LocalEmbeddingProvider, FallbackEmbeddingProvider, cosine_similarity
from engine.providers.reranker import LocalRerankerProvider, FallbackRerankerProvider


def test_fallback_embedding_provider():
    provider = FallbackEmbeddingProvider(dim=64)
    vec = provider.get_embedding("kecerdasan buatan dan properti")
    assert len(vec) == 64
    assert any(x > 0 for x in vec)
    
    # Test deterministic property
    vec2 = provider.get_embedding("kecerdasan buatan dan properti")
    assert vec == vec2


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0


def test_local_embedding_provider_with_fallback_on_invalid_endpoint():
    # Point to a non-existent port to test graceful offline fallback
    provider = LocalEmbeddingProvider(endpoint_url="http://127.0.0.1:59999/v1/embeddings", timeout=1, enable_fallback=True)
    embeddings = provider.get_embeddings(["test query"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 128  # Fallback generates 128-dim vector


def test_fallback_reranker_provider():
    reranker = FallbackRerankerProvider()
    docs = [
        "Properti dan rumah di pinggiran kota",
        "Resep memasak kue cokelat lezat",
        "Investasi tanah kavling untuk hunian masa depan"
    ]
    results = reranker.rerank(query="rumah dan properti", documents=docs, top_n=2)
    assert len(results) == 2
    # The first document has direct keyword overlap with query
    assert results[0]["index"] == 0
    assert "relevance_score" in results[0]


def test_local_reranker_with_fallback_on_invalid_endpoint():
    # Point to a non-existent port to test graceful offline fallback
    reranker = LocalRerankerProvider(endpoint_url="http://127.0.0.1:59999/v1/rerank", timeout=1, enable_fallback=True)
    docs = ["Dokumen pertama tentang AI", "Dokumen kedua tentang seni"]
    results = reranker.rerank(query="AI", documents=docs, top_n=2)
    assert len(results) == 2
    assert results[0]["index"] == 0
