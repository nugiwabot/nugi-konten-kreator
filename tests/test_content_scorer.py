"""
tests/test_content_scorer.py
============================
Verifies 10-dimension ContentQualityEvaluator and status threshold classification.
"""

import pytest
from engine.editorial.content_scorer import ContentQualityEvaluator


def test_content_quality_evaluator_high_quality():
    """
    Validates that a complete dossier with verified facts and sound narrative
    scores high (PUBLISH_READY or MINOR_EDIT) with 10 present dimensions.
    """
    evaluator = ContentQualityEvaluator()
    dossier_data = {
        "primary_sources": [
            {"tier": "S1", "publisher": "BPS", "url": "https://bps.go.id"},
            {"tier": "S2", "publisher": "OpenAlex", "url": "https://openalex.org"}
        ],
        "evidence_items": [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}],
        "claims": [
            {"id": "c1", "text": "Claim 1", "supporting_evidence": [{"id": "1"}]},
            {"id": "c2", "text": "Claim 2", "supporting_evidence": [{"id": "2"}]}
        ],
        "narrative_angles": [
            {
                "title": "Angle 1",
                "human_dilemma": "Dilema masyarakat menghadapi inflasi biaya hidup harian."
            }
        ]
    }
    script_text = (
        "[00:00 - 00:08] HOOK\nPernahkah kamu menyadari pergeseran ini?\n"
        "[00:08 - 00:25] TENSION & PARADOX\nBanyak orang mengira ini sederhana, namun data BPS membuktikan sebaliknya.\n"
        "[00:25 - 00:45] CONTEXT & STRUCTURAL CAUSE\nPendorong utamanya adalah dinamika pasar yang mengubah kehidupan masyarakat.\n"
        "[00:45 - 00:60] THE REVELATION (THE WHY)\nIni tentang bagaimana kita mempertahankan ruang hidup masa depan."
    )
    fact_check_result = {
        "overall_verdict": "VERIFIED",
        "pass_gate": True,
        "breakdown": {"verified": 3, "probable": 1, "disputed": 0, "unverified": 0}
    }
    shots_data = [
        {"shot_id": "shot_1", "visual_requirement": "REAL_PREFERRED"},
        {"shot_id": "shot_2", "visual_requirement": "GENERIC_ALLOWED"}
    ]
    downloaded_assets = [{"local_path": "/path/to/asset.jpg"}]

    report = evaluator.evaluate(
        topic="Dinamika Pasar Properti",
        dossier_data=dossier_data,
        script_text=script_text,
        fact_check_result=fact_check_result,
        shots_data=shots_data,
        downloaded_assets=downloaded_assets,
    )

    assert report.overall_score >= 80
    assert report.status in ("PUBLISH_READY", "MINOR_EDIT")
    assert len(report.dimension_scores) == 10
    assert len(report.blockers) == 0


def test_content_quality_evaluator_disputed_overclaim():
    """
    Validates that disputed causal overclaims or clickbait trigger blockers
    and reduce overall score.
    """
    evaluator = ContentQualityEvaluator()
    dossier_data = {"claims": []}
    script_text = "Pasti cuan 100%! Ini adalah satu-satunya penyebab krisis ekonomi."
    fact_check_result = {
        "overall_verdict": "DISPUTED",
        "breakdown": {"disputed": 1}
    }

    report = evaluator.evaluate(
        topic="Investasi Bodong",
        dossier_data=dossier_data,
        script_text=script_text,
        fact_check_result=fact_check_result,
        shots_data=[],
        downloaded_assets=[],
    )

    assert len(report.blockers) > 0
    assert report.status in ("NEEDS_REVIEW", "REJECT_AND_RESEARCH_AGAIN")


def test_unverified_fact_check_cannot_receive_publish_ready_label():
    report = ContentQualityEvaluator().evaluate(
        topic="Topik uji",
        dossier_data={"claims": [], "primary_sources": [], "evidence_items": []},
        script_text="Naskah dengan struktur yang perlu diperiksa.",
        fact_check_result={"overall_verdict": "UNVERIFIED", "pass_gate": False, "breakdown": {"unverified": 1}},
        shots_data=[],
        downloaded_assets=[],
    )

    assert report.status not in {"PUBLISH_READY", "MINOR_EDIT"}
    assert any("publish gate" in blocker.lower() for blocker in report.blockers)
