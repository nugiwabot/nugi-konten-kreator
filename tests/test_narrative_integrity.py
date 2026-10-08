"""Regression tests for evidence-aware narrative integrity gates."""

from engine.editorial.script_auditor import audit_narrative_integrity, audit_script_with_dossier


def test_disputed_claim_asserted_as_fact_is_a_hard_blocker():
    sentence = "Pembangunan jalan tol menyebabkan harga rumah di Bandung naik tajam."
    dossier = {
        "epistemic_status": "DISPUTED",
        "claims": [{"id": "c1", "text": sentence, "status": "DISPUTED"}],
    }

    report = audit_narrative_integrity(sentence, dossier, story_plan={})

    assert report["gate_status"] == "BLOCKED"
    assert any(item["code"] == "UNRESOLVED_CLAIM_ASSERTED_AS_FACT" for item in report["findings"])
    assert report["publication_approval"] is False


def test_probable_claim_with_cautious_qualifier_is_not_hard_blocked():
    sentence = "Bukti awal mengindikasikan harga rumah di Bandung cenderung naik."
    dossier = {
        "epistemic_status": "PROBABLE",
        "claims": [{
            "id": "c1",
            "text": "Harga rumah di Bandung cenderung naik berdasarkan bukti awal.",
            "status": "PROBABLE",
        }],
    }

    report = audit_narrative_integrity(sentence, dossier, story_plan=None)

    assert report["gate_status"] != "BLOCKED"
    assert not any(item["severity"] == "CRITICAL" for item in report["findings"])
    assert report["publication_approval"] is False


def test_unlinked_numerical_claim_is_flagged():
    dossier = {
        "epistemic_status": "VERIFIED",
        "claims": [{"id": "c1", "text": "Harga tanah berbeda antarwilayah.", "status": "VERIFIED"}],
        "data_points": [],
    }

    report = audit_narrative_integrity(
        "Data menunjukkan bahwa harga rumah mencapai 45 persen pada tahun 2025.",
        dossier,
    )

    assert any(item["code"] == "SCRIPT_NUMERIC_DETAIL_NOT_LINKED" for item in report["findings"])
    assert report["gate_status"] == "REVIEW_REQUIRED"


def test_discovery_only_source_cannot_be_used_as_supported_story_plan_claim():
    claim_text = "Laporan awal menyebut perubahan harga rumah di Bandung."
    dossier = {
        "epistemic_status": "VERIFIED",
        "claims": [{
            "id": "c1",
            "text": claim_text,
            "status": "VERIFIED",
            "supporting_evidence": [{"evidence_role": "DISCOVERY_ONLY", "title": "Search result"}],
        }],
    }
    plan = {
        "beats": [{
            "beat_id": "beat_01",
            "evidence_status": "SUPPORTED_CLAIM",
            "evidence_claims": [{"id": "c1", "text": claim_text, "status": "VERIFIED"}],
        }]
    }

    report = audit_narrative_integrity(claim_text, dossier, plan)

    assert report["gate_status"] == "BLOCKED"
    assert any(item["code"] == "DISCOVERY_ONLY_USED_AS_SUPPORT" for item in report["findings"])


def test_untraceable_direct_quote_is_flagged():
    dossier = {"epistemic_status": "VERIFIED", "claims": []}

    report = audit_narrative_integrity(
        'Pejabat itu mengatakan, "Harga rumah pasti naik tahun depan".',
        dossier,
    )

    assert any(item["code"] == "QUOTE_PROVENANCE_MISSING" for item in report["findings"])


def test_legacy_fact_check_input_still_returns_integrity_report():
    report = audit_script_with_dossier(
        "Belum ada sumber yang cukup untuk memastikan penyebabnya.",
        dossier_data={},
    )

    assert report["narrative_integrity"]["schema_version"] == 1
    assert report["narrative_integrity"]["publication_approval"] is False
    assert report["editorial_gate"]["publication_approval"] is False
