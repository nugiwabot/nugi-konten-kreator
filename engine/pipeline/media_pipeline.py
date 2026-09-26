"""
engine/pipeline/media_pipeline.py
===================================
Orchestrates the full Media Retrieval Agent workflow:

  Natural Language Request
        ↓
  Query Understanding & Expansion  (MediaQueryExpander)
        ↓
  Provider Search                  (WikimediaProvider + InternetArchiveProvider)
        ↓
  Candidate Pool (merged, raw)
        ↓
  Deduplicate + Semantic Ranking   (MediaRanker)
        ↓
  Download                         (MediaDownloader)
        ↓
  sources.json                     (MediaDownloader)
        ↓
  DownloadReport / MediaSearchResult

Usage pattern:
    pipeline = MediaPipeline()
    report = pipeline.search_and_download(
        "Cari footage D-Day 1944 Normandy", count=5, folder="assets/ww2/d-day"
    )
    print(report.summary_line())
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

from engine.config import MEDIA_SEARCH_MAX_RESULTS
from engine.pipeline.media_downloader import DownloadReport, MediaDownloader
from engine.pipeline.media_query_expander import ExpandedQuery, MediaQueryExpander
from engine.pipeline.media_ranker import MediaRanker
from engine.providers.internet_archive_provider import InternetArchiveProvider
from engine.providers.media import MediaItem, MediaProvider
from engine.providers.wikimedia_provider import WikimediaProvider

logger = logging.getLogger(__name__)

_PROVIDER_TIMEOUT = 5  # seconds for connectivity check


@dataclass
class MediaSearchResult:
    """Result of a search-only run (no download)."""
    request: str
    expanded_queries: List[str]
    candidates: List[MediaItem]
    total_candidates_found: int
    embedding_used: bool
    reranker_used: bool
    fallback_reason: str = ""

    def preview_lines(self, top: int = 5) -> List[str]:
        """Return human-readable preview of top candidates."""
        lines = []
        for item in self.candidates[:top]:
            lines.append(
                f"  #{item.final_rank} [{item.provider}] [{item.media_type}] "
                f"{item.title[:70]}"
            )
            lines.append(f"      Rerank Score: {item.reranker_score:.3f} | "
                         f"Embed Sim: {item.embedding_similarity:.3f}")
            lines.append(f"      Source: {item.source_url}")
            lines.append(f"      Download: {item.download_url[:80]}...")
            lines.append("")
        return lines


class MediaPipeline:
    """
    Orchestrates the full Media Retrieval Agent workflow.

    Designed for use both from CLI and from AI agents via natural language.
    All errors are caught at provider level — the pipeline never crashes.
    """

    def __init__(
        self,
        providers: Optional[List[MediaProvider]] = None,
        ranker: Optional[MediaRanker] = None,
        downloader: Optional[MediaDownloader] = None,
        expander: Optional[MediaQueryExpander] = None,
    ):
        self.providers: List[MediaProvider] = providers or [
            WikimediaProvider(),
            InternetArchiveProvider(),
        ]
        self.ranker: MediaRanker = ranker or MediaRanker()
        self.downloader: MediaDownloader = downloader or MediaDownloader()
        self.expander: MediaQueryExpander = expander or MediaQueryExpander()

    # ------------------------------------------------------------------
    # Public: search only (no download)
    # ------------------------------------------------------------------

    def search(
        self,
        request: str,
        count: int = 10,
        media_type: Optional[str] = None,
    ) -> MediaSearchResult:
        """
        Run the full search + ranking pipeline but do NOT download anything.

        Args:
            request: Natural-language visual request.
            count: How many ranked results to return.
            media_type: "image" | "video" | "any" (auto-detected if None).

        Returns:
            MediaSearchResult with ranked candidates.
        """
        eq = self.expander.expand(request, media_type_override=media_type)
        candidates = self._gather_candidates(eq, max_per_query=max(count, 5))

        logger.info(f"MediaPipeline.search: {len(candidates)} raw candidates gathered")

        ranked, fallback_reason = self.ranker.rank(
            original_request=request,
            candidates=candidates,
            top_n=count,
        )

        emb_used = all(c.embedding_similarity != 0.0 for c in ranked[:3]) if ranked else False
        rer_used = all(c.reranker_score != 0.0 for c in ranked[:3]) if ranked else False

        return MediaSearchResult(
            request=request,
            expanded_queries=eq.all_queries,
            candidates=ranked,
            total_candidates_found=len(candidates),
            embedding_used=emb_used,
            reranker_used=rer_used,
            fallback_reason=fallback_reason,
        )

    # ------------------------------------------------------------------
    # Public: search + download
    # ------------------------------------------------------------------

    def search_and_download(
        self,
        request: str,
        count: int = 5,
        folder: str = "general",
        media_type: Optional[str] = None,
    ) -> DownloadReport:
        """
        Full pipeline: search, rank, and download.

        Args:
            request: Natural-language visual request.
            count: Number of files to download.
            folder: Destination subfolder (sanitized, relative to MEDIA_ASSETS_DIR).
            media_type: Force "image" | "video" | "any" (auto-detected if None).

        Returns:
            DownloadReport with per-file results.
        """
        result = self.search(request, count=count * 3, media_type=media_type)
        # We search for 3× more candidates than needed to give downloader
        # room to skip unavailable files.

        if not result.candidates:
            logger.warning(f"No candidates found for '{request}'")
            from engine.pipeline.media_downloader import DownloadReport
            return DownloadReport(total_attempted=0, folder=None)

        report = self.downloader.download_batch(
            items=result.candidates,
            folder=folder,
            count=count,
        )

        if result.fallback_reason:
            logger.info(f"Ranking fallback: {result.fallback_reason}")

        return report

    # ------------------------------------------------------------------
    # Public: script-to-asset mode
    # ------------------------------------------------------------------

    def search_from_script(
        self,
        script_text: str,
        folder: str = "script-assets",
        count_per_scene: int = 3,
    ) -> List[DownloadReport]:
        """
        Script-to-visual mode: extract scenes from script, search per scene.

        Args:
            script_text: Full narration / script text.
            folder: Base folder; scene sub-folders created automatically.
            count_per_scene: Files to download per detected scene.

        Returns:
            List of DownloadReport, one per detected scene.
        """
        scene_queries = self.expander.expand_script(script_text)
        if not scene_queries:
            logger.warning("Script scene extraction found no visual scenes.")
            return []

        reports: List[DownloadReport] = []
        for scene_idx, eq in enumerate(scene_queries, 1):
            scene_folder = f"{folder}/scene-{scene_idx:03d}"
            primary = eq.primary_queries[0] if eq.primary_queries else eq.original_request[:50]
            logger.info(f"Scene {scene_idx}: searching '{primary}'")

            candidates = self._gather_candidates(eq, max_per_query=MEDIA_SEARCH_MAX_RESULTS)
            if not candidates:
                logger.warning(f"No candidates for scene {scene_idx}: {primary}")
                continue

            ranked, _ = self.ranker.rank(
                original_request=eq.original_request,
                candidates=candidates,
                top_n=count_per_scene * 3,
            )

            report = self.downloader.download_batch(
                items=ranked,
                folder=scene_folder,
                count=count_per_scene,
            )
            reports.append(report)

        return reports

    # ------------------------------------------------------------------
    # Public: health check
    # ------------------------------------------------------------------

    def doctor(self) -> dict:
        """
        Check availability of all services.
        Returns dict suitable for CLI display.
        """
        status = {}

        # Provider connectivity (just check DNS resolution)
        status["wikimedia"] = self._check_url("https://commons.wikimedia.org")
        status["internet_archive"] = self._check_url("https://archive.org")

        # AI services
        ai_status = self.ranker.get_status()
        status["embedding"] = ai_status.get("embedding", "UNKNOWN")
        status["reranker"] = ai_status.get("reranker", "UNKNOWN")

        return status

    # ------------------------------------------------------------------
    # Internal: candidate gathering
    # ------------------------------------------------------------------

    def _gather_candidates(
        self,
        eq: ExpandedQuery,
        max_per_query: int = 20,
    ) -> List[MediaItem]:
        """
        Run all queries in ExpandedQuery against all providers.
        Merges results, deduplicates by dedup_key.
        """
        seen_keys: set = set()
        all_candidates: List[MediaItem] = []

        for query in eq.all_queries:
            if len(all_candidates) >= max_per_query:
                break
            for provider in self.providers:
                if len(all_candidates) >= max_per_query:
                    break
                try:
                    items = provider.search_media(
                        query=query,
                        media_type=eq.detected_media_type,
                        max_results=max_per_query,
                    )
                    for item in items:
                        key = item.dedup_key()
                        if key not in seen_keys:
                            seen_keys.add(key)
                            all_candidates.append(item)
                except Exception as e:
                    logger.warning(
                        f"Provider {provider.PROVIDER_NAME} failed for "
                        f"query='{query}': {e}"
                    )

        return all_candidates

    @staticmethod
    def _check_url(url: str, timeout: int = _PROVIDER_TIMEOUT) -> str:
        """Return 'OK' or 'OFFLINE' based on HTTP connectivity."""
        try:
            req = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "NugiContentBrain/1.0 health-check"},
            )
            with urllib.request.urlopen(req, timeout=timeout):
                return "OK"
        except Exception:
            return "OFFLINE"
