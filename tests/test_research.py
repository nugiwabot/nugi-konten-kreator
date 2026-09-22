import pytest
from engine.providers.search import classify_source_quality, WebResearchProvider
from engine.pipeline.research_runner import ResearchRunner


class MockSearchProvider(WebResearchProvider):
    """Mock provider for deterministic testing without external network."""
    
    def search(self, query: str, recency=None, domains=None, language="id-id", max_results=5):
        return [
            {
                "source": "bps.go.id",
                "title": "Data Statistik Perkembangan Perumahan Nasional",
                "date": "2026-03-01",
                "url": "https://www.bps.go.id/report/housing-2026",
                "content": "Pertumbuhan kepemilikan rumah generasi muda melambat 4.2% menurut data sensus resmi.",
                "publisher": "bps.go.id",
                "relevance": "HIGH",
                "source_tier": 1,
                "source_tier_name": "Primary Source / Official",
                "reliability": "HIGH"
            },
            {
                "source": "techcrunch.com",
                "title": "AI Startups Raising Record Capital for Real Estate Workflows",
                "date": "2026-03-10",
                "url": "https://techcrunch.com/ai-realestate",
                "content": "CEO startup mengklaim bahwa sistem agen otomatis memangkas waktu survei lahan hingga 70%.",
                "publisher": "techcrunch.com",
                "relevance": "HIGH",
                "source_tier": 5,
                "source_tier_name": "Industry Publication",
                "reliability": "MEDIUM_HIGH"
            }
        ]


def test_source_quality_tier_classification():
    t1 = classify_source_quality("https://arxiv.org/abs/2401.12345", "arxiv.org")
    assert t1["tier"] == 1
    assert t1["reliability"] == "HIGH"
    
    t4 = classify_source_quality("https://www.reuters.com/business/finance", "reuters.com")
    assert t4["tier"] == 4
    assert t4["reliability"] == "HIGH"

    t5 = classify_source_quality("https://www.inman.com/real-estate-trends", "inman.com")
    assert t5["tier"] == 5

    t7 = classify_source_quality("https://twitter.com/user/status/123", "twitter.com")
    assert t7["tier"] == 7
    assert t7["reliability"] == "LOW_NEEDS_VERIFICATION"


def test_research_runner_fact_and_claim_separation():
    mock = MockSearchProvider()
    runner = ResearchRunner(search_provider=mock)
    res = runner.run_research(topic="properti dan AI")
    
    assert res["total_sources_found"] == 2
    assert len(res["preliminary_facts"]) > 0
    assert len(res["preliminary_claims"]) > 0
    # Tier 1 source is in facts
    assert "bps.go.id" in res["preliminary_facts"][0]
    # Klaim keyword routed to claims
    assert "techcrunch.com" in res["preliminary_claims"][0]
