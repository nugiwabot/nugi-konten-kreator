"""
Nugi Content Discovery Engine.

Ranks content opportunities using the existing RSS, taxonomy, story-type and
editorial-fit layers. Discovery results remain leads until deep research verifies
their claims.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from engine.editorial.fit_score import calculate_editorial_fit
from engine.editorial.story_type import classify_story_type
from engine.editorial.taxonomy import classify_topic
from engine.intelligence.rss import RSSDiscoveryService


DEFAULT_DISCOVERY_QUERIES: Tuple[str, ...] = (
    "rumah properti tanah kota Indonesia",
    "urbanisasi transportasi kota Indonesia",
    "AI pekerjaan kota Indonesia",
    "sejarah kota Indonesia",
    "perubahan ruang hidup manusia Indonesia",
)

EVERGREEN_SEEDS: Tuple[str, ...] = (
    "Kenapa rumah yang lebih murah sering meminta kita membayar dengan waktu?",
    "Kenapa kota besar terus tumbuh meski hidup di dalamnya terasa semakin mahal?",
    "Bagaimana pekerjaan mengubah bentuk kota dan rumah tempat manusia tinggal?",
    "Kenapa manusia selalu mengubah tempat tinggalnya ketika teknologi berubah?",
    "Mengapa harga tanah bisa mengubah bentuk kota lebih jauh daripada arsitektur?",
)


@dataclass
class ContentOpportunity:
    suggested_title: str
    source_headline: str = ""
    source_url: str = ""
    source_names: List[str] = field(default_factory=list)
    source_count: int = 0
    published_at: str = ""
    primary_domain: str = ""
    anchor: str = ""
    lens: str = ""
    research_mode: str = ""
    story_type: str = ""
    human_question: str = ""
    deeper_why: str = ""
    editorial_fit_score: float = 0.0
    niche_fit_score: float = 0.0
    niche_decision: str = "NEEDS_SCOPING"
    niche_fit_reason: str = ""
    opportunity_score: float = 0.0
    novelty_score: float = 0.0
    evidence_signal: float = 0.0
    nugi_fit_score: float = 0.0
    recency_score: float = 0.0
    visual_potential_score: float = 0.0
    evidence_strength: float = 0.0
    research_claims_count: int = 0
    research_primary_sources_count: int = 0
    research_status: str = "NOT_RESEARCHED"
    research_findings: List[str] = field(default_factory=list)
    selection_reason: List[str] = field(default_factory=list)
    status: str = "DISCOVERY_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tokens(text: str) -> Set[str]:
    stop = {
        "yang", "dan", "atau", "untuk", "dari", "dengan", "dalam", "pada",
        "ini", "itu", "akan", "bisa", "jadi", "lebih", "sebuah", "tentang",
        "kenapa", "mengapa", "bagaimana", "why", "how", "the", "and", "for",
    }
    return {w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if w not in stop}


def _similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def _days_old(date_text: str) -> float:
    if not date_text:
        return 60.0
    try:
        value = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - value.astimezone(timezone.utc)).total_seconds() / 86400.0)
    except Exception:
        return 30.0



# Explicit niche qualification is intentionally separate from Editorial Fit Score.
# These patterns operate on the original signal, before generated narrative fields
# are added, so generic AI-generated wording cannot make an unrelated topic fit.
_PLACE_NICHE_PATTERNS = (
    r"\b(rumah|properti|kpr|tanah|lahan|hunian|perumahan|kost|apartemen|ruko|developer|pengembang)\b",
    r"\b(kota|urbanisasi|tata ruang|transportasi|komuter|macet|mrt|lrt|jalan tol|infrastruktur|desa|kampung|kawasan|ruang publik)\b",
    r"\b(minimarket|supermarket|pasar|warung|toko|ritel|retail|sewa|harga rumah|harga tanah|tempat tinggal)\b",
)
_SYSTEM_NICHE_PATTERNS = (
    r"\b(ekonomi|inflasi|suku bunga|biaya hidup|harga|gaji|upah|bisnis|perusahaan|pasokan|permintaan|pasar kerja)\b",
    r"\b(ai|teknologi|algoritma|otomasi|otomatisasi|internet|digital|pekerjaan|kerja|kantor|industri|infrastruktur)\b",
    r"\b(sejarah|kolonial|kebijakan|regulasi|pemerintah|institusi|sistem|aturan|demografi|populasi|penduduk)\b",
    r"\b(psikologi|perilaku|kebiasaan|identitas|kelas sosial|status sosial|insentif|konsumen|konsumerisme)\b",
)
_HUMAN_RELEVANCE_PATTERNS = (
    r"\b(manusia|orang|warga|masyarakat|keluarga|pekerja|konsumen|penduduk|generasi|anak muda)\b",
    r"\b(kehidupan|hidup|pilihan|waktu|uang|akses|kebutuhan|rasa aman|dampak|mengubah|memengaruhi|mempengaruhi)\b",
)
_SPECIFIC_CASE_PATTERNS = (
    r"\b(indonesia|jakarta|bandung|surabaya|yogyakarta|medan|bekasi|semarang|makassar|singapura|jepang|amerika)\b",
    r"\b(19\d{2}|20\d{2}|abad ke-\d+)\b",
)


def evaluate_niche_alignment(
    title: str,
    classification: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score whether an original topic signal fits Nugi's human/place/system niche.

    The score is a transparent heuristic, not a calibrated probability. It is
    deliberately computed from the original title rather than generated copy.
    """
    text = re.sub(r"\s+", " ", str(title or "")).strip().lower()
    place_match = any(re.search(pattern, text) for pattern in _PLACE_NICHE_PATTERNS)
    system_match = any(re.search(pattern, text) for pattern in _SYSTEM_NICHE_PATTERNS)
    human_match = any(re.search(pattern, text) for pattern in _HUMAN_RELEVANCE_PATTERNS)
    specific_case = any(re.search(pattern, text) for pattern in _SPECIFIC_CASE_PATTERNS)
    question_match = bool(re.search(
        r"\b(kenapa|mengapa|bagaimana|why|how|apa yang membuat|apa sebab)\b",
        text,
    ))

    score = 0
    matched_dimensions: List[str] = []
    if place_match:
        score += 35
        matched_dimensions.append("place/living environment")
    if system_match:
        score += 25
        matched_dimensions.append("system/mechanism")
    if human_match:
        score += 20
        matched_dimensions.append("human consequence")
    if specific_case and (place_match or system_match):
        score += 10
        matched_dimensions.append("specific case or context")
    if question_match:
        score += 10
        matched_dimensions.append("explanatory question")
    score = min(100, score)

    # A human-only or trending-only headline cannot qualify by itself. It needs
    # a credible place or system connection, not just a generic human keyword.
    has_niche_anchor = place_match or system_match
    if has_niche_anchor and score >= 55 and human_match:
        decision = "QUALIFIED"
        reason = "Ada koneksi niche dan konsekuensi manusia yang cukup jelas untuk masuk ke riset mendalam."
    elif has_niche_anchor and score >= 25:
        decision = "NEEDS_SCOPING"
        reason = "Ada sinyal tempat/sistem, tetapi pertanyaan atau konsekuensi manusia perlu dipertegas sebelum riset mendalam."
    else:
        decision = "REJECTED"
        reason = "Judul belum menunjukkan hubungan bermakna dengan tempat, sistem, atau mekanisme yang membentuk kehidupan manusia."

    if matched_dimensions:
        reason += " Dimensi terdeteksi: " + ", ".join(matched_dimensions) + "."
    return {
        "score": float(score),
        "decision": decision,
        "reason": reason,
        "matched_dimensions": matched_dimensions,
        "has_place_connection": place_match,
        "has_system_connection": system_match,
        "has_human_relevance": human_match,
        "specific_case": specific_case,
        "explanatory_question": question_match,
    }


