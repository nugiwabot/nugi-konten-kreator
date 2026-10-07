"""
Tests for Research Dossier Engine.
"""
import pytest
from pathlib import Path
from engine.pipeline.research_dossier import DossierGenerator, ResearchDossier


def test_dossier_generation_structure():
    gen = DossierGenerator()
    dossier = gen.build_dossier("kenapa harga tanah terus naik", max_evidence_per_source=2)
    
    assert isinstance(dossier, ResearchDossier)
    assert len(dossier.subquestions) >= 3
    assert len(dossier.key_findings) >= 2
    assert len(dossier.claims) >= 1
    assert len(dossier.causal_relationships) >= 1
    assert len(dossier.narrative_angles) >= 1
    assert len(dossier.visual_implications) >= 1
    assert dossier.epistemic_status in ("VERIFIED", "PROBABLE")

    md = dossier.to_markdown()
    assert "# RESEARCH DOSSIER:" in md
    assert "## 1. RESEARCH QUESTION" in md
    assert "## 4. CLAIMS & EVIDENCE MAPPING" in md
    assert "## 8. SOURCE PROVENANCE REGISTRY" in md


def test_dossier_save_to_workspace(tmp_path):
    gen = DossierGenerator()
    dossier = gen.build_dossier("urbanisasi dan komuter", max_evidence_per_source=1)
    files = gen.save_dossier_to_workspace(dossier, tmp_path)
    
    json_path = Path(files["json_path"])
    md_path = Path(files["md_path"])
    assert json_path.exists()
    assert md_path.exists()
    assert json_path.stat().st_size > 500
    assert md_path.stat().st_size > 500
