"""
engine/pipeline/video_pipeline.py
=================================
Automated batch faceless video production pipeline:

  SCRIPT
    ↓
  PARSE NARRATIVES & TIMECODES (ScriptParser)
    ↓
  VISUAL SHOT DESIGN & REQUIREMENTS (VisualRequirementsGenerator)
    ↓
  SEARCH EXISTING RETRIEVAL SYSTEM (MediaPipeline: Wikimedia + IA)
    ↓
  LOCAL EMBEDDING & RERANKING (LocalEmbeddingProvider + LocalRerankerProvider)
    ↓
  DOWNLOAD ASSETS & LOG METADATA (MediaDownloader -> sources.json)
    ↓
  GENERATE SUBTITLES (SRTGenerator -> subtitles.srt)
    ↓
  ROUGH CUT TIMELINE (TimelineData -> timeline.json)
    ↓
  KDENLIVE PROJECT EXPORT (KdenliveExporter -> Nugi_Narasi_XX.kdenlive)

Vertical 9:16 format (1080x1920, 30fps) for TikTok / YouTube Shorts.
Faceless visual essay / mini-documentary style with visual pacing and metaphor.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from engine.pipeline.kdenlive_exporter import KdenliveExporter, TimelineClip, TimelineData
from engine.pipeline.media_downloader import DownloadedFile, MediaDownloader
from engine.pipeline.media_pipeline import MediaPipeline
from engine.pipeline.script_parser import NarasiScript, ScriptParser
from engine.pipeline.srt_generator import SRTGenerator
from engine.pipeline.visual_requirements import VisualRequirementsGenerator, VisualShotRequirement
from engine.providers.media import MediaItem

logger = logging.getLogger(__name__)


@dataclass
class NarrativeProductionResult:
    """Outcome for a single produced narrative."""
    narrative_id: str
    index: int
    title: str
    output_dir: Path
    kdenlive_file: Path
    timeline_file: Path
    subtitles_file: Path
    sources_file: Path
    assets_downloaded: int
    total_shots: int
    duration_seconds: float


@dataclass
class BatchProductionReport:
    """Summary report of the entire batch video production run."""
    script_file: str
    total_narratives: int
    successful_narratives: List[NarrativeProductionResult] = field(default_factory=list)
    failed_narratives: List[str] = field(default_factory=list)

    def print_summary(self) -> None:
        print("\n" + "=" * 65)
        print("🎬 BATCH VIDEO PRODUCTION COMPLETE")
        print("=" * 65)
        print(f"Script: {self.script_file}")
        print(f"Successfully processed: {len(self.successful_narratives)} / {self.total_narratives} narratives\n")

        for res in self.successful_narratives:
            print(f"📌 [{res.narrative_id.upper()}] {res.title}")
            print(f"   Duration: {res.duration_seconds:.1f}s | Shots: {res.total_shots} | Assets: {res.assets_downloaded}")
            print(f"   📁 Output:    {res.output_dir}")
            print(f"   🎥 Kdenlive:  {res.kdenlive_file.name}")
            print(f"   ⏱️ Timeline:  {res.timeline_file.name}")
            print(f"   💬 Subtitles: {res.subtitles_file.name}")
            print(f"   📋 Sources:   {res.sources_file.name}\n")

        if self.failed_narratives:
            print(f"⚠️ Failed narratives: {', '.join(self.failed_narratives)}")
        print("=" * 65 + "\n")


class VideoPipeline:
    """
    Orchestrates the entire batch video generation pipeline from
    markdown script to finished Kdenlive project files.
    """

    def __init__(
        self,
        media_pipeline: Optional[MediaPipeline] = None,
        script_parser: Optional[ScriptParser] = None,
        visual_generator: Optional[VisualRequirementsGenerator] = None,
        kdenlive_exporter: Optional[KdenliveExporter] = None,
        srt_generator: Optional[SRTGenerator] = None,
    ):
        self.media_pipeline = media_pipeline or MediaPipeline()
        self.script_parser = script_parser or ScriptParser()
        self.visual_generator = visual_generator or VisualRequirementsGenerator()
        self.kdenlive_exporter = kdenlive_exporter or KdenliveExporter()
        self.srt_generator = srt_generator or SRTGenerator()

    def run(
        self,
        script_path: Path | str,
        output_dir: Path | str = "output",
        target_narasi: str = "all",
        dry_run: bool = False,
    ) -> BatchProductionReport:
        """
        Run batch video production for all narratives in the script file.

        Args:
            script_path: Path to narrative script (.md).
            output_dir: Root directory for output folders.
            target_narasi: 'all' or specific index/id (e.g. '1' or 'narasi-01').
            dry_run: If True, skips actual asset downloads and uses placeholders.
        """
        script_p = self._resolve_script_path(script_path)
        out_root = Path(output_dir).resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        logger.info(f"Parsing script: {script_p}")
        narratives = self.script_parser.parse_file(script_p)
        logger.info(f"Found {len(narratives)} narratives in script.")

        # Filter target narratives if requested
        if target_narasi.lower() != "all":
            filtered = []
            for n in narratives:
                if str(n.index) == target_narasi or n.id.lower() == target_narasi.lower():
                    filtered.append(n)
            narratives = filtered

        report = BatchProductionReport(
            script_file=str(script_p),
            total_narratives=len(narratives),
        )

        global_seen_urls: Set[str] = set()

        for narrative in narratives:
            try:
                result = self._process_single_narrative(
                    narrative=narrative,
                    out_root=out_root,
                    global_seen_urls=global_seen_urls,
                    dry_run=dry_run,
                )
                report.successful_narratives.append(result)
            except Exception as e:
                logger.exception(f"Error processing {narrative.id}: {e}")
                report.failed_narratives.append(f"{narrative.id} ({e})")

        return report

    def _process_single_narrative(
        self,
        narrative: NarasiScript,
        out_root: Path,
        global_seen_urls: Set[str],
        dry_run: bool = False,
    ) -> NarrativeProductionResult:
        """Process one narrative into its complete output folder."""
        narasi_dir = out_root / narrative.id
        assets_dir = narasi_dir / "assets"
        narasi_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"--- Processing [{narrative.id}] {narrative.title} ---")

        # 1. Generate subtitles
        srt_file = narasi_dir / "subtitles.srt"
        self.srt_generator.write_srt_file(srt_file, narrative.sections)

        # 2. Generate visual shot requirements
        shots = self.visual_generator.generate_shots_for_narrative(narrative)

        # 3. Retrieve and download assets for each shot
        timeline_clips: List[TimelineClip] = []
        sources_records: List[Dict[str, Any]] = []
        used_for_narasi_urls: Set[str] = set()

        # Dedicated downloader scoped to this narrative's assets folder
        downloader = MediaDownloader(base_dir=narasi_dir, timeout=12)

        for shot_idx, shot in enumerate(shots, 1):
            clip = self._produce_shot_clip(
                shot=shot,
                shot_idx=shot_idx,
                narrative=narrative,
                assets_dir=assets_dir,
                downloader=downloader,
                global_seen_urls=global_seen_urls,
                used_for_narasi_urls=used_for_narasi_urls,
                sources_records=sources_records,
                dry_run=dry_run,
            )
            timeline_clips.append(clip)

        # 4. Save sources.json
        sources_file = narasi_dir / "sources.json"
        sources_payload = {
            "narrative_id": narrative.id,
            "title": narrative.title,
            "pillar": narrative.pillar,
            "dna": narrative.dna,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_assets": len(sources_records),
            "assets": sources_records,
        }
        sources_file.write_text(json.dumps(sources_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # 5. Build TimelineData and export timeline.json
        total_frames = int(round(narrative.total_duration_seconds * 30))
        timeline_data = TimelineData(
            project_name=narrative.project_name,
            narrative_id=narrative.id,
            title=narrative.title,
            pillar=narrative.pillar,
            dna=narrative.dna,
            aspect_ratio="9:16",
            width=1080,
            height=1920,
            fps=30,
            total_duration_seconds=narrative.total_duration_seconds,
            total_frames=total_frames,
            subtitles_file="subtitles.srt",
            audio_placeholder=True,
            clips=timeline_clips,
        )
        timeline_file = narasi_dir / "timeline.json"
        self.kdenlive_exporter.export_timeline_json(timeline_file, timeline_data)

        # 6. Export Kdenlive project file
        kdenlive_filename = f"{narrative.project_name}.kdenlive"
        kdenlive_file = narasi_dir / kdenlive_filename
        self.kdenlive_exporter.export_project(kdenlive_file, timeline_data, srt_path=srt_file)

        return NarrativeProductionResult(
            narrative_id=narrative.id,
            index=narrative.index,
            title=narrative.title,
            output_dir=narasi_dir,
            kdenlive_file=kdenlive_file,
            timeline_file=timeline_file,
            subtitles_file=srt_file,
            sources_file=sources_file,
            assets_downloaded=len(sources_records),
            total_shots=len(shots),
            duration_seconds=narrative.total_duration_seconds,
        )

    def _produce_shot_clip(
        self,
        shot: VisualShotRequirement,
        shot_idx: int,
        narrative: NarasiScript,
        assets_dir: Path,
        downloader: MediaDownloader,
        global_seen_urls: Set[str],
        used_for_narasi_urls: Set[str],
        sources_records: List[Dict[str, Any]],
        dry_run: bool,
    ) -> TimelineClip:
        """Find, rank, download, and map an asset for a single shot."""
        clip_id = f"clip_{narrative.index:02d}_{shot_idx:02d}"
        chosen_candidate: Optional[MediaItem] = None
        downloaded_file: Optional[DownloadedFile] = None

        print(f"  [{shot.shot_id}] ({shot.start_seconds:.1f}s - {shot.end_seconds:.1f}s) '{shot.text_overlay}' -> {shot.search_query[:45]}...")
        if not dry_run:
            # 1. Search existing retrieval system
            try:
                search_res = self.media_pipeline.search(
                    request=shot.search_query,
                    count=5,
                    media_type=shot.preferred_media_type,
                )
                # Only accept actual visual media (image or video), exclude PDFs/documents
                valid_candidates = []
                for cand in search_res.candidates:
                    url_lower = (cand.download_url or "").lower().split("?")[0]
                    if any(url_lower.endswith(bad) for bad in [".pdf", ".xml", ".txt", ".torrent", ".sqlite", ".json", ".zip", ".tar", ".gz", ".djvu", ".epub"]):
                        continue
                    if cand.media_type in ("video", "image"):
                        valid_candidates.append(cand)

                # Filter unseen candidates, or fall back to any valid candidates
                unseen_candidates = [
                    c for c in valid_candidates
                    if (c.download_url or c.source_url) not in used_for_narasi_urls
                ]
                candidate_pool = unseen_candidates if unseen_candidates else valid_candidates

                # 2. Try downloading candidates in ranked order until one succeeds
                for cand in candidate_pool:
                    if not cand.download_url and not cand.thumbnail_url:
                        continue
                    try:
                        res = downloader._download_item(
                            item=cand,
                            folder_path=assets_dir,
                            index=shot_idx,
                        )
                        if res:
                            downloaded_file = res
                            chosen_candidate = cand
                            break
                    except Exception as e:
                        logger.warning(f"Download error for '{cand.title}': {e}")

            except Exception as e:
                logger.warning(f"Search failed for shot '{shot.search_query}': {e}")

        # 3. Handle successful download vs placeholder
        if downloaded_file:
            print(f"     ✅ Downloaded: {downloaded_file.filename} ({downloaded_file.file_size_bytes // 1024} KB)")
            cand_key = chosen_candidate.download_url or chosen_candidate.source_url
            used_for_narasi_urls.add(cand_key)
            global_seen_urls.add(cand_key)

            media_type = "video" if chosen_candidate.media_type == "video" else "image"
            local_path = str(Path(downloaded_file.local_path).resolve())

            # Log source metadata
            sources_records.append({
                "shot_id": shot.shot_id,
                "clip_id": clip_id,
                "section": shot.section_name,
                "section_type": shot.section_type,
                "timecode": f"{shot.start_seconds:.1f}s - {shot.end_seconds:.1f}s",
                "text_overlay": shot.text_overlay,
                "filename": downloaded_file.filename,
                "local_path": local_path,
                "provider": downloaded_file.provider,
                "source_url": downloaded_file.source_url,
                "download_url": downloaded_file.download_url,
                "title": downloaded_file.title,
                "creator": downloaded_file.creator,
                "date": downloaded_file.date,
                "license": downloaded_file.license,
                "retrieved_at": downloaded_file.retrieved_at,
                "relevance_scores": {
                    "embedding_similarity": downloaded_file.embedding_similarity,
                    "reranker_score": downloaded_file.reranker_score,
                    "final_rank": downloaded_file.final_rank,
                },
            })

            return TimelineClip(
                clip_id=clip_id,
                section_index=shot.section_index,
                section_name=shot.section_name,
                section_type=shot.section_type,
                start_seconds=shot.start_seconds,
                end_seconds=shot.end_seconds,
                duration_seconds=shot.duration_seconds,
                start_frame=shot.start_frame,
                end_frame=shot.end_frame,
                duration_frames=shot.duration_frames,
                media_type=media_type,
                asset_filename=downloaded_file.filename,
                asset_local_path=local_path,
                text_overlay=shot.text_overlay,
                visual_description=shot.visual_description,
                source_url=downloaded_file.source_url,
                license=downloaded_file.license,
            )

        # Fallback placeholder (elegant dark backdrop with text overlay)
        return TimelineClip(
            clip_id=clip_id,
            section_index=shot.section_index,
            section_name=shot.section_name,
            section_type=shot.section_type,
            start_seconds=shot.start_seconds,
            end_seconds=shot.end_seconds,
            duration_seconds=shot.duration_seconds,
            start_frame=shot.start_frame,
            end_frame=shot.end_frame,
            duration_frames=shot.duration_frames,
            media_type="color_placeholder",
            asset_filename="",
            asset_local_path="",
            text_overlay=shot.text_overlay,
            visual_description=shot.visual_description,
            source_url="placeholder",
            license="N/A",
        )

    def _resolve_script_path(self, script_path: Path | str) -> Path:
        """Find the script file by checking direct, cwd, and known locations."""
        p = Path(script_path)
        if p.exists():
            return p.resolve()

        # Check in current workspace
        candidate_paths = [
            Path(p.name),
            Path(f"c:/Users/Nugi/Documents/nugi-konten-kreator/{p.name}"),
            Path(f"C:/Users/Nugi/Videos/nugi-konten-kreator/{p.name}"),
            Path(f"C:/Users/Nugi/Downloads/{p.name}"),
        ]
        for cp in candidate_paths:
            if cp.exists():
                return cp.resolve()

        raise FileNotFoundError(f"Could not locate script file: {script_path}")