def _recency_score(date_text: str) -> float:
    age = _days_old(date_text)
    if age <= 1:
        return 25.0
    if age <= 3:
        return 22.0
    if age <= 7:
        return 18.0
    if age <= 30:
        return 12.0
    if age <= 90:
        return 7.0
    return 3.0


def _narrative_title(headline: str, classification: Dict[str, Any]) -> str:
    clean = re.sub(r"\s+", " ", (headline or "").strip(" .,:;"))
    if not clean:
        return "Fenomena baru yang sedang mengubah cara manusia hidup"

    domain = classification.get("primary_domain", "human")
    if clean.endswith("?"):
        return clean
    if domain == "property":
        return f"Apa yang sebenarnya berubah di balik {clean}?"
    if domain == "city":
        return f"Kenapa {clean.lower()} bisa mengubah cara kita hidup di kota?"
    if domain == "ai":
        return f"Kalau {clean.lower()}, apa yang berubah dari cara manusia hidup?"
    if domain == "history":
        return f"Bagaimana {clean.lower()} mengubah tempat kita hidup hari ini?"
    return f"Apa yang sebenarnya terjadi di balik {clean.lower()}?"


def _human_question(topic: str, classification: Dict[str, Any]) -> str:
    domain = classification.get("primary_domain", "human")
    anchor = classification.get("anchor", "housing")
    if domain == "property":
        return f"Kenapa perubahan pada {anchor} akhirnya terasa di uang, waktu, atau rasa aman kita?"
    if domain == "city":
        return "Mengapa perubahan kota akhirnya menentukan bagaimana kita bergerak, bekerja, dan tinggal?"
    if domain == "ai":
        return "Kalau teknologi mengubah pekerjaan, apa yang ikut berubah dari tempat manusia hidup?"
    if domain == "history":
        return "Keputusan manusia di masa lalu masih menentukan ruang hidup apa yang kita miliki sekarang?"
    return "Mengapa perubahan yang tampak jauh dari kehidupan sehari-hari akhirnya terasa sangat dekat?"


