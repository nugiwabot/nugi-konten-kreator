"""
engine/pipeline/media_finder.py
===============================
Canonical front-door helper for finding photos and footage for Nugi content.

Designed for simplicity, speed, and storytelling alignment:
  STORY → MICRO-BEAT → VISUAL NEED → MEDIA FINDER → RANKING → DOWNLOAD

Supported Modes:
- Media: photo | video | any
- Era: historical | past | present | future | timeless | auto
- Style: formal | neutral | documentary | archival | cinematic | conceptual | auto

Provider Routing:
- PRESENT + PHOTO: Pexafy (semantic photo search) + Wikimedia Commons
- PAST / HISTORICAL: Wikimedia Commons + Internet Archive (archival photos & footage)
- HISTORICAL + VIDEO: Internet Archive first + Wikimedia Commons
- FUTURE + PHOTO: Pexafy (conceptual query expansion) + Wikimedia Commons
- VIDEO (any era): Internet Archive + Wikimedia Commons (providers that return video)

Reuses existing:
- MediaRanker (engine/pipeline/media_ranker.py) for semantic deduplication and ranking
- MediaDownloader (engine/pipeline/media_downloader.py) for optional batch downloading & provenance logging
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.config import MEDIA_ASSETS_DIR
from engine.pipeline.media_downloader import DownloadReport, MediaDownloader
from engine.pipeline.media_ranker import MediaRanker
from engine.providers.internet_archive_provider import InternetArchiveProvider
from engine.providers.media import MediaItem, MediaProvider
from engine.providers.pexafy_provider import PexafyProvider
from engine.providers.wikimedia_provider import WikimediaProvider

logger = logging.getLogger(__name__)

# ── Vocabulary and Stop Words ──────────────────────────────────────────────────

_ID_STOP_WORDS = {
    "cari", "carikan", "tolong", "saya", "kami", "satu", "dua", "tiga",
    "untuk", "yang", "dan", "di", "ke", "dari", "dengan", "tentang",
    "mengenai", "adalah", "ini", "itu", "bisa", "foto", "gambar", "video",
    "footage", "visual", "minta", "ingin", "mau", "sebuah", "suatu",
}

_EN_STOP_WORDS = {
    "find", "search", "get", "show", "me", "some", "a", "an", "the",
    "of", "in", "on", "at", "for", "with", "about", "related", "please",
    "photo", "photos", "picture", "pictures", "image", "images", "video",
    "footage", "clip", "clips",
}

# Indonesian → English translation helper for query intelligence
_ID_EN_DICT = {
    "manusia mulai menetap pada zaman prasejarah": "prehistoric human settlement early hunter gatherers transitioning to village life",
    "manusia mulai hidup menetap pada zaman prasejarah": "prehistoric human settlement early agriculture transition to village",
    "manusia bekerja di kantor modern": "professional office worker in modern contemporary workplace",
    "rumah masa depan ketika ai sudah mengubah cara manusia bekerja": "futuristic home environment human living space with ambient AI technology",
    "rumah masa depan dengan ai": "near future conceptual home environment with ambient technology",
    "zaman prasejarah": "prehistoric era",
    "prasejarah": "prehistoric",
    "mulai menetap": "early human settlement",
    "hidup menetap": "sedentary lifestyle village settlement",
    "kantor modern": "modern office workplace",
    "masa depan": "future",
    "revolusi industri": "industrial revolution",
    "perang dunia": "world war",
    "perang dunia kedua": "world war II",
    "perang dunia pertama": "world war I",
    "pasar tradisional": "traditional market",
    "pelabuhan penting": "major shipping seaport",
    "tempat tinggal": "human dwelling shelter",
    "pabrik manufaktur": "manufacturing factory",
    "lingkungan perkotaan": "urban city neighborhood",
    "manusia": "human",
    "orang": "person",
    "pekerja": "worker",
    "karyawan": "employee",
    "kantor": "office",
    "rumah": "home",
    "tanah": "land",
    "kota": "city",
    "jalan": "street",
    "sungai": "river",
    "keluarga": "family",
    "bekerja": "working",
    "teknologi": "technology",
    "sejarah": "history",
    "kuno": "ancient",
    "arsip": "archival",
    "pabrik": "factory",
    "pelabuhan": "seaport",
    "desa": "village",
    "anak": "child",
    "masyarakat": "community",
    "transportasi": "transportation",
    "kehidupan": "life",
}

# ── Era and Style Detection Cues ───────────────────────────────────────────────

_HISTORICAL_CUES = {
    "sejarah", "kuno", "prasejarah", "zaman dulu", "tempo dulu", "arsip",
    "archival", "archive", "historical", "vintage", "century", "abad",
    "perang", "colonial", "kolonial", "kerajaan", "prehistoric", "ancient",
    "d-day", "ww2", "wwii", "ww1", "1944", "1945", "1800", "1900",
}

_FUTURE_CUES = {
    "masa depan", "future", "futuristik", "futuristic", "ai", "artificial intelligence",
    "2050", "spekulatif", "speculative", "near-future", "kecerdasan buatan",
    "robotik", "konsep masa depan",
}

_PRESENT_CUES = {
    "modern", "saat ini", "sekarang", "hari ini", "kontemporer", "contemporary",
    "present", "today", "current", "kantor modern", "smart office",
}

_YEAR_RE = re.compile(r"\b(1[0-9]{3}|200[0-9])\b")


# ── Data Structures ────────────────────────────────────────────────────────────

@dataclass
class MediaFinderItem:
    """Standardized representation of a media candidate returned by MediaFinder."""
    rank: int
    title: str
    provider: str
    media_type: str
    score: float
    source_url: str
    download_url: str
    thumbnail_url: str = ""
    creator: str = ""
    date: str = ""
    license: str = ""
    license_url: str = ""
    local_path: Optional[str] = None
    width: int = 0
    height: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaFinderResult:
    """Structured result returned by MediaFinder."""
    request: str
    media_type: str
    era: str
    style: str
    queries: List[str]
    providers_contacted: List[str]
    results: List[MediaFinderItem]
    total_candidates_found: int = 0
    downloaded_count: int = 0
    fallback_reason: str = ""
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["results"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.results]
        return d

    def preview(self, max_items: int = 5) -> str:
        """Return a clean human-readable preview."""
        lines = [
            "=" * 64,
            f"  NUGI MEDIA FINDER — RESULT PREVIEW",
            "=" * 64,
            f"  Request:    {self.request}",
            f"  Media Type: {self.media_type} | Era: {self.era} | Style: {self.style}",
            f"  Providers:  {', '.join(self.providers_contacted)}",
            f"  Found:      {self.total_candidates_found} candidates | Returned: {len(self.results)}",
            "-" * 64,
            "  SEARCH QUERIES USED:",
        ]
        for idx, q in enumerate(self.queries, 1):
            lines.append(f"    [{idx}] {q}")
        lines.append("-" * 64)
        lines.append("  TOP CANDIDATES:")
        if not self.results:
            lines.append("    (No candidates matched the criteria)")
        for item in self.results[:max_items]:
            lines.append(
                f"  #{item.rank} [{item.provider.upper()}] [{item.media_type}] {item.title[:65]}"
            )
            lines.append(
                f"      Score: {item.score:.3f} | Creator: {item.creator or 'N/A'} | License: {item.license}"
            )
            lines.append(f"      Source: {item.source_url}")
            if item.local_path:
                lines.append(f"      Downloaded to: {item.local_path}")
            lines.append("")
        lines.append("=" * 64)
        return "\n".join(lines)


# ── MediaFinder Class ──────────────────────────────────────────────────────────

class MediaFinder:
    """
    Main user-facing entry point for finding media assets (photos & videos)
    for Nugi Content Creator.
    """

    def __init__(
        self,
        providers: Optional[List[MediaProvider]] = None,
        ranker: Optional[MediaRanker] = None,
        downloader: Optional[MediaDownloader] = None,
    ):
        # Default providers: Pexafy, Wikimedia Commons, Internet Archive
        self.providers: List[MediaProvider] = providers if providers is not None else [
            PexafyProvider(),
            WikimediaProvider(),
            InternetArchiveProvider(),
        ]
        self.ranker: MediaRanker = ranker or MediaRanker()
        self.downloader: MediaDownloader = downloader or MediaDownloader()

    # --------------------------------------------------------------------------
    # Public: find (search + rank only)
    # --------------------------------------------------------------------------

    def find(
        self,
        request: str,
        media: str = "any",
        era: str = "auto",
        style: str = "auto",
        count: int = 8,
    ) -> MediaFinderResult:
        """
        Search for photos or videos matching the natural-language request.

        Args:
            request: Natural language visual description (Indonesian or English).
            media: "photo" | "video" | "any" (or "image")
            era: "historical" | "past" | "present" | "future" | "timeless" | "auto"
            style: "formal" | "neutral" | "documentary" | "archival" | "cinematic" | "conceptual" | "auto"
            count: Number of ranked results to return (default 8).

        Returns:
            MediaFinderResult
        """
        if not request or not request.strip():
            return MediaFinderResult(
                request="",
                media_type=media,
                era=era,
                style=style,
                queries=[],
                providers_contacted=[],
                results=[],
                total_candidates_found=0,
            )

        resolved_media = self._normalize_media_type(media, request)
        resolved_era = self._resolve_era(era, request)
        resolved_style = self._resolve_style(style, resolved_era, request)

        queries = self._generate_query_intelligence(request, resolved_era, resolved_style)
        routed_providers = self._route_providers(resolved_era, resolved_media)

        candidates = self._gather_candidates(queries, routed_providers, resolved_media, max_items=max(count * 3, 15))

        ranked_items, fallback_reason = self._rank_candidates(
            original_request=request,
            candidates=candidates,
            media_type=resolved_media,
            era=resolved_era,
            style=resolved_style,
            count=count,
        )

        providers_contacted = [p.PROVIDER_NAME for p in routed_providers]

        return MediaFinderResult(
            request=request,
            media_type=resolved_media,
            era=resolved_era,
            style=resolved_style,
            queries=queries,
            providers_contacted=providers_contacted,
            results=ranked_items,
            total_candidates_found=len(candidates),
            downloaded_count=0,
            fallback_reason=fallback_reason,
        )

    # --------------------------------------------------------------------------
    # Public: find_and_download (search + rank + download)
    # --------------------------------------------------------------------------

    def find_and_download(
        self,
        request: str,
        media: str = "any",
        era: str = "auto",
        style: str = "auto",
        count: int = 8,
        folder: Optional[str] = None,
    ) -> MediaFinderResult:
        """
        Search for media and download the top ranked candidates to the local filesystem.
        Provenance metadata is preserved in sources.json.
        """
        result = self.find(request=request, media=media, era=era, style=style, count=count)
        if not result.results:
            return result

        # Convert MediaFinderItem back to MediaItem for MediaDownloader
        media_items: List[MediaItem] = []
        for r in result.results:
            media_items.append(
                MediaItem(
                    provider=r.provider,
                    id=r.download_url,
                    title=r.title,
                    description=r.metadata.get("description", r.title),
                    media_type=r.media_type,
                    source_url=r.source_url,
                    download_url=r.download_url,
                    thumbnail_url=r.thumbnail_url,
                    creator=r.creator,
                    date=r.date,
                    license=r.license,
                    file_size_bytes=0,
                    width=r.width,
                    height=r.height,
                    metadata=r.metadata,
                    reranker_score=r.score,
                    final_rank=r.rank,
                )
            )

        target_folder = folder or f"finder/{self._sanitize_folder_name(request)}"
        download_report: DownloadReport = self.downloader.download_batch(
            items=media_items,
            folder=target_folder,
            count=count,
        )

        # Map local_path back to results
        downloaded_map: Dict[str, str] = {
            f.download_url: f.local_path for f in download_report.successful
        }
        for item in result.results:
            if item.download_url in downloaded_map:
                item.local_path = downloaded_map[item.download_url]

        result.downloaded_count = download_report.success_count
        return result

    # --------------------------------------------------------------------------
    # Public: find_from_microbeat
    # --------------------------------------------------------------------------

    def find_from_microbeat(
        self,
        microbeat: Dict[str, Any],
        count: int = 8,
        download: bool = False,
        folder: Optional[str] = None,
    ) -> MediaFinderResult:
        """
        Find assets using a microbeat specification dictionary.

        Accepts:
            {
                "visual_concept": "...",
                "search_query": "...",
                "preferred_media_type": "photo|video|any",
                "era": "historical|present|...",
                "style": "formal|documentary|..."
            }
        """
        search_query = microbeat.get("search_query")
        visual_concept = microbeat.get("visual_concept") or ""

        # Prioritize explicit search_query; derive from visual_concept if none exists
        if search_query and search_query.strip():
            effective_request = search_query.strip()
        else:
            effective_request = visual_concept.strip()

        media = (
            microbeat.get("preferred_media_type")
            or microbeat.get("media_type")
            or microbeat.get("media")
            or "any"
        )
        era = microbeat.get("era", "auto")
        style = microbeat.get("style", "auto")

        if download:
            return self.find_and_download(
                request=effective_request,
                media=media,
                era=era,
                style=style,
                count=count,
                folder=folder,
            )
        return self.find(
            request=effective_request,
            media=media,
            era=era,
            style=style,
            count=count,
        )

    # --------------------------------------------------------------------------
    # Internal: Query Intelligence & Variants
    # --------------------------------------------------------------------------

    def _generate_query_intelligence(
        self,
        request: str,
        era: str,
        style: str,
    ) -> List[str]:
        """
        Transform a natural language visual request into 4 distinct query variants:
          1. primary descriptive query (well-formed scene sentence)
          2. style-specific variant (formal, documentary, archival, etc.)
          3. contextual variant (spatial / environmental context)
          4. fallback query (concise direct keywords)
        """
        core_english = self._translate_to_core_english(request)

        # 1. Primary descriptive query
        if style == "formal":
            primary = f"{core_english}, professional editorial photography, clean natural lighting"
        elif style == "archival":
            primary = f"{core_english}, archival historical photograph, authentic period reference"
        elif style == "documentary":
            primary = f"{core_english}, candid documentary photography, authentic real setting"
        elif style == "cinematic":
            primary = f"{core_english}, atmospheric cinematic composition, dramatic lighting"
        elif style == "conceptual":
            primary = f"{core_english}, conceptual speculative visualization, editorial perspective"
        else:
            primary = f"{core_english}, neutral documentary photography, realistic natural lighting"

        # 2. Style-specific variant
        style_variant = self._build_style_variant(core_english, style, era)

        # 3. Contextual / environmental variant
        contextual = self._build_contextual_variant(core_english, era)

        # 4. Fallback concise query
        fallback = self._build_fallback_query(core_english)

        queries = [primary, style_variant, contextual, fallback]
        # Deduplicate while preserving order
        unique_queries: List[str] = []
        for q in queries:
            q_clean = " ".join(q.split())
            if q_clean and q_clean not in unique_queries:
                unique_queries.append(q_clean)

        return unique_queries

    def _translate_to_core_english(self, text: str) -> str:
        """Translate key phrases and terms from Indonesian to clean English core concept."""
        clean = text.lower().strip()
        # Direct exact or prefix lookup
        for id_phrase, en_phrase in _ID_EN_DICT.items():
            if id_phrase in clean:
                clean = clean.replace(id_phrase, en_phrase)

        # Remove stop words
        words = clean.split()
        filtered = [
            w for w in words
            if w not in _ID_STOP_WORDS and w not in _EN_STOP_WORDS and len(w) > 1
        ]
        if not filtered:
            return text.strip()

        # Word-level replacement for any remaining Indonesian words
        result_words = []
        for w in filtered:
            result_words.append(_ID_EN_DICT.get(w, w))

        return " ".join(result_words)

    @staticmethod
    def _build_style_variant(core: str, style: str, era: str) -> str:
        """Build style-specific query adhering to visual style rules."""
        if style == "formal":
            return f"{core}, corporate workplace professional setting, realistic neutral composition"
        if style == "archival":
            if era in ("historical", "past"):
                return f"{core}, original archival photograph, historical document"
            return f"{core}, archival reference photography"
        if style == "documentary":
            return f"{core}, observational photography, real ordinary environment, natural lighting"
        if style == "cinematic":
            return f"{core}, cinematic wide shot, atmospheric framing"
        if style == "conceptual":
            return f"{core}, human-centered technology conceptual scene, modern architectural space"
        # neutral
        return f"{core}, ordinary everyday environment, observational realistic photo"

    @staticmethod
    def _build_contextual_variant(core: str, era: str) -> str:
        """Add human-place spatial context to the query."""
        if era in ("historical", "past"):
            return f"{core}, historical city street and human dwelling"
        if era == "future":
            return f"{core}, modern architectural space and smart living environment"
        return f"{core}, contemporary urban and interior environment"

    @staticmethod
    def _build_fallback_query(core: str) -> str:
        """Generate concise 3-5 keyword fallback for simple catalog indexing."""
        words = [w for w in core.split() if len(w) > 2]
        return " ".join(words[:5])

    # --------------------------------------------------------------------------
    # Internal: Normalization & Detection
    # --------------------------------------------------------------------------

    @staticmethod
    def _normalize_media_type(media: str, request: str) -> str:
        m = (media or "any").lower().strip()
        if m in ("photo", "image", "foto", "gambar"):
            return "photo"
        if m in ("video", "footage", "film", "rekaman"):
            return "video"
        if m in ("any", "all", "semua"):
            return "any"
        # If auto or unrecognized, detect from request
        lower_req = request.lower()
        if any(w in lower_req for w in ("video", "footage", "film", "rekaman", "klip")):
            return "video"
        if any(w in lower_req for w in ("foto", "gambar", "photo", "image", "potret")):
            return "photo"
        return "any"

    @staticmethod
    def _resolve_era(era: str, request: str) -> str:
        e = (era or "auto").lower().strip()
        if e in ("historical", "past", "present", "future", "timeless"):
            return "historical" if e == "past" else e
        if e != "auto":
            return "timeless"

        lower_req = request.lower()
        if any(w in lower_req for w in _HISTORICAL_CUES) or _YEAR_RE.search(request):
            return "historical"
        if any(w in lower_req for w in _FUTURE_CUES):
            return "future"
        if any(w in lower_req for w in _PRESENT_CUES):
            return "present"
        return "timeless"

    @staticmethod
    def _resolve_style(style: str, era: str, request: str) -> str:
        s = (style or "auto").lower().strip()
        valid_styles = {"formal", "neutral", "documentary", "archival", "cinematic", "conceptual"}
        if s in valid_styles:
            return s

        lower_req = request.lower()
        if any(w in lower_req for w in ("formal", "resmi", "profesional", "kantor", "bisnis")):
            return "formal"
        if any(w in lower_req for w in ("arsip", "archival", "vintage", "kuno")):
            return "archival"
        if any(w in lower_req for w in ("cinematic", "sinematik", "dramatis", "filmis")):
            return "cinematic"
        if any(w in lower_req for w in ("konseptual", "conceptual", "spekulatif", "speculative")):
            return "conceptual"
        if any(w in lower_req for w in ("dokumenter", "documentary", "kandid", "candid", "realistis")):
            return "documentary"

        # Defaults based on resolved era
        if era in ("historical", "past"):
            return "documentary"
        if era == "future":
            return "conceptual"
        return "neutral"

    # --------------------------------------------------------------------------
    # Internal: Provider Routing
    # --------------------------------------------------------------------------

    def _route_providers(self, era: str, media: str) -> List[MediaProvider]:
        """
        Route to providers based on era and media type:
        - PRESENT + PHOTO: Pexafy first, then Wikimedia
        - PAST/HISTORICAL: Wikimedia Commons + Internet Archive
        - HISTORICAL + VIDEO: Internet Archive first, then Wikimedia
        - FUTURE + PHOTO: Pexafy (conceptual) + Wikimedia
        - VIDEO: Wikimedia Commons + Internet Archive (Pexafy NEVER routed for video)
        """
        by_name: Dict[str, MediaProvider] = {p.PROVIDER_NAME: p for p in self.providers}

        selected: List[MediaProvider] = []

        if media == "video":
            # Pexafy NEVER supports video
            if "internet_archive" in by_name:
                selected.append(by_name["internet_archive"])
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
            return selected

        # Photo or Any
        if era in ("historical", "past"):
            # Prefer Wikimedia Commons and Internet Archive for archival depth
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
            if "internet_archive" in by_name:
                selected.append(by_name["internet_archive"])
            if media != "video" and "pexafy" in by_name:
                selected.append(by_name["pexafy"])
        elif era == "future":
            # Prefer Pexafy for modern conceptual photography, supplemented by Wikimedia
            if "pexafy" in by_name:
                selected.append(by_name["pexafy"])
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
        else:
            # Present or Timeless
            if "pexafy" in by_name:
                selected.append(by_name["pexafy"])
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
            if "internet_archive" in by_name and media != "photo":
                selected.append(by_name["internet_archive"])

        return selected if selected else self.providers

    # --------------------------------------------------------------------------
    # Internal: Candidate Gathering
    # --------------------------------------------------------------------------

    def _gather_candidates(
        self,
        queries: List[str],
        providers: List[MediaProvider],
        media: str,
        max_items: int = 25,
    ) -> List[MediaItem]:
        """Gather candidates across queries and providers, deduplicating by dedup_key."""
        candidates: List[MediaItem] = []
        seen_keys: set = set()

        # Map 'photo' to 'image' for provider APIs
        provider_media_type = "image" if media == "photo" else media

        for q in queries:
            if len(candidates) >= max_items:
                break
            for provider in providers:
                if len(candidates) >= max_items:
                    break
                try:
                    items = provider.search_media(
                        query=q,
                        media_type=provider_media_type,
                        max_results=max(max_items - len(candidates), 5),
                    )
                    for item in items:
                        key = item.dedup_key()
                        if key not in seen_keys:
                            seen_keys.add(key)
                            candidates.append(item)
                except Exception as e:
                    logger.warning(
                        f"MediaFinder: Provider {provider.PROVIDER_NAME} failed for query '{q}': {e}"
                    )

        return candidates

    # --------------------------------------------------------------------------
    # Internal: Semantic Ranking & Filtering
    # --------------------------------------------------------------------------

    def _rank_candidates(
        self,
        original_request: str,
        candidates: List[MediaItem],
        media_type: str,
        era: str,
        style: str,
        count: int,
    ) -> Tuple[List[MediaFinderItem], str]:
        """Filter by media type affinity, run MediaRanker, and format as MediaFinderItems."""
        if not candidates:
            return [], "No candidates gathered from providers."

        # Filter strictly by requested media type
        filtered: List[MediaItem] = []
        for item in candidates:
            mtype = item.media_type.lower()
            if media_type == "photo" and mtype in ("video", "audio", "document"):
                continue
            if media_type == "video" and mtype != "video":
                continue
            filtered.append(item)

        # Fallback to candidates if filter was overly restrictive
        if not filtered and media_type == "any":
            filtered = candidates
        elif not filtered:
            # If user wanted video but none found, or wanted photo and none found
            return [], f"No matching candidates found for media_type='{media_type}'."

        ranked, fallback_reason = self.ranker.rank(
            original_request=original_request,
            candidates=filtered,
            top_n=count * 2,
        )

        results: List[MediaFinderItem] = []
        for rank_idx, item in enumerate(ranked[:count], 1):
            results.append(
                MediaFinderItem(
                    rank=rank_idx,
                    title=item.title,
                    provider=item.provider,
                    media_type=item.media_type,
                    score=item.reranker_score,
                    source_url=item.source_url,
                    download_url=item.download_url,
                    thumbnail_url=item.thumbnail_url,
                    creator=item.creator,
                    date=item.date,
                    license=item.license,
                    license_url=item.metadata.get("license_url", ""),
                    local_path=None,
                    width=item.width,
                    height=item.height,
                    metadata=item.metadata,
                )
            )

        return results, fallback_reason

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name.lower().strip())
        return clean[:40].strip("_") or "media_search"
