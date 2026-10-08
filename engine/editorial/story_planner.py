"""
Evidence-aware story planning for the canonical production pipeline.

The planner creates a narrative outline from the existing research dossier and
story-type engine. It does not add research, validate claims, or invent evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List

from engine.editorial.story_type import get_script_structure


SUPPORTED_STATUSES = {"VERIFIED", "PROBABLE"}


def _claim_value(claim: Any, name: str, default: Any = "") -> Any:
    if isinstance(claim, dict):
        return claim.get(name, default)
    return getattr(claim, name, default)


def build_story_plan(
    dossier: Any,
    story_type_info: Dict[str, Any],
    duration_seconds: float = 60,
    visual_preflight: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a structured, auditable story plan using only dossier-backed claims."""
    topic = str(getattr(dossier, "topic", "") or "")
    research_question = str(getattr(dossier, "research_question", "") or "").strip()
    claims = list(getattr(dossier, "claims", []) or [])
    angles = list(getattr(dossier, "narrative_angles", []) or [])
    causal_relationships = list(getattr(dossier, "causal_relationships", []) or [])
    evidence_gaps = list(getattr(dossier, "evidence_gaps", []) or [])
    epistemic_status = str(getattr(dossier, "epistemic_status", "UNVERIFIED") or "UNVERIFIED").upper()
    strength = float(getattr(dossier, "evidence_strength", 0.0) or 0.0)

    story_type = str(story_type_info.get("primary_type", "hidden_system") or "hidden_system")
    format_mode = "short" if float(duration_seconds or 60) <= 120 else "long"
    structure = get_script_structure(story_type, format_mode=format_mode)
    safe_claims = [
        claim for claim in claims
        if str(_claim_value(claim, "status", "UNVERIFIED")).upper() in SUPPORTED_STATUSES
    ]
    unresolved_claims = [
        claim for claim in claims
        if str(_claim_value(claim, "status", "UNVERIFIED")).upper() not in SUPPORTED_STATUSES
    ]

    def claim_ref(claim: Any) -> Dict[str, Any]:
        return {
            "id": str(_claim_value(claim, "id", "")),
            "text": str(_claim_value(claim, "text", "")),
            "status": str(_claim_value(claim, "status", "UNVERIFIED")).upper(),
            "confidence_score": float(_claim_value(claim, "confidence_score", 0.0) or 0.0),
            "independent_sources_count": int(_claim_value(claim, "independent_sources_count", 0) or 0),
        }

    verified_refs = [claim_ref(c) for c in safe_claims if str(_claim_value(c, "text", "")).strip()]
    unresolved_refs = [claim_ref(c) for c in unresolved_claims if str(_claim_value(c, "text", "")).strip()]
    angle = angles[0] if angles and isinstance(angles[0], dict) else {}
    central_question = research_question or f"Apa yang dapat dibuktikan tentang {topic}?"
    human_question = str(angle.get("human_dilemma", "") or "").strip()
    if not human_question:
        human_question = "Siapa yang terdampak oleh fenomena ini, dan dalam keputusan sehari-hari apa dampaknya terlihat?"

    beats: List[Dict[str, Any]] = []
    used_claim_ids = set()
    for index, raw_stage in enumerate(structure.get("stages", []), start=1):
        stage_name, _, stage_purpose = str(raw_stage).partition(" — ")
        label = stage_name.strip() or f"BEAT_{index}"
        lower = label.lower()
        refs: List[Dict[str, Any]] = []
        narration_seed = ""
        requires_evidence = any(word in lower for word in (
            "evidence", "cause", "mechanism", "timeline", "historical", "reality",
            "transformation", "effect", "consequence", "data", "state", "forces"
        ))

        if any(word in lower for word in ("hook", "observation", "assumption", "question", "condition", "situation")):
            narration_seed = central_question
        elif any(word in lower for word in ("evidence", "reality", "context", "timeline", "state", "surface", "before")):
            next_claim = next((c for c in verified_refs if c["id"] not in used_claim_ids), None)
            if next_claim:
                refs = [next_claim]
                used_claim_ids.add(next_claim["id"])
                narration_seed = next_claim["text"]
            elif unresolved_refs:
                refs = [unresolved_refs[0]]
                narration_seed = (
                    f"Klaim yang belum terverifikasi: {unresolved_refs[0]['text']} "
                    "Klaim ini belum boleh disampaikan sebagai fakta."
                )
            else:
                narration_seed = "Bukti spesifik untuk bagian ini belum tersedia dalam dossier."
        elif any(word in lower for word in ("cause", "mechanism", "forces", "why", "structural")):
            verified_cause = next(
                (item for item in causal_relationships if isinstance(item, dict)
                 and item.get("cause") and item.get("mechanism")
                 and epistemic_status == "VERIFIED" and verified_refs),
                None,
            )
            if verified_cause:
                narration_seed = (
                    f"Dossier mengidentifikasi {verified_cause['cause']} sebagai faktor yang perlu dijelaskan, "
                    f"melalui mekanisme: {verified_cause['mechanism']}."
                )
            else:
                narration_seed = (
                    "Mekanisme sebab-akibat belum cukup terkonfirmasi. Sajikan sebagai pertanyaan riset, "
                    "bukan sebagai kesimpulan."
                )
        elif any(word in lower for word in ("human", "consequence", "trade-off", "choice", "reflection")):
            narration_seed = f"Pertanyaan dampak manusia: {human_question}"
        elif any(word in lower for word in ("revelation", "alternative", "deeper", "future", "scenario")):
            if verified_refs:
                narration_seed = (
                    "Sintesis sementara harus dibatasi pada temuan yang didukung: "
                    + "; ".join(ref["text"] for ref in verified_refs[:2])
                )
            else:
                narration_seed = (
                    "Belum ada dasar yang cukup untuk menyatakan satu jawaban final. "
                    "Jelaskan apa yang diketahui, apa yang belum diketahui, dan bukti apa yang dibutuhkan."
                )
        else:
            narration_seed = stage_purpose or "Kembangkan beat ini tanpa menambah klaim di luar dossier."

        beats.append({
            "beat_id": f"beat_{index:02d}",
            "stage": label,
            "purpose": stage_purpose or label,
            "narration_seed": narration_seed,
            "evidence_claims": refs,
            "requires_evidence": requires_evidence,
            "evidence_status": "SUPPORTED_CLAIM" if refs and all(r["status"] in SUPPORTED_STATUSES for r in refs) else "GAP_OR_QUESTION",
            "visual_direction": "Pilih visual spesifik hanya jika relevan dengan beat; verifikasi aset pada tahap visual/media.",
        })

    return {
        "schema_version": 1,
        "topic": topic,
        "central_question": central_question,
        "story_type": structure.get("story_type", story_type),
        "story_type_name": structure.get("story_type_name", story_type),
        "narrative_device": structure.get("narrative_device", story_type_info.get("narrative_device", "")),
        "format_mode": format_mode,
        "duration_seconds": float(duration_seconds or 60),
        "epistemic_status": epistemic_status,
        "evidence_strength_heuristic": strength,
        "evidence_summary": {
            "total_claims": len(claims),
            "supported_claims_used": len(verified_refs),
            "unresolved_claims": len(unresolved_refs),
            "evidence_gaps": evidence_gaps[:20],
            "publication_approval": False,
        },
        "human_relevance_prompt": human_question,
        "beats": beats,
        "visual_preflight": visual_preflight or {"status": "NOT_PROVIDED", "asset_availability_verified": False},
        "script_guardrails": [
            "Jangan menyatakan klaim PROBABLE atau VERIFIED sebagai kepastian mutlak; pertahankan konteks dan batas sumber.",
            "Jangan ubah klaim UNVERIFIED, DISPUTED, atau kontradiktif menjadi fakta narasi.",
            "Jangan mengarang statistik, sumber, kutipan, peristiwa, tokoh, atau visual yang belum diverifikasi.",
            "Jika bukti tidak cukup, jadikan celah bukti sebagai batas atau pertanyaan cerita.",
            "Jangan memaksakan konflik/kontradiksi bila story type tidak memerlukannya.",
        ],
    }
