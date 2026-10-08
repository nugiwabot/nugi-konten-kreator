"""
Tests for Research Dossier Engine.
"""
import pytest
from pathlib import Path
from engine.pipeline.research_dossier import DossierGenerator, ResearchDossier
from engine.editorial.script_synthesizer import DynamicScriptSynthesizer


def test_dossier_generation_structure(research_offline):
    gen = DossierGenerator()
    dossier = gen.build_dossier("kenapa harga tanah terus naik", max_evidence_per_source=2)
    
    assert isinstance(dossier, ResearchDossier)
    assert len(dossier.subquestions) >= 3
    assert dossier.key_findings == ["Tidak ada bukti yang dapat diverifikasi berhasil diambil pada sesi riset ini."]
    assert dossier.claims == []
    assert len(dossier.causal_relationships) >= 1
    assert len(dossier.narrative_angles) >= 1
    assert len(dossier.visual_implications) >= 1
    assert dossier.epistemic_status == "UNVERIFIED"
    assert dossier.evidence_strength == 0.0

    md = dossier.to_markdown()
    assert "# RESEARCH DOSSIER:" in md
    assert "## 1. RESEARCH QUESTION" in md
    assert "## 4. CLAIMS & EVIDENCE MAPPING" in md
    assert "## 8. SOURCE PROVENANCE REGISTRY" in md


def test_dossier_save_to_workspace(tmp_path, research_offline):
    gen = DossierGenerator()
    dossier = gen.build_dossier("urbanisasi dan komuter", max_evidence_per_source=1)
    files = gen.save_dossier_to_workspace(dossier, tmp_path)
    
    json_path = Path(files["json_path"])
    md_path = Path(files["md_path"])
    assert json_path.exists()
    assert md_path.exists()
    assert json_path.stat().st_size > 500
    assert md_path.stat().st_size > 500


def test_recency_reaches_primary_and_contradiction_web_searches(monkeypatch):
    import engine.pipeline.research_dossier as dossier_module
    monkeypatch.setattr(dossier_module, "RSS_DISCOVERY_ENABLED", False)
    class EmptyProvider:
        def search_evidence(self, query, max_results=5):
            return []

    class RecencySpy:
        def __init__(self):
            self.recencies = []

        def search(self, query, recency=None, max_results=5):
            self.recencies.append(recency)
            return []

    web = RecencySpy()
    generator = DossierGenerator(
        bps_provider=EmptyProvider(),
        openalex_provider=EmptyProvider(),
        crossref_provider=EmptyProvider(),
        gdelt_provider=EmptyProvider(),
        pubmed_provider=EmptyProvider(),
        europe_pmc_provider=EmptyProvider(),
        web_provider=web,
    )
    dossier = generator.build_dossier("urbanisasi", depth="deep", recency="w")

    assert dossier.epistemic_status == "UNVERIFIED"
    assert web.recencies == ["w", "w"]


def test_rss_leads_are_serialized_separately_from_dossier_evidence(monkeypatch):
    from engine.intelligence.rss import FeedItem
    import engine.pipeline.research_dossier as dossier_module

    class EmptyProvider:
        def search_evidence(self, query, max_results=5):
            return []

    class EmptyWeb:
        def search(self, query, recency=None, max_results=5):
            return []

    feed_item = FeedItem(
        source_id="wire",
        source_name="Wire",
        feed_url="https://news.example/rss",
        title="Jakarta flood response expands",
        canonical_url="https://news.example/story",
    )

    class RSS:
        def discover(self, query, max_items=25):
            return [feed_item]

    monkeypatch.setattr(dossier_module, "RSS_DISCOVERY_ENABLED", True)
    monkeypatch.setattr(dossier_module, "RSSDiscoveryService", RSS)
    generator = DossierGenerator(
        bps_provider=EmptyProvider(),
        openalex_provider=EmptyProvider(),
        crossref_provider=EmptyProvider(),
        gdelt_provider=EmptyProvider(),
        pubmed_provider=EmptyProvider(),
        europe_pmc_provider=EmptyProvider(),
        web_provider=EmptyWeb(),
    )
    dossier = generator.build_dossier("Jakarta flood response", depth="quick")
    restored = ResearchDossier.from_dict(dossier.to_dict())

    assert restored.research_intelligence["rss_discoveries"][0]["title"] == feed_item.title
    assert restored.research_intelligence["evidence_status"] == "DISCOVERY_ONLY"
    assert restored.evidence_items == []
    assert "RSS DISCOVERY LEADS (NOT VERIFIED EVIDENCE)" in restored.to_markdown()


