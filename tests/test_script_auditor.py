"""
tests/test_script_auditor.py
============================
Unit tests for Python Script Fact & Narrative Verification Engine (script_auditor.py).
Covers all 10 mandatory verification and epistemic checks.
"""

import pytest
from engine.editorial.script_auditor import (
    ScriptAuditor,
    EvidenceResolver,
    EvidenceItem,
    ExtractedClaim,
    ClaimType,
    VerificationStatus,
    Severity,
    OverallStatus,
    extract_claims_from_text
)


# =============================================================================
# TEST 1 — Supported fact (Evidence kuat langsung mendukung klaim)
# =============================================================================
def test_1_supported_fact():
    auditor = ScriptAuditor()
    script = "Penelitian Daniel Kahneman membuktikan bahwa subjek menuntut harga dua kali lipat untuk melepaskan barang miliknya."
    evidence = [
        EvidenceItem(
            source="Kahneman, Knetsch, & Thaler (1990)",
            source_tier=1,
            source_tier_name="Academic / Primary",
            reliability="HIGH",
            content="Eksperimen klasik Kahneman membuktikan subjek menuntut kompensasi 2x lipat lebih tinggi untuk melepaskan mug miliknya."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status in [VerificationStatus.VERIFIED, VerificationStatus.SUPPORTED]
    assert target.severity == Severity.LOW
    assert report.overall_status == OverallStatus.PASS


# =============================================================================
# TEST 2 — No evidence (Claim faktual tanpa source)
# =============================================================================
def test_2_no_evidence():
    auditor = ScriptAuditor()
    script = "Sebuah asteroid misterius pernah menghantam perumahan di Jakarta pada tahun 1720."
    report = auditor.audit_script(script, provided_evidence=[])
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.UNVERIFIED
    # UNVERIFIED != FALSE/CONTRADICTED
    assert target.status != VerificationStatus.CONTRADICTED
    assert "UNVERIFIED" in target.reason or "Belum ditemukan data" in target.reason


# =============================================================================
# TEST 3 — Correlation -> Causation (Causal Overclaim)
# =============================================================================
def test_3_correlation_to_causation():
    auditor = ScriptAuditor()
    script = "Penggunaan media sosial menyebabkan kenaikan harga rumah di perkotaan."
    evidence = [
        EvidenceItem(
            source="Urban Studies Journal",
            source_tier=1,
            content="Studi menemukan adanya korelasi dan asosiasi statistik antara penggunaan media sosial dan persepsi harga rumah di perkotaan."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.PARTIALLY_SUPPORTED
    assert "CAUSAL_OVERCLAIM" in target.issues
    assert "korelasi" in target.recommendation.lower()


# =============================================================================
# TEST 4 — Scope Mismatch (Source Jakarta -> Script Orang Indonesia)
# =============================================================================
def test_4_scope_mismatch():
    auditor = ScriptAuditor()
    script = "Orang Indonesia menghabiskan 4 jam sehari di jalanan karena macet."
    evidence = [
        EvidenceItem(
            source="Survei Komuter 2024",
            source_tier=4,
            content="Hasil survei terhadap 1.000 warga Jakarta menunjukkan waktu tempuh komuter mencapai 4 jam sehari di jalanan."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.NEEDS_CONTEXT
    assert "SCOPE_MISMATCH" in target.issues
    assert "jakarta" in target.recommendation.lower()


# =============================================================================
# TEST 5 — Temporal Mismatch (Source 2018 -> Script "Saat ini")
# =============================================================================
def test_5_temporal_mismatch():
    auditor = ScriptAuditor()
    script = "Saat ini ada 15 juta rumah tangga yang belum memiliki tempat tinggal layak."
    evidence = [
        EvidenceItem(
            source="BPS Sensus 2018",
            source_tier=1,
            year=2018,
            content="Berdasarkan data sensus BPS tahun 2018, terdapat 15 juta rumah tangga belum memiliki hunian."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.NEEDS_CONTEXT
    assert "TEMPORAL_MISMATCH" in target.issues


# =============================================================================
# TEST 6 — Numerical Mismatch (Source 21% -> Script 30%)
# =============================================================================
def test_6_numerical_mismatch():
    auditor = ScriptAuditor()
    script = "Tingkat kekosongan apartemen di pusat kota telah melonjak mencapai 30%."
    evidence = [
        EvidenceItem(
            source="Laporan Riset Properti Kuartal 4",
            source_tier=4,
            content="Tingkat kekosongan apartemen di pusat kota tercatat sebesar 21%."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.CONTRADICTED
    assert "NUMERICAL_MISMATCH" in target.issues
    assert target.severity == Severity.CRITICAL
    assert report.overall_status == OverallStatus.BLOCK


# =============================================================================
# TEST 7 — Opinion / Subjective Expression
# =============================================================================
def test_7_opinion_handling():
    auditor = ScriptAuditor()
    script = "Menurut saya, rumah modern dengan dinding kaca terasa lebih dingin dan kurang bersahabat."
    report = auditor.audit_script(script, provided_evidence=[])
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.type == ClaimType.OPINION
    assert target.status == VerificationStatus.OPINION
    assert target.severity == Severity.LOW


# =============================================================================
# TEST 8 — Conflicting Sources (Dua sumber kredibel bertentangan)
# =============================================================================
def test_8_conflicting_sources():
    auditor = ScriptAuditor()
    script = "Harga tanah di pinggiran kota mengalami pergerakan drastis tahun ini."
    evidence = [
        EvidenceItem(
            source="Bank Indonesia SHPR",
            source_tier=1,
            content="Indeks harga tanah dan properti residensial menunjukkan tren meningkat pesat sebesar 8%."
        ),
        EvidenceItem(
            source="Lembaga Riset Properti Nasional",
            source_tier=4,
            content="Transaksi dan harga tanah di kawasan penyangga mengalami penurunan signifikan sebesar 5%."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.CONFLICTING_EVIDENCE
    assert "CONFLICTING_EVIDENCE" in target.issues


# =============================================================================
# TEST 9 — Overclaim (Generalisasi absolut "semua" / "selalu")
# =============================================================================
def test_9_overclaim_detection():
    auditor = ScriptAuditor()
    script = "Semua orang pasti mengalami insomnia jika tidur di dekat lampu."
    evidence = [
        EvidenceItem(
            source="Journal of Sleep Research",
            source_tier=1,
            content="Studi menemukan bahwa paparan cahaya malam menekan melatonin pada sebagian besar orang (sekitar 65% responden)."
        )
    ]
    report = auditor.audit_script(script, provided_evidence=evidence)
    assert len(report.claims) >= 1
    target = report.claims[0]
    assert target.status == VerificationStatus.PARTIALLY_SUPPORTED
    assert "OVERCLAIM" in target.issues


# =============================================================================
# TEST 10 — Existing Research Integration & Extraction Diversity
# =============================================================================
def test_10_existing_research_integration():
    from engine.providers.search import classify_source_quality
    from engine.pipeline.research_runner import ResearchRunner

    # Verify existing source classification reuse
    tier = classify_source_quality("https://www.bi.go.id/shpr", "bank indonesia")
    assert tier["tier"] == 1

    ev_item = EvidenceItem.from_dict({
        "url": "https://www.bps.go.id",
        "publisher": "Badan Pusat Statistik",
        "content": "Backlog perumahan mencapai 9,9 juta unit rumah tangga."
    })
    assert ev_item.source_tier == 1
    assert ev_item.reliability == "HIGH"

    # Multi-type claim extraction test
    multi_script = """
    ### 🪝 HOOK
    Tahun 1931, Harry Beck merancang peta kereta pertama.
    ### 📖 BODY
    Kadar CO2 melonjak 2 kali lipat dalam kamar tertutup.
    Harga tanah naik jauh lebih cepat daripada upah pekerja.
    AI membutuhkan jutaan liter air untuk mendinginkan server.
    ### 💡 REVELATION
    Menurut saya, rumah adalah benteng pertahanan terakhir.
    """
    claims = extract_claims_from_text(multi_script)
    types_found = {c.claim_type for c in claims}
    assert ClaimType.QUANTITATIVE in types_found or ClaimType.HISTORICAL in types_found
    assert ClaimType.OPINION in types_found


# =============================================================================
# TEST 11 — Nugi Property Brand Fit (Core, Strong Lens, and Tacked-on Detection)
# =============================================================================
def test_11_nugi_property_brand_fit():
    from engine.editorial.script_auditor import evaluate_nugi_property_brand_fit

    # Case A: Core Property Script (KPR 20 tahun & agunan tanah)
    core_script = """
    Kenapa bank berani memberi pinjaman KPR hingga 20 tahun untuk sebuah rumah?
    Jawabannya ada pada agunan tanah fisik yang tidak bisa dipindahkan.
    Nilai tanah cenderung bertahan, cicilan diamortisasi secara ketat, dan bank memegang sertifikat hak milik.
    Yang dibiayai bank sebenarnya bukan sekadar bangunan bata, melainkan kepemilikan tapak tanah permanen.
    """
    fit_core = evaluate_nugi_property_brand_fit(core_script, title="Kenapa Bank Berani Utang KPR 20 Tahun?")
    assert fit_core["score"] >= 17
    assert fit_core["tier"] == "CORE PROPERTY"
    assert fit_core["status"] == "PASS"
    assert not fit_core["tacked_on_warning"]

    # Case B: Strong Property Lens (AI remote work altering home workspace)
    lens_script = """
    Kalau kecerdasan buatan memungkinkan kita bekerja dari mana saja, kenapa rumah kita malah makin mirip kantor?
    Setiap sudut kamar tidur dan ruang keluarga sekarang terpaksa disesuaikan menjadi meja kerja darurat.
    Denah rumah modern kehilangan sekat privasi karena batas tempat istirahat dan jam kerja lebur.
    AI tidak membebaskan kita dari ruang fisik, tapi diam-diam merampas ruang santai di dalam rumah kita sendiri.
    """
    fit_lens = evaluate_nugi_property_brand_fit(lens_script, title="Kenapa Rumah Kita Malah Makin Mirip Kantor?")
    assert fit_lens["score"] >= 13
    assert fit_lens["tier"] in ["CORE PROPERTY", "STRONG PROPERTY LENS"]
    assert fit_lens["status"] == "PASS"

    # Case C: Tacked-on Property Closing (Generic clock topic with 'rumah' forced at the end)
    tacked_script = """
    Kenapa jarum jam selalu berputar ke arah kanan?
    Ini bermula dari jam matahari peradaban kuno di belahan bumi utara.
    Ketika bayangan tiang gnomon bergerak dari barat melintasi utara ke timur, gerakannya melingkar ke kanan.
    Tradisi mekanik ribuan tahun lalu itu tetap bertahan sampai jam tangan modern hari ini.
    Dan waktu yang berputar itulah yang akhirnya membawa manusia pulang ke rumah.
    """
    fit_tacked = evaluate_nugi_property_brand_fit(tacked_script, title="Kenapa Jarum Jam Berputar ke Kanan?")
    assert fit_tacked["score"] <= 4
    assert fit_tacked["tier"] == "OFF BRAND"
    assert fit_tacked["status"] == "REVISE_OR_REPLACE"
    assert fit_tacked["tacked_on_warning"] is True

    # Case D: Integration in ScriptAuditor report
    auditor = ScriptAuditor()
    rep = auditor.audit_script(core_script, editorial_context={"title": "KPR 20 Tahun"})
    assert rep.property_brand_fit is not None
    assert rep.property_brand_fit["score"] >= 17

