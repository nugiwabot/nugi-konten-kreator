import pytest
from engine.pipeline.retriever import KnowledgeRetriever
from engine.providers.embedding import FallbackEmbeddingProvider
from engine.providers.reranker import FallbackRerankerProvider


def test_retriever_initialization():
    retriever = KnowledgeRetriever()
    assert retriever.total_chunks > 0


def test_retriever_query_execution():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("prinsip kelangkaan dan rasa takut kehilangan", top_k_candidates=10, top_k_reranked=3)
    assert len(results) > 0
    assert "concept" in results[0]
    assert "text" in results[0]
    assert "rerank_score" in results[0]


def test_retriever_fallback_on_offline_providers():
    # Test retriever functioning with full fallback providers
    offline_emb = FallbackEmbeddingProvider(dim=128)
    offline_rerank = FallbackRerankerProvider()
    retriever = KnowledgeRetriever(embedding_provider=offline_emb, reranker_provider=offline_rerank)
    
    results = retriever.retrieve("kenapa ide bisa viral", top_k_candidates=5, top_k_reranked=2)
    assert len(results) <= 2
    for r in results:
        assert "text" in r


def test_retriever_empty_query():
    retriever = KnowledgeRetriever()
    results = retriever.retrieve("", top_k_candidates=5, top_k_reranked=2)
    # Empty query gracefully handled without exceptions
    assert isinstance(results, list)
