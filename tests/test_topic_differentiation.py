"""
tests/test_topic_differentiation.py
====================================
Verifies that DossierGenerator and DynamicScriptSynthesizer produce
TOPIC-SPECIFIC empirical conclusions and completely divergent scripts,
eliminating any hardcoded generic housing/KPR narratives.
"""

import pytest
from engine.pipeline.research_dossier import DossierGenerator
from engine.editorial.script_synthesizer import DynamicScriptSynthesizer


def test_three_topic_synthesis_differentiation():
    """
    Generate dossiers and scripts for 3 meaningfully distinct topics:
    1. Evergreen Housing / Economy
    2. Modern AI / Technology
    3. Historical / Indonesian Reformasi 1998
    
    Assert that findings, claims, causal mechanisms, angles, visuals,
    and scripts differ completely without cross-contamination.
    """
    gen = DossierGenerator()
    synth = DynamicScriptSynthesizer()

    topic_housing = "Krisis Keterjangkauan Rumah dan KPR Kaum Muda"
    topic_ai = "Otomatisasi Artificial Intelligence pada Industri Kreatif"
    topic_history = "Gerakan Reformasi 1998 dan Krisis Moneter Indonesia"

    # Quick depth for fast deterministic unit testing
    dossier_housing = gen.build_dossier(topic_housing, max_evidence_per_source=2, depth="quick")
    dossier_ai = gen.build_dossier(topic_ai, max_evidence_per_source=2, depth="quick")
    dossier_history = gen.build_dossier(topic_history, max_evidence_per_source=2, depth="quick")

    # 1. Assert Key Findings Differ
    assert dossier_housing.key_findings != dossier_ai.key_findings
    assert dossier_ai.key_findings != dossier_history.key_findings
    assert "Krisis Keterjangkauan Rumah" in " ".join(dossier_housing.key_findings)
    assert "Artificial Intelligence" in " ".join(dossier_ai.key_findings)

    # 2. Assert Entities Differ
    assert dossier_housing.entities != dossier_ai.entities
    # AI topic must NOT contain housing-specific terms unless topic explicitly mentions them
    housing_terms = ["kpr", "rumah", "jabodetabek", "susenas"]
    ai_entities_str = " ".join(dossier_ai.entities).lower()
    for term in housing_terms:
        assert term not in ai_entities_str, f"Found generic housing term '{term}' in AI entities!"

    # 3. Assert Causal Relationships Differ
    cause_housing = dossier_housing.causal_relationships[0]["cause"]
    cause_ai = dossier_ai.causal_relationships[0]["cause"]
    cause_history = dossier_history.causal_relationships[0]["cause"]
    assert cause_housing != cause_ai
    assert cause_ai != cause_history
    assert "Artificial Intelligence" in cause_ai or "ai" in cause_ai.lower() or "industri" in cause_ai.lower()

    # 4. Assert Narrative Angles Differ
    angle_housing = dossier_housing.narrative_angles[0]["revelation"]
    angle_ai = dossier_ai.narrative_angles[0]["revelation"]
    assert angle_housing != angle_ai

    # 5. Assert Visual Implications Differ
    vis_housing = " ".join(v["concept"] for v in dossier_housing.visual_implications)
    vis_ai = " ".join(v["concept"] for v in dossier_ai.visual_implications)
    vis_history = " ".join(v["concept"] for v in dossier_history.visual_implications)
    assert vis_housing != vis_ai
    assert vis_ai != vis_history
    # AI visual concepts should not search commuter/KPR maps
    assert "komuter jabodetabek" not in vis_ai.lower()
    assert "sertifikat tanah" not in vis_ai.lower()

    # 6. Assert Generated Scripts Differ Materially
    script_housing = synth.synthesize_script(dossier_housing)
    script_ai = synth.synthesize_script(dossier_ai)
    script_history = synth.synthesize_script(dossier_history)

    assert script_housing != script_ai
    assert script_ai != script_history
    assert "Artificial Intelligence" in script_ai or "industri kreatif" in script_ai.lower()
    assert "1998" in script_history or "reformasi" in script_history.lower()
    # Script AI must not have static housing ending
    assert "ruang bukan sekadar dinding dan atap" not in script_ai.lower()