def test_web_search_snippets_are_separate_discovery_leads(monkeypatch):
    import engine.pipeline.research_dossier as dossier_module
    monkeypatch.setattr(dossier_module, "RSS_DISCOVERY_ENABLED", False)
    class EmptyProvider:
        def search_evidence(self, query, max_results=5):
            return []

    class SearchLeadWeb:
        def search(self, query, recency=None, max_results=5):
            return [{"title": "Jakarta transit report", "url": "https://example.org/report",
                     "publisher": "Example", "content": "A search snippet about Jakarta public transit."}]

    generator = DossierGenerator(
        bps_provider=EmptyProvider(), openalex_provider=EmptyProvider(),
        crossref_provider=EmptyProvider(), gdelt_provider=EmptyProvider(),
        pubmed_provider=EmptyProvider(), europe_pmc_provider=EmptyProvider(), web_provider=SearchLeadWeb(),
    )
    dossier = generator.build_dossier("Jakarta public transit", depth="quick")
    assert dossier.evidence_items == []
    assert dossier.claims == []
    assert dossier.research_intelligence["web_discoveries"][0]["evidence_status"] == "DISCOVERY_ONLY"
    assert "NOT CLAIM EVIDENCE" in dossier.to_markdown()


def test_rss_escalation_queries_trigger_structured_research_providers(monkeypatch):
    from engine.intelligence.rss import FeedItem
    import engine.pipeline.research_dossier as dossier_module

    class EmptyProvider:
        def search_evidence(self, query, max_results=5):
            return []

    class SearchSpy(EmptyProvider):
        def __init__(self):
            self.queries = []

        def search_evidence(self, query, max_results=5):
            self.queries.append(query)
            return []

    class EmptyWeb:
        def search(self, query, recency=None, max_results=5):
            return []

    feed_item = FeedItem(
        source_id="wire", source_name="Wire", feed_url="https://wire.example/rss",
        title="Jakarta earthquake relief report", canonical_url="https://wire.example/story",
    )

    class RSS:
        def discover(self, query, max_items=25):
            return [feed_item]

    monkeypatch.setattr(dossier_module, "RSS_DISCOVERY_ENABLED", True)
    monkeypatch.setattr(dossier_module, "RSSDiscoveryService", RSS)
    pubmed, europe = SearchSpy(), SearchSpy()
    generator = DossierGenerator(
        bps_provider=EmptyProvider(), openalex_provider=EmptyProvider(), crossref_provider=EmptyProvider(),
        gdelt_provider=EmptyProvider(), pubmed_provider=pubmed, europe_pmc_provider=europe, web_provider=EmptyWeb(),
    )
    dossier = generator.build_dossier("Jakarta earthquake", depth="quick")
    assert any("Jakarta earthquake relief report" in query for query in pubmed.queries[1:])
    assert any("Jakarta earthquake relief report" in query for query in europe.queries[1:])
    assert dossier.evidence_items == []


def test_dossier_reports_evidence_gaps_and_not_publication_approval(research_offline):
    dossier = DossierGenerator().build_dossier("kenapa harga tanah terus naik", depth="quick")
    assert dossier.research_readiness["status"] == "INSUFFICIENT_EVIDENCE"
    assert dossier.research_readiness["is_publication_approval"] is False
    assert dossier.research_readiness["verified_claims"] == 0
    assert any("Belum ada klaim" in gap["gap"] for gap in dossier.evidence_gaps)
    assert any("sumber primer" in gap["gap"].lower() for gap in dossier.evidence_gaps)
    assert any("mode quick" in gap["gap"].lower() for gap in dossier.evidence_gaps)
    assert "RESEARCH READINESS & EVIDENCE GAPS" in dossier.to_markdown()


def test_evidence_gap_report_excludes_discovery_leads_from_support_counts():
    from engine.pipeline.research_dossier import _build_evidence_gap_report
    from engine.providers.evidence_model import EvidenceItem, Source, SourceTier, SourceType
    lead = EvidenceItem(
        id="lead", claim_text="Headline only",
        source=Source(
            url="https://example.com/lead", publisher="Example",
            tier=SourceTier.S1, source_type=SourceType.GOVERNMENT,
            metadata={"evidence_role": "DISCOVERY_ONLY"},
        ),
        retrieved_snippet="Search snippet, not verified source text", is_supporting=True,
    )
    report = _build_evidence_gap_report([], [lead], [], 1, "deep")
    assert report["research_readiness"]["supporting_evidence_count"] == 0
    assert report["research_readiness"]["primary_source_count"] == 0
    assert report["research_readiness"]["discovery_leads_excluded"] == 1
    assert report["research_readiness"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_dossier_readiness_and_claim_coverage_survive_serialization(research_offline):
    dossier = DossierGenerator().build_dossier("urbanisasi dan komuter", depth="quick")
    restored = ResearchDossier.from_dict(dossier.to_dict())
    assert restored.research_readiness == dossier.research_readiness
    assert restored.evidence_gaps == dossier.evidence_gaps
    assert restored.claim_coverage == dossier.claim_coverage


def test_script_does_not_assert_data_or_causality_without_research(research_offline):
    dossier = DossierGenerator().build_dossier("transportasi publik Jakarta", depth="quick")
    script = DynamicScriptSynthesizer().synthesize_script(dossier, target_duration_seconds=30)

    assert "Belum ada bukti yang cukup" in script
    assert "data menunjukkan sebaliknya" not in script.lower()
    assert "pendorong utamanya adalah" not in script.lower()
