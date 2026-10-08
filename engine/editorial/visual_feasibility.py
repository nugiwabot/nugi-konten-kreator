"""
Stage 06: early visual feasibility assessment for scoped content candidates.

This is a planning heuristic, not a media search. It must never imply that
assets exist, have been verified, or are licensed for reuse.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from engine.pipeline.visual_requirements import (
    classify_visual_era,
    classify_visual_requirement,
)


def assess_visual_feasibility(topic: str, scope: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a conservative, explainable visual plan before script production."""
    raw = re.sub(r"\s+", " ", str(topic or "")).strip()
    lower = raw.lower()
    context = scope or {}

    if not raw:
        return {
            "status": "VISUALS_BLOCKED",
            "score": 0,
            "confidence": "LOW",
            "summary": "Belum ada topik untuk dinilai.",
            "visual_requirement": "UNKNOWN",
            "visual_type": "UNKNOWN",
            "visual_era": "unknown",
            "visual_routes": [],
            "risk_flags": ["topic_missing"],
            "asset_search_performed": False,
            "asset_availability_verified": False,
            "download_performed": False,
            "recommended_next_step": "Tentukan topik dan kasus konkret terlebih dahulu.",
        }

    visual_requirement, visual_type, entities, _, source_role = classify_visual_requirement(raw)
    era = classify_visual_era(raw)
    routes: List[Dict[str, Any]] = []

    def add(route_id: str, label: str, asset_types: List[str], rationale: str) -> None:
        if not any(item["id"] == route_id for item in routes):
            routes.append({
                "id": route_id,
                "label": label,
                "asset_types": asset_types,
                "rationale": rationale,
                "availability": "NOT_CHECKED",
                "rights_status": "NOT_CHECKED",
            })

    # Evidence-bearing routes are deliberately distinct from decorative B-roll.
    add(
        "documents_and_primary_records",
        "Dokumen dan sumber primer",
        ["official documents", "reports", "records", "archival documents"],
        "Dapat mendukung konteks dan klaim jika dokumen yang relevan benar-benar ditemukan.",
    )

    place_cues = re.search(
        r"\b(indonesia|jakarta|bandung|surabaya|yogyakarta|medan|bekasi|semarang|makassar|singapura|jepang|amerika|kota|desa|kawasan|perumahan|pelabuhan|stasiun|pasar)\b",
        lower,
    )
    historical_cues = re.search(
        r"\b(sejarah|historis|arsip|kolonial|perang|abad|zaman|prasejarah|dulu|194[0-9]|19[0-9]{2})\b",
        lower,
    )
    quantitative_cues = re.search(
        r"\b(harga|biaya|ekonomi|inflasi|gaji|upah|populasi|data|persen|persentase|meningkat|turun|naik|perubahan|statistik|permintaan|pasokan)\b|\b\d+(?:[.,]\d+)?\s*%",
        lower,
    )
    system_cues = re.search(
        r"\b(kenapa|mengapa|bagaimana|sistem|mekanisme|insentif|kebijakan|aturan|teknologi|ai|algoritma|transportasi|infrastruktur|pekerjaan|pasar)\b",
        lower,
    )
    has_scoped_case = (
        str(context.get("scoping_status", "")) == "READY_FOR_RESEARCH"
        or (
            bool(place_cues or re.search(r"\b(?:19|20)\d{2}\b", lower))
            and "belum ada kasus spesifik" not in str(context.get("concrete_case", "")).lower()
        )
    )

    if place_cues:
        add(
            "place_and_geography",
            "Lokasi, peta, dan geografi",
            ["location footage", "maps", "satellite or street-level imagery"],
            "Lokasi yang disebut dapat memberi visual spesifik setelah kecocokan tempat diverifikasi.",
        )
    if historical_cues or era == "historical":
        add(
            "historical_and_archival",
            "Arsip dan visual historis",
            ["archival photographs", "period footage", "contemporary records"],
            "Visual periode perlu dicocokkan dengan waktu, tempat, peristiwa, dan sumber asalnya.",
        )
    if quantitative_cues:
        add(
            "data_and_charts",
            "Data dan grafik",
            ["official datasets", "charts", "tables"],
            "Grafik baru layak dibuat setelah angka, definisi, rentang waktu, dan sumber datanya diverifikasi.",
        )
    if system_cues:
        add(
            "mechanism_explainer",
            "Diagram mekanisme",
            ["custom diagrams", "maps", "process graphics"],
            "Diagram dapat menjelaskan hubungan sebab-akibat sebagai penjelasan, bukan bukti visual langsung.",
        )
    add(
        "human_context",
        "Kehidupan sehari-hari dan konteks manusia",
        ["relevant documentary footage", "photographs", "objects and environments"],
        "Footage konteks dapat membantu menjelaskan dampak manusia, tetapi tidak membuktikan kejadian spesifik.",
    )

    risks: List[str] = []
    if not place_cues:
        risks.append("specific_location_not_identified")
    if historical_cues or era == "historical":
        risks.append("historical_authenticity_and_date_match_required")
    if quantitative_cues:
        risks.append("data_visuals_require_verified_underlying_data")
    if visual_requirement == "REAL_REQUIRED":
        risks.append("authentic_specific_visual_may_be_required")
    risks.append("rights_and_provenance_must_be_checked_before_reuse")

    if has_scoped_case and len(routes) >= 3:
        status, score = "VISUALS_FEASIBLE", 75
        summary = "Ada beberapa jalur visual yang masuk akal untuk ditelusuri; asetnya belum dicari atau diverifikasi."
        next_step = "Lanjutkan riset dan verifikasi kasus; pada tahap akuisisi, uji tiap jalur visual melalui MediaFinder."
    else:
        status, score = "VISUALS_PARTIAL", 45 if len(routes) >= 2 else 25
        summary = "Jalur visual awal tersedia, tetapi kasus atau batas visual masih perlu dipersempit sebelum produksi."
        next_step = "Perjelas lokasi, periode, objek, atau peristiwa spesifik; jangan menganggap rute visual sebagai aset yang tersedia."

    return {
        "status": status,
        "score": score,
        "confidence": "LOW",
        "summary": summary,
        "visual_requirement": visual_requirement,
        "visual_type": visual_type,
        "source_role": source_role,
        "entities": [str(item.get("name", "")) for item in entities if isinstance(item, dict)],
        "visual_era": era,
        "visual_routes": routes,
        "risk_flags": risks,
        "asset_search_performed": False,
        "asset_availability_verified": False,
        "download_performed": False,
        "recommended_next_step": next_step,
        "limitations": [
            "Penilaian ini berbasis heuristik topik dan scope, bukan hasil pencarian aset.",
            "Tidak ada aset yang dinyatakan tersedia, autentik, atau berlisensi hanya dari preflight ini.",
        ],
    }
