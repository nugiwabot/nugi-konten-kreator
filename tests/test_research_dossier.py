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


def test_recency_reaches_primary_and_contradiction_web_searches():
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
        web_provider=web,
    )
    dossier = generator.build_dossier("urbanisasi", depth="deep", recency="w")

    assert dossier.epistemic_status == "UNVERIFIED"
    assert web.recencies == ["w", "w"]


def test_script_does_not_assert_data_or_causality_without_research(research_offline):
    dossier = DossierGenerator().build_dossier("transportasi publik Jakarta", depth="quick")
    script = DynamicScriptSynthesizer().synthesize_script(dossier, target_duration_seconds=30)

    assert "Belum ada bukti yang cukup" in script
    assert "data menunjukkan sebaliknya" not in script.lower()
    assert "pendorong utamanya adalah" not in script.lower()