def _deeper_why(classification: Dict[str, Any]) -> str:
    domain = classification.get("primary_domain", "human")
    lens = classification.get("lens", "sociology")
    return (
        f"Telusuri insentif, sejarah, desain, dan perilaku yang membuat fenomena ini bertahan; "
        f"gunakan lensa {lens} untuk menjelaskan mekanismenya, bukan sekadar mengulang gejalanya "
        f"dalam domain {domain}."
    )


def _read_existing_content(repo_root: Path, limit: int = 120) -> List[str]:
    output = repo_root / "output"
    if not output.is_dir():
        return []

    texts: List[str] = []
    for path in sorted(output.rglob("*.md"))[:limit]:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        heading = next(
            (line.strip("# ").strip() for line in content.splitlines() if line.startswith("#")),
            "",
        )
        if heading:
            texts.append(heading[:240])
        elif content.strip():
            texts.append(content[:240])
    return texts


def _dedupe_candidates(
    candidates: Sequence[ContentOpportunity],
    existing: Sequence[str],
) -> List[ContentOpportunity]:
    accepted: List[ContentOpportunity] = []
    seen = list(existing)
    for candidate in sorted(candidates, key=lambda x: x.opportunity_score, reverse=True):
        if any(_similarity(candidate.suggested_title, prior) >= 0.72 for prior in seen):
            continue
        accepted.append(candidate)
        seen.append(candidate.suggested_title)
    return accepted


