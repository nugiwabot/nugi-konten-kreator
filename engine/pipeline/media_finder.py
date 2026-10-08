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

from engine.pipeline.media_library import MediaLibrary

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.config import MEDIA_ASSETS_DIR
from engine.pipeline.media_downloader import DownloadReport, MediaDownloader
from engine.pipeline.media_query_expander import MediaQueryExpander
from engine.pipeline.media_ranker import MediaRanker
from engine.pipeline.visual_requirements import (
    GENERIC_ALLOWED,
    NO_BROLL,
    REAL_PREFERRED,
    REAL_REQUIRED,
    REMOTION_REQUIRED,
    ARCHIVAL_REFERENCE,
    DIRECT_CONTEXT,
    DOCUMENT,
    GENERIC_ATMOSPHERE,
    MOTION_GRAPHICS,
    NO_VISUAL,
    PRIMARY_EVIDENCE,
    classify_visual_requirement,
    extract_entities,
)
from engine.providers.capabilities import get_provider_capabilities, route_provider_names
from engine.providers.internet_archive_provider import InternetArchiveProvider
from engine.providers.library_of_congress_provider import LibraryOfCongressProvider
from engine.providers.media import MediaItem, MediaProvider
from engine.providers.pexafy_provider import PexafyProvider
from engine.providers.rights import is_reusable_rights_status, item_rights_status
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
    rights_status: str = "UNKNOWN"
    query: str = ""
    capability: List[str] = field(default_factory=list)
    semantic_score: float = 0.0
    contextual_score: float = 0.0
    generic_penalty: float = 0.0
    selection_reason: str = ""
    local_path: Optional[str] = None
    width: int = 0
    height: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    visual_requirement: str = ""
    source_role: str = ""
    authenticity_score: float = 0.0
    entity_match_score: float = 0.0
    temporal_match_score: float = 0.0
    location_match_score: float = 0.0
    event_match_score: float = 0.0
    source_specificity_score: float = 0.0
    matched_entities: List[str] = field(default_factory=list)
    matched_event: str = ""
    matched_location: str = ""
    matched_time: str = ""
    rejection_reason: str = ""
    is_archival: bool = False
    is_generic: bool = False
    human_basic_need_score: float = 0.0
    life_lens_score: float = 0.0
    everyday_relevance_score: float = 0.0
    human_place_relevance_score: float = 0.0
    human_alignment_score: float = 0.0
    human_basic_need: str = ""
    life_lens: str = ""

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
    visual_requirement: str = ""
    visual_type: str = ""
    entities: List[str] = field(default_factory=list)
    motion_spec: Optional[Dict[str, Any]] = None
    source_role: str = ""
    status: str = "OK"  # "OK", "INSUFFICIENT_EVIDENCE", "NO_BROLL", "REMOTION_REQUIRED"
    search_completed: bool = True
    usable_results: int = 0
    fallback_allowed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["results"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.results]
        return d

    def preview(self, max_items: int = 5) -> str:
        """Return a clean human-readable preview."""
        lines = [
            "=" * 64,
            "  NUGI MEDIA FINDER — RESULT PREVIEW",
            "=" * 64,
            f"  Request:            {self.request}",
            f"  Visual Requirement: {self.visual_requirement or 'auto'} | Status: {self.status} (Usable: {self.usable_results})",
            f"  Media Type:         {self.media_type} | Era: {self.era} | Style: {self.style}",
        ]
        if self.entities:
            lines.append(f"  Entities:           {', '.join(self.entities)}")
        if self.motion_spec:
            lines.append(f"  Motion Spec:        {self.motion_spec.get('type', '')} ({self.motion_spec})")
        lines.append(f"  Providers:          {', '.join(self.providers_contacted) if self.providers_contacted else 'None'}")
        lines.append(f"  Found:              {self.total_candidates_found} candidates | Returned: {len(self.results)}")
        lines.append("-" * 64)

        if self.status == "NO_BROLL":
            lines.append("  [NO_BROLL] Narrative pause — no visual search needed.")
            lines.append("=" * 64)
            return "\n".join(lines)

        if self.status == "REMOTION_REQUIRED":
            lines.append("  [REMOTION_REQUIRED] Motion graphics required — no stock footage search.")
            lines.append("=" * 64)
            return "\n".join(lines)

        if self.status == "INSUFFICIENT_EVIDENCE":
            lines.append("  ⚠ REAL EVIDENCE NOT FOUND")
            lines.append("  (Exact authentic evidence was required but no candidate met authenticity threshold)")
            lines.append("-" * 64)

        lines.append("  SEARCH QUERIES USED:")
        for idx, q in enumerate(self.queries, 1):
            lines.append(f"    [{idx}] {q}")
        lines.append("-" * 64)
        lines.append("  TOP CANDIDATES:")
        if not self.results:
            lines.append("    (No candidates matched the criteria)")
        for item in self.results[:max_items]:
            vr_tag = item.visual_requirement or self.visual_requirement or "MEDIA"
            s_role = item.source_role or "CONTEXT"
            lines.append(f"  #{item.rank} [{vr_tag}] [{s_role}]")
            lines.append(f"      Provider: {item.provider} | Type: {item.media_type}")
            if item.event_match_score > 0:
                lines.append(f"      Event Match: {item.event_match_score:.2f}")
            if item.entity_match_score > 0:
                lines.append(f"      Entity Match: {item.entity_match_score:.2f}")
            if item.authenticity_score > 0:
                lines.append(f"      Authenticity: {item.authenticity_score:.2f}")
            lines.append(f"      Title: {item.title[:65]}")
            lines.append(
                f"      Score: {item.score:.3f} | Creator: {item.creator or 'N/A'} | License: {item.license}"
            )
            if item.human_alignment_score > 0:
                lines.append(
                    f"      Human Fit: Need={item.human_basic_need or '-'} "
                    f"{item.human_basic_need_score:.2f} | Lens={item.life_lens or '-'} "
                    f"{item.life_lens_score:.2f} | Everyday={item.everyday_relevance_score:.2f} | "
                    f"Place={item.human_place_relevance_score:.2f} | Alignment={item.human_alignment_score:.2f}"
                )
            lines.append(f"      Source: {item.source_url}")
            if item.local_path:
                lines.append(f"      Downloaded to: {item.local_path}")
            if item.rejection_reason:
                lines.append(f"      [REJECTED]: {item.rejection_reason}")
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
            LibraryOfCongressProvider(),
        ]
        self.ranker: MediaRanker = ranker or MediaRanker()
        self.downloader: MediaDownloader = downloader or MediaDownloader()
        self.library: MediaLibrary = MediaLibrary()

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
        visual_requirement: str = "auto",
        research_intelligence: Optional[Dict[str, Any]] = None,
    ) -> MediaFinderResult:
        """
        Search for photos or videos matching the natural-language request.
        Applies documentary evidence classification, entity preservation, and authenticity filtering.

        Args:
            request: Natural language visual description (Indonesian or English).
            media: "photo" | "video" | "any" (or "image")
            era: "historical" | "past" | "present" | "future" | "timeless" | "auto"
            style: "formal" | "neutral" | "documentary" | "archival" | "cinematic" | "conceptual" | "auto"
            count: Number of ranked results to return (default 8).
            visual_requirement: "REAL_REQUIRED" | "REAL_PREFERRED" | "GENERIC_ALLOWED" | "NO_BROLL" | "REMOTION_REQUIRED" | "auto"

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
                usable_results=0,
            )

        # 1. Evidence Classification & Entity Extraction
        if visual_requirement == "auto":
            req_class, v_type, entity_objs, motion_spec, s_role = classify_visual_requirement(request)
            entities = [e["name"] for e in entity_objs]
        else:
            req_class = visual_requirement.upper().strip()
            entity_objs = extract_entities(request)
            entities = [e["name"] for e in entity_objs]
            _, v_type, _, motion_spec, s_role = classify_visual_requirement(request)
            if req_class == REAL_REQUIRED:
                s_role = PRIMARY_EVIDENCE
            elif req_class == REAL_PREFERRED:
                s_role = DIRECT_CONTEXT
            elif req_class == GENERIC_ALLOWED:
                s_role = GENERIC_ATMOSPHERE
            elif req_class == NO_BROLL:
                s_role = NO_VISUAL
            elif req_class == REMOTION_REQUIRED:
                s_role = MOTION_GRAPHICS

        # Short-circuit NO_BROLL (Section 19: narrative pause)
        if req_class == NO_BROLL:
            logger.info(f"MediaFinder: '{request}' classified as NO_BROLL. No media search conducted.")
            return MediaFinderResult(
                request=request,
                media_type=media,
                era=era,
                style=style,
                queries=[],
                providers_contacted=[],
                results=[],
                total_candidates_found=0,
                downloaded_count=0,
                fallback_reason="NO_BROLL: Narrative pause — no visual search required",
                visual_requirement=NO_BROLL,
                visual_type=v_type or "narrative_pause",
                entities=entities,
                motion_spec=None,
                source_role=NO_VISUAL,
                status="NO_BROLL",
                search_completed=True,
                usable_results=0,
                fallback_allowed=False,
            )

        # Short-circuit REMOTION_REQUIRED (Section 18: motion graphics)
        if req_class == REMOTION_REQUIRED:
            logger.info(f"MediaFinder: '{request}' classified as REMOTION_REQUIRED. Motion graphics spec generated.")
            return MediaFinderResult(
                request=request,
                media_type=media,
                era=era,
                style=style,
                queries=[],
                providers_contacted=[],
                results=[],
                total_candidates_found=0,
                downloaded_count=0,
                fallback_reason="REMOTION_REQUIRED: Motion graphics required — no stock search",
                visual_requirement=REMOTION_REQUIRED,
                visual_type=v_type or "STATISTIC",
                entities=entities,
                motion_spec=motion_spec or {"type": "bar_chart", "data_needed": True},
                source_role=MOTION_GRAPHICS,
                status="REMOTION_REQUIRED",
                search_completed=True,
                usable_results=0,
                fallback_allowed=False,
            )

        resolved_media = self._normalize_media_type(media, request)
        resolved_era = self._resolve_era(era, request)
        resolved_style = self._resolve_style(style, resolved_era, request)

        logger.info(
            f"MediaFinder.find: request='{request}', requested_media='{media}', "
            f"resolved_media='{resolved_media}', era='{resolved_era}', style='{resolved_style}', "
            f"visual_requirement='{req_class}', entities={entities}"
        )

        queries = self._generate_query_intelligence(
            request, resolved_era, resolved_style, media=resolved_media,
            entities=entities, visual_requirement=req_class,
            research_intelligence=research_intelligence,
        )
        routed_providers = self._route_providers(
            resolved_era, resolved_media, visual_requirement=req_class
        )

        # ── LOCAL LIBRARY FIRST: Check local catalog before remote searches ──
        local_candidates: List[MediaItem] = []
        try:
            local_hits = self.library.search_local(
                query=request,
                media_type=resolved_media,
                entities=entities,
                visual_requirement=req_class,
                max_results=count,
            )
            for hit in local_hits:
                local_candidates.append(
                    MediaItem(
                        provider="local_library",
                        id=hit["id"],
                        title=hit["title"],
                        description=hit["metadata"].get("description", hit["title"]),
                        media_type=hit["media_type"],
                        source_url=hit["source_url"],
                        download_url=hit["download_url"],
                        thumbnail_url="",
                        creator=hit.get("creator", ""),
                        date=hit.get("date", ""),
                        license=hit.get("metadata", {}).get("license", ""),
                        license_url=hit.get("metadata", {}).get("license_url", ""),
                        rights_status=hit.get("metadata", {}).get("rights_status", "UNKNOWN"),
                        retrieval_query=hit.get("metadata", {}).get("retrieval_query", ""),
                        provider_capability=hit.get("metadata", {}).get("provider_capability", ""),
                        selection_reason=hit.get("metadata", {}).get("selection_reason", ""),
                        visual_requirement=hit.get("visual_requirement", req_class),
                        matched_entities=hit.get("entities", []),
                        metadata=hit.get("metadata", {}),
                    )
                )
        except Exception as e:
            logger.warning(f"MediaFinder: Local library lookup failed: {e}")

        # If local candidates cover the request, we can minimize remote queries
        remote_max = max(count * 3 - len(local_candidates), 10)
        remote_candidates = self._gather_candidates(
            queries, routed_providers, resolved_media, max_items=remote_max
        )
        candidates = local_candidates + remote_candidates

        ranked_items, fallback_reason = self._rank_candidates(
            original_request=request,
            candidates=candidates,
            media_type=resolved_media,
            era=resolved_era,
            style=resolved_style,
            count=count,
            entities=entities,
            visual_requirement=req_class,
        )

        providers_contacted = [p.PROVIDER_NAME for p in routed_providers]

        # Evaluate usable results and authenticity gate (Section 10, 22)
        usable_items = [item for item in ranked_items if not item.rejection_reason]
        status = "OK"
        fallback_allowed = True

        if req_class == REAL_REQUIRED:
            if not usable_items:
                status = "INSUFFICIENT_EVIDENCE"
                fallback_allowed = False
                fallback_reason = "REAL_REQUIRED: Inadequate authentic evidence found. Generic stock rejected."
                logger.warning(
                    f"MediaFinder: REAL_REQUIRED hard gate failed for '{request}'. Usable results: 0"
                )
            results_to_return = usable_items
        else:
            results_to_return = ranked_items

        return MediaFinderResult(
            request=request,
            media_type=resolved_media,
            era=resolved_era,
            style=resolved_style,
            queries=queries,
            providers_contacted=providers_contacted,
            results=results_to_return,
            total_candidates_found=len(candidates),
            downloaded_count=0,
            fallback_reason=fallback_reason,
            visual_requirement=req_class,
            visual_type=v_type or ("EVENT" if req_class == REAL_REQUIRED else "SCENE"),
            entities=entities,
            motion_spec=None,
            source_role=s_role,
            status=status,
            search_completed=True,
            usable_results=len(usable_items),
            fallback_allowed=fallback_allowed,
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
        visual_requirement: str = "auto",
        research_intelligence: Optional[Dict[str, Any]] = None,
    ) -> MediaFinderResult:
        """
        Search for media and download the top ranked candidates to the local filesystem.
        Provenance metadata is preserved in sources.json.
        """
        result = self.find(
            request=request,
            media=media,
            era=era,
            style=style,
            count=count,
            visual_requirement=visual_requirement,
            research_intelligence=research_intelligence,
        )
        if not result.results or result.status in ("NO_BROLL", "REMOTION_REQUIRED", "INSUFFICIENT_EVIDENCE"):
            return result

        # Convert only assets with explicit reusable rights into download items.
        media_items: List[MediaItem] = []
        for r in result.results:
            r.rights_status = item_rights_status(r)
            if not is_reusable_rights_status(r.rights_status):
                r.selection_reason = (r.selection_reason + "; " if r.selection_reason else "") + f"Discovery only: rights status {r.rights_status} does not allow automatic reuse"
                continue
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
                    license_url=r.license_url,
                    rights_status=r.rights_status,
                    retrieval_query=r.query,
                    provider_capability=", ".join(r.capability),
                    selection_reason=r.selection_reason,
                    file_size_bytes=0,
                    width=r.width,
                    height=r.height,
                    metadata=r.metadata,
                    reranker_score=r.score,
                    final_rank=r.rank,
                    visual_requirement=r.visual_requirement,
                    source_role=r.source_role,
                    authenticity_score=r.authenticity_score,
                    entity_match_score=r.entity_match_score,
                    temporal_match_score=r.temporal_match_score,
                    location_match_score=r.location_match_score,
                    event_match_score=r.event_match_score,
                    source_specificity_score=r.source_specificity_score,
                    matched_entities=r.matched_entities,
                    rejection_reason=r.rejection_reason,
                    is_archival=r.is_archival,
                    is_generic=r.is_generic,
                    semantic_score=r.semantic_score,
                    contextual_score=r.contextual_score,
                    generic_penalty=r.generic_penalty,
                )
            )

        if not media_items:
            result.fallback_reason = (result.fallback_reason + " " if result.fallback_reason else "") + "No candidate had explicit reusable rights; results remain discovery-only."
            return result

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
                "style": "formal|documentary|...",
                "visual_requirement": "REAL_REQUIRED|REAL_PREFERRED|...",
                "visual_type": "...",
                "entities": [...],
                "source_role": "..."
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
        visual_requirement = microbeat.get("visual_requirement", "auto")

        if download:
            return self.find_and_download(
                request=effective_request,
                media=media,
                era=era,
                style=style,
                count=count,
                folder=folder,
                visual_requirement=visual_requirement,
            )
        return self.find(
            request=effective_request,
            media=media,
            era=era,
            style=style,
            count=count,
            visual_requirement=visual_requirement,
        )

    # --------------------------------------------------------------------------
    # Internal: Query Intelligence & Variants
    # --------------------------------------------------------------------------

    def _generate_query_intelligence(
        self,
        request: str,
        era: str,
        style: str,
        media: str = "any",
        entities: Optional[List[str]] = None,
        visual_requirement: str = "auto",
        research_intelligence: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Transform a natural language visual request into distinct query variants.
        For REAL_REQUIRED & REAL_PREFERRED: strictly preserve entities and build evidence queries.
        For GENERIC_ALLOWED: build descriptive scene and atmospheric queries.
        """
        vr = (visual_requirement or "auto").upper().strip()

        # REAL_REQUIRED and REAL_PREFERRED use evidence/context-aware expansion.
        # This also applies to human-life scenes without named entities.
        if vr in (REAL_REQUIRED, REAL_PREFERRED):
            expander = MediaQueryExpander()
            eq = expander.expand(request, media_type_override=media, visual_requirement=vr)
            candidate_queries = list(eq.all_queries)
            if era in ("historical", "past") or any(y in request for y in ("1944", "1945", "1921", "2007", "abad")):
                for ent in entities:
                    arch_q = f"{ent} archival documentation"
                    if arch_q not in candidate_queries:
                        candidate_queries.append(arch_q)
            if style == "formal":
                formal_q = f"{self._translate_to_core_english(request)}, editorial photograph"
                if formal_q not in candidate_queries:
                    candidate_queries.append(formal_q)
            unique: List[str] = []
            for q in candidate_queries:
                q_clean = " ".join(q.split())
                if q_clean and q_clean not in unique:
                    unique.append(q_clean)
            if unique:
                return self._append_research_queries(unique, research_intelligence, request)

        core_english = self._translate_to_core_english(request)

        # 1. Primary descriptive query
        if media == "video":
            if era in ("historical", "past"):
                if style == "archival":
                    primary = f"{core_english}, archival footage, historical film newsreel"
                elif style == "cinematic":
                    primary = f"{core_english}, cinematic archival footage, dramatic historical motion picture"
                elif style == "documentary":
                    primary = f"{core_english}, documentary footage, authentic recorded film"
                else:
                    primary = f"{core_english}, historical footage, authentic film recording"
            else:
                if style == "formal":
                    primary = f"{core_english}, professional corporate video footage, clean natural lighting"
                elif style == "cinematic":
                    primary = f"{core_english}, atmospheric cinematic composition, motion picture footage"
                elif style == "conceptual":
                    primary = f"{core_english}, conceptual video footage, speculative futuristic motion"
                elif style == "documentary":
                    primary = f"{core_english}, candid documentary video footage, authentic real setting"
                else:
                    primary = f"{core_english}, documentary video footage, realistic natural lighting"
        else:
            if style == "formal":
                primary = f"{core_english}, professional editorial photography, clean natural lighting"
            elif style == "archival":
                if media == "any":
                    primary = f"{core_english}, archival historical reference, authentic period visual"
                else:
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
        style_variant = self._build_style_variant(core_english, style, era, media=media)

        # 3. Contextual / environmental variant
        contextual = self._build_contextual_variant(core_english, era, media=media)

        # 4. Fallback concise query
        fallback = self._build_fallback_query(core_english, media=media)

        queries = [primary, style_variant, contextual, fallback]
        # Deduplicate while preserving order
        unique_queries: List[str] = []
        for q in queries:
            q_clean = " ".join(q.split())
            if q_clean and q_clean not in unique_queries:
                unique_queries.append(q_clean)

        return self._append_research_queries(unique_queries, research_intelligence, request)

    @staticmethod
    def _append_research_queries(
        base_queries: List[str],
        research_intelligence: Optional[Dict[str, Any]],
        request: str,
    ) -> List[str]:
        """Add bounded event/entity/place expansions from structured research."""
        if not isinstance(research_intelligence, dict):
            return base_queries
        extras = research_intelligence.get("recommended_broll_queries", [])
        if not isinstance(extras, list):
            return base_queries
        request_terms = {w for w in re.findall(r"[a-z0-9]+", request.lower()) if len(w) > 3}
        result = list(base_queries)
        for extra in extras[:5]:
            if not isinstance(extra, str) or not extra.strip():
                continue
            # Keep research-derived additions tied to this shot/topic. If there
            # is no token overlap, the request itself must appear in the query.
            extra_terms = {w for w in re.findall(r"[a-z0-9]+", extra.lower()) if len(w) > 3}
            if request_terms and not request_terms.intersection(extra_terms) and request.lower() not in extra.lower():
                continue
            clean = " ".join(extra.split())
            if clean not in result:
                result.append(clean)
            if len(result) >= 10:
                break
        return result

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
    def _build_style_variant(core: str, style: str, era: str, media: str = "any") -> str:
        """Build style-specific query adhering to visual style rules."""
        if media == "video":
            if style == "formal":
                return f"{core}, corporate workplace professional video footage, realistic neutral composition"
            if style == "archival":
                if era in ("historical", "past"):
                    return f"{core}, original film footage, wartime newsreel footage"
                return f"{core}, archival film footage, authentic recorded footage"
            if style == "documentary":
                return f"{core}, observational video footage, real ordinary environment"
            if style == "cinematic":
                return f"{core}, cinematic wide shot footage, atmospheric film framing"
            if style == "conceptual":
                return f"{core}, human-centered technology conceptual video, modern architectural space"
            # neutral
            return f"{core}, ordinary everyday environment, observational video footage"

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
    def _build_contextual_variant(core: str, era: str, media: str = "any") -> str:
        """Add human-place spatial context to the query."""
        if media == "video":
            if era in ("historical", "past"):
                return f"{core}, historical footage, city street and human dwelling"
            if era == "future":
                return f"{core}, modern architectural space, futuristic video footage"
            return f"{core}, contemporary urban and interior video footage"

        if era in ("historical", "past"):
            return f"{core}, historical city street and human dwelling"
        if era == "future":
            return f"{core}, modern architectural space and smart living environment"
        return f"{core}, contemporary urban and interior environment"

    @staticmethod
    def _build_fallback_query(core: str, media: str = "any") -> str:
        """Generate concise 3-5 keyword fallback for simple catalog indexing."""
        words = [w for w in core.split() if len(w) > 2]
        if media == "video":
            base = " ".join(words[:4])
            return f"{base} footage" if "footage" not in base else base
        return " ".join(words[:5])

    # --------------------------------------------------------------------------
    # Internal: Normalization & Detection
    # --------------------------------------------------------------------------

    @staticmethod
    def _normalize_media_type(media: str, request: str) -> str:
        m = (media or "").lower().strip()
        if m in ("photo", "image", "foto", "gambar"):
            return "photo"
        if m in ("video", "footage", "film", "rekaman"):
            return "video"
        if m in ("any", "all", "semua"):
            return "any"
        # If auto, empty, or unrecognized, detect from request
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

    def _route_providers(
        self,
        era: str,
        media: str,
        visual_requirement: str = "GENERIC_ALLOWED",
    ) -> List[MediaProvider]:
        """
        Route to providers based on visual requirement, era, and media type (Section 8):
        - REAL_REQUIRED + HISTORICAL + VIDEO: 1. Internet Archive, 2. Wikimedia Commons. Pexafy: DISABLED.
        - REAL_REQUIRED + HISTORICAL + IMAGE: 1. Wikimedia Commons, 2. Internet Archive. Pexafy: DISABLED.
        - REAL_REQUIRED + PRESENT + IMAGE: 1. Wikimedia Commons, 2. Internet Archive. Pexafy: DISABLED.
        - REAL_PREFERRED: Wikimedia, Internet Archive, Pexafy (specific real -> archival -> stock fallback).
        - GENERIC_ALLOWED: Pexafy, Wikimedia, Internet Archive.
        """
        by_name: Dict[str, MediaProvider] = {p.PROVIDER_NAME: p for p in self.providers}
        selected: List[MediaProvider] = []
        vr = (visual_requirement or "GENERIC_ALLOWED").upper().strip()

        # Prefer the machine-readable capability matrix; the legacy ordering
        # below remains a fallback for unusual/custom provider names.
        routed_names = route_provider_names(
            by_name.keys(), era=era, media_type=media, visual_requirement=vr
        )
        if vr == REAL_REQUIRED:
            routed_names = [
                name for name in routed_names
                if get_provider_capabilities(name).get("source_role") != "stock_discovery"
            ]
        routed = [by_name[name] for name in routed_names if name in by_name]
        if routed:
            return routed

        # ── REAL_REQUIRED: Pexafy is DISABLED ──
        if vr == REAL_REQUIRED:
            if media == "video":
                if "internet_archive" in by_name:
                    selected.append(by_name["internet_archive"])
                if "wikimedia" in by_name:
                    selected.append(by_name["wikimedia"])
            elif era in ("historical", "past"):
                if "wikimedia" in by_name:
                    selected.append(by_name["wikimedia"])
                if "internet_archive" in by_name:
                    selected.append(by_name["internet_archive"])
            else:
                if "wikimedia" in by_name:
                    selected.append(by_name["wikimedia"])
                if "internet_archive" in by_name:
                    selected.append(by_name["internet_archive"])
            return selected

        # ── REAL_PREFERRED: Real/archival first, semantic stock allowed ──
        if vr == REAL_PREFERRED:
            if media == "video":
                if "internet_archive" in by_name:
                    selected.append(by_name["internet_archive"])
                if "wikimedia" in by_name:
                    selected.append(by_name["wikimedia"])
            elif era in ("historical", "past"):
                if "wikimedia" in by_name:
                    selected.append(by_name["wikimedia"])
                if "internet_archive" in by_name:
                    selected.append(by_name["internet_archive"])
                if "pexafy" in by_name:
                    selected.append(by_name["pexafy"])
            else:
                if "wikimedia" in by_name:
                    selected.append(by_name["wikimedia"])
                if "pexafy" in by_name:
                    selected.append(by_name["pexafy"])
                if "internet_archive" in by_name:
                    selected.append(by_name["internet_archive"])
            return selected

        # ── GENERIC_ALLOWED or others ──
        if media == "video":
            if "internet_archive" in by_name:
                selected.append(by_name["internet_archive"])
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
            return selected

        # Photo or Any
        if era in ("historical", "past"):
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
            if "internet_archive" in by_name:
                selected.append(by_name["internet_archive"])
            if media != "video" and "pexafy" in by_name:
                selected.append(by_name["pexafy"])
        elif era == "future":
            if "pexafy" in by_name:
                selected.append(by_name["pexafy"])
            if "wikimedia" in by_name:
                selected.append(by_name["wikimedia"])
        else:
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
                    v_cnt = sum(1 for it in items if (it.media_type or "").lower() == "video")
                    img_cnt = sum(1 for it in items if (it.media_type or "").lower() == "image")
                    logger.info(
                        f"MediaFinder: Provider {provider.PROVIDER_NAME} returned {len(items)} items "
                        f"(video={v_cnt}, image={img_cnt}) for query='{q}' (requested_type='{provider_media_type}')"
                    )
                    for item in items:
                        item.retrieval_query = item.retrieval_query or q
                        profile = provider.capabilities()
                        item.provider_capability = ", ".join(profile.get("capabilities", []))
                        item.rights_status = item_rights_status(item)
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
        entities: Optional[List[str]] = None,
        visual_requirement: str = "auto",
    ) -> Tuple[List[MediaFinderItem], str]:
        """Filter by media type affinity, run MediaRanker, and format as MediaFinderItems."""
        if not candidates:
            return [], "No candidates gathered from providers."

        # Count candidate breakdown for observability
        video_count = sum(1 for c in candidates if (c.media_type or "").lower() == "video")
        image_count = sum(1 for c in candidates if (c.media_type or "").lower() == "image")

        # Filter strictly by requested media type
        filtered: List[MediaItem] = []
        for item in candidates:
            mtype = (item.media_type or "").lower()
            if media_type == "video":
                if mtype != "video":
                    continue
                # For video, ensure download_url is valid and not a directory
                if not item.download_url or item.download_url.endswith("/"):
                    continue
            elif media_type in ("photo", "image"):
                if mtype != "image":
                    continue
            else:
                # "any": keep visual media (exclude audio/document)
                if mtype in ("audio", "document"):
                    continue
            filtered.append(item)

        removed_count = len(candidates) - len(filtered)
        logger.info(
            f"MediaFinder: requested_media='{media_type}', candidates={len(candidates)} "
            f"(video={video_count}, image={image_count}), filtered_out={removed_count}, retained={len(filtered)}"
        )

        # Fallback to candidates if filter was overly restrictive in "any" mode
        if not filtered and media_type == "any":
            filtered = candidates
        elif not filtered:
            # If user wanted video but none found, or wanted photo and none found
            return [], f"No matching candidates found for media_type='{media_type}'."

        try:
            ranked, fallback_reason = self.ranker.rank(
                original_request=original_request,
                candidates=filtered,
                top_n=count * 2,
                entities=entities,
                visual_requirement=visual_requirement,
                era=era,
            )
        except TypeError:
            ranked, fallback_reason = self.ranker.rank(
                original_request=original_request,
                candidates=filtered,
                top_n=count * 2,
            )

        results: List[MediaFinderItem] = []
        for rank_idx, item in enumerate(ranked[:count], 1):
            profile = get_provider_capabilities(item.provider)
            semantic_score = item.semantic_score or item.embedding_similarity or item.reranker_score or item.keyword_score
            contextual_score = item.contextual_score or (
                0.35 * item.entity_match_score + 0.25 * item.event_match_score
                + 0.20 * item.location_match_score + 0.20 * item.temporal_match_score
            )
            rights_status = item_rights_status(item)
            reason_parts = [f"Ranked #{rank_idx} by contextual and semantic fit"]
            if item.matched_entities:
                reason_parts.append("matched entities: " + ", ".join(item.matched_entities[:4]))
            if item.event_match_score > 0.5:
                reason_parts.append("event context matched")
            if item.is_archival:
                reason_parts.append("archival source")
            reason_parts.append(f"reuse rights: {rights_status.lower()}")
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
                    license_url=item.license_url or item.metadata.get("license_url", ""),
                    rights_status=rights_status,
                    query=item.retrieval_query,
                    capability=profile.get("capabilities", []),
                    semantic_score=round(semantic_score, 4),
                    contextual_score=round(contextual_score, 4),
                    generic_penalty=item.generic_penalty,
                    selection_reason="; ".join(reason_parts),
                    local_path=None,
                    width=item.width,
                    height=item.height,
                    metadata=item.metadata,
                    visual_requirement=item.visual_requirement or visual_requirement,
                    source_role=item.source_role or ("PRIMARY_EVIDENCE" if visual_requirement == REAL_REQUIRED else "DIRECT_CONTEXT"),
                    authenticity_score=item.authenticity_score,
                    entity_match_score=item.entity_match_score,
                    temporal_match_score=item.temporal_match_score,
                    location_match_score=item.location_match_score,
                    event_match_score=item.event_match_score,
                    source_specificity_score=item.source_specificity_score,
                    matched_entities=item.matched_entities,
                    matched_event=str(item.metadata.get("matched_event", "")),
                    matched_location=str(item.metadata.get("matched_location", "")),
                    matched_time=str(item.metadata.get("matched_time", "")),
                    rejection_reason=item.rejection_reason,
                    is_archival=item.is_archival,
                    is_generic=item.is_generic,
                    human_basic_need_score=item.human_basic_need_score,
                    life_lens_score=item.life_lens_score,
                    everyday_relevance_score=item.everyday_relevance_score,
                    human_place_relevance_score=item.human_place_relevance_score,
                    human_alignment_score=item.human_alignment_score,
                    human_basic_need=item.human_basic_need,
                    life_lens=item.life_lens,
                )
            )

        return results, fallback_reason

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name.lower().strip())
        return clean[:40].strip("_") or "media_search"