class IdeaDiscoveryEngine:
    def __init__(self, *, rss_service: Optional[Any] = None, repo_root: Optional[Path] = None):
        self.rss_service = rss_service or RSSDiscoveryService()
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2])

    def _collect_signals(
        self,
        queries: Sequence[str],
        max_items_per_query: int,
    ) -> List[Any]:
        items: List[Any] = []
        seen: Set[str] = set()
        for query in queries:
            try:
                discovered = self.rss_service.discover(query, max_items=max_items_per_query)
            except Exception:
                discovered = []
            for item in discovered or []:
                key = getattr(item, "canonical_url", "") or (
                    getattr(item, "source_name", "") + "::" + getattr(item, "title", "")
                )
                key = str(key).strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(item)
        return items

    @staticmethod
    def _source_names(items: Iterable[Any]) -> List[str]:
        result: List[str] = []
        for item in items:
            name = str(getattr(item, "source_name", "") or "").strip()
            if name and name not in result:
                result.append(name)
        return result

    def _make_candidate(self, item: Any, existing_topics: Sequence[str]) -> Optional[ContentOpportunity]:
        headline = str(getattr(item, "title", "") or "").strip()
        if not headline:
            return None

        classification = classify_topic(headline)
        niche = evaluate_niche_alignment(headline, classification)
        story_type_result = classify_story_type(headline)
        story_type = story_type_result.get("primary_type", "hidden_system") if isinstance(story_type_result, dict) else str(story_type_result)
        fit = calculate_editorial_fit(
            {
                "title": headline,
                "human_question": _human_question(headline, classification),
                "deeper_why": _deeper_why(classification),
                "story_type": story_type,
                "everyday_life_scene": "Orang biasa melihat konsekuensi fenomena ini dalam keputusan hidup sehari-hari.",
                "primary_human_basic_need": "Curiosity",
                "life_lens": "wealth" if classification.get("lens") == "economics" else "relationship",
                "source_candidates": [getattr(item, "source_name", "")],
            }
        )
        fit_score = float(fit.get("total_score", 0.0))
        source_names = self._source_names([item])
        recency = _recency_score(str(getattr(item, "published_at", "") or ""))
        nugi_fit = niche["score"] / 5.0
        novelty = max(
            0.0,
            15.0 - max((_similarity(headline, prior) for prior in existing_topics), default=0.0) * 15.0,
        )
        evidence = 7.0 + min(3.0, len(source_names))
        visual = 4.0 if classification.get("primary_domain") in {"city", "history", "property"} else 3.0
        opportunity = min(
            100.0,
            recency * 0.25
            + nugi_fit
            + novelty
            + evidence
            + visual
            + min(20.0, fit_score * 0.20),
        )
        reasons = [
            "current discovery signal from configured intelligence feeds",
            f"editorial fit {fit_score:.0f}/100",
            f"Nugi-domain alignment: {classification.get('primary_domain')}",
            f"niche qualification {niche['decision']} ({niche['score']:.0f}/100): {niche['reason']}",
        ]
        return ContentOpportunity(
            suggested_title=_narrative_title(headline, classification),
            source_headline=headline,
            source_url=str(getattr(item, "canonical_url", "") or ""),
            source_names=source_names,
            source_count=len(source_names),
            published_at=str(getattr(item, "published_at", "") or ""),
            primary_domain=classification.get("primary_domain", ""),
            anchor=classification.get("anchor", ""),
            lens=classification.get("lens", ""),
            research_mode="current",
            story_type=story_type,
            human_question=_human_question(headline, classification),
            deeper_why=_deeper_why(classification),
            editorial_fit_score=fit_score,
            niche_fit_score=niche["score"],
            niche_decision=niche["decision"],
            niche_fit_reason=niche["reason"],
            opportunity_score=round(opportunity, 2),
            novelty_score=round(novelty, 2),
            evidence_signal=round(evidence, 2),
            nugi_fit_score=round(nugi_fit, 2),
            recency_score=round(recency, 2),
            visual_potential_score=round(visual, 2),
            selection_reason=reasons,
        )

    def _enrich_with_research(self, candidate: ContentOpportunity, depth: str = "quick") -> None:
        """Run a bounded evidence pass on one candidate without making discovery a hard dependency."""
        try:
            from engine.pipeline.research_dossier import DossierGenerator

            research_topic = candidate.source_headline or candidate.suggested_title
            dossier = DossierGenerator().build_dossier(
                research_topic,
                max_evidence_per_source=2,
                depth=depth,
                recency="m",
            )
            candidate.evidence_strength = round(float(dossier.evidence_strength), 3)
            candidate.research_claims_count = len(dossier.claims)
            candidate.research_primary_sources_count = len(dossier.primary_sources)
            candidate.research_status = str(dossier.epistemic_status or "UNKNOWN")
            candidate.research_findings = [str(item) for item in dossier.key_findings[:3]]
            evidence_bonus = min(12.0, candidate.evidence_strength * 12.0)
            source_bonus = min(6.0, candidate.research_primary_sources_count * 2.0)
            candidate.opportunity_score = round(
                min(100.0, candidate.opportunity_score + evidence_bonus + source_bonus),
                2,
            )
            candidate.selection_reason.append(
                f"bounded evidence pass: {candidate.research_status}, "
                f"strength {candidate.evidence_strength:.2f}, "
                f"{candidate.research_primary_sources_count} primary-source leads"
            )
        except Exception as exc:
            candidate.research_status = "RESEARCH_UNAVAILABLE"
            candidate.selection_reason.append(
                "evidence pass unavailable; candidate remains discovery-only"
            )

    def discover(
        self,
        *,
        count: int = 5,
        queries: Optional[Sequence[str]] = None,
        include_evergreen_fallback: bool = True,
        max_items_per_query: int = 8,
        enrich_with_research: bool = False,
        research_top_n: int = 2,
        research_depth: str = "quick",
    ) -> Dict[str, Any]:
        requested = max(1, min(20, int(count)))
        queries = tuple(queries or DEFAULT_DISCOVERY_QUERIES)
        feed_items = self._collect_signals(queries, max_items_per_query=max_items_per_query)
        existing_topics = _read_existing_content(self.repo_root)
        candidates: List[ContentOpportunity] = []

        for item in feed_items:
            candidate = self._make_candidate(item, existing_topics)
            if candidate and candidate.niche_decision != "REJECTED":
                candidates.append(candidate)

        if include_evergreen_fallback and len(candidates) < requested:
            for seed in EVERGREEN_SEEDS:
                classification = classify_topic(seed)
                story_type_result = classify_story_type(seed)
                story_type = story_type_result.get("primary_type", "hidden_system") if isinstance(story_type_result, dict) else str(story_type_result)
                fit = calculate_editorial_fit(
                    {
                        "title": seed,
                        "human_question": _human_question(seed, classification),
                        "deeper_why": _deeper_why(classification),
                        "story_type": story_type,
                        "everyday_life_scene": "Pekerja atau keluarga membuat kompromi nyata terkait rumah, waktu, uang, atau mobilitas.",
                        "primary_human_basic_need": "Shelter",
                        "life_lens": "wealth",
                        "source_candidates": ["institutional research candidates"],
                    }
                )
                fit_score = float(fit.get("total_score", 0.0))
                niche = evaluate_niche_alignment(seed, classification)
                if niche["decision"] == "REJECTED":
                    continue
                novelty = max(
                    0.0,
                    15.0 - max((_similarity(seed, prior) for prior in existing_topics), default=0.0) * 15.0,
                )
                nugi_fit = niche["score"] / 5.0
                opportunity = min(95.0, 32.0 + nugi_fit + novelty + min(15.0, fit_score * 0.15))
                candidates.append(
                    ContentOpportunity(
                        suggested_title=seed,
                        primary_domain=classification.get("primary_domain", ""),
                        anchor=classification.get("anchor", ""),
                        lens=classification.get("lens", ""),
                        research_mode=classification.get("research_mode", "evergreen"),
                        story_type=story_type,
                        human_question=_human_question(seed, classification),
                        deeper_why=_deeper_why(classification),
                        editorial_fit_score=fit_score,
                        niche_fit_score=niche["score"],
                        niche_decision=niche["decision"],
                        niche_fit_reason=niche["reason"],
                        opportunity_score=round(opportunity, 2),
                        novelty_score=round(novelty, 2),
                        evidence_signal=8.0,
                        nugi_fit_score=round(nugi_fit, 2),
                        recency_score=3.0,
                        visual_potential_score=4.0,
                        selection_reason=[
                            "evergreen fallback because current-feed coverage is insufficient",
                            f"editorial fit {fit_score:.0f}/100",
                            f"niche qualification {niche['decision']} ({niche['score']:.0f}/100): {niche['reason']}",
                        ],
                    )
                )

        ranked = _dedupe_candidates(candidates, existing_topics)[: max(requested, min(20, requested + 3))]
        if enrich_with_research and ranked:
            for candidate in ranked[: max(0, min(int(research_top_n), 3))]:
                self._enrich_with_research(candidate, depth=research_depth)
            ranked.sort(key=lambda x: x.opportunity_score, reverse=True)

        ranked = ranked[:requested]
        return {
            "status": "ok",
            "intent": "DISCOVER_CONTENT",
            "count_requested": requested,
            "count_returned": len(ranked),
            "queries": list(queries),
            "signals_considered": len(feed_items),
            "candidates": [item.to_dict() for item in ranked],
            "safety": {
                "feed_items_are_discovery_only": True,
                "no_feed_item_is_treated_as_verified_evidence": True,
                "deep_research_required_before_script_claims": True,
            },
        }
