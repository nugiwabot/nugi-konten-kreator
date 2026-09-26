"""
engine/pipeline/kdenlive_exporter.py
====================================
Generates standard Kdenlive (.kdenlive) project files and timeline.json metadata.

Characteristics:
  - Valid MLT XML (version 7.41.0 compatible)
  - Vertical 9:16 profile (1080x1920, 30fps) for TikTok / YouTube Shorts
  - Main video track (ordered visual essay clips with frame-accurate durations)
  - Audio track placeholder for voice-over narration
  - Subtitle track referencing subtitles.srt via avfilter.subtitles & kdenlive properties
  - Generates companion timeline.json with full clip and timecode metadata
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)


@dataclass
class TimelineClip:
    """A media clip placed on the video timeline."""
    clip_id: str
    section_index: int
    section_name: str
    section_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    start_frame: int
    end_frame: int
    duration_frames: int
    media_type: str  # "video", "image", or "color_placeholder"
    asset_filename: str
    asset_local_path: str
    text_overlay: str = ""
    visual_description: str = ""
    source_url: str = ""
    license: str = ""


@dataclass
class TimelineData:
    """Complete rough-cut timeline data."""
    project_name: str
    narrative_id: str
    title: str
    pillar: str
    dna: str
    aspect_ratio: str = "9:16"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    total_duration_seconds: float = 75.0
    total_frames: int = 2250
    subtitles_file: str = "subtitles.srt"
    audio_placeholder: bool = True
    clips: List[TimelineClip] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "narrative_id": self.narrative_id,
            "title": self.title,
            "pillar": self.pillar,
            "dna": self.dna,
            "video_format": {
                "aspect_ratio": self.aspect_ratio,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "total_duration_seconds": self.total_duration_seconds,
                "total_frames": self.total_frames,
            },
            "subtitles": {
                "file": self.subtitles_file,
            },
            "tracks": {
                "audio_track_placeholder": {
                    "name": "Voice Over (Audio)",
                    "type": "audio",
                    "duration_seconds": self.total_duration_seconds,
                    "duration_frames": self.total_frames,
                },
                "video_track_main": {
                    "name": "Visual Essay (Video)",
                    "type": "video",
                    "total_clips": len(self.clips),
                    "clips": [asdict(c) for c in self.clips],
                },
            },
        }


class KdenliveExporter:
    """Exports timelines to .kdenlive (MLT XML) and timeline.json."""

    def __init__(self, mlt_version: str = "7.41.0"):
        self.mlt_version = mlt_version

    def generate_kdenlive_xml(
        self,
        timeline: TimelineData,
        srt_path: Optional[Path | str] = None,
    ) -> str:
        """
        Produce a valid MLT XML string representing the Kdenlive project.
        """
        root = ET.Element("mlt")
        root.set("LC_NUMERIC", "C")
        root.set("version", self.mlt_version)
        root.set("title", timeline.project_name)
        root.set("producer", "main_bin")

        # 9:16 Vertical HD Profile
        profile = ET.SubElement(root, "profile")
        profile.set("description", f"Vertical HD {timeline.width}x{timeline.height} {timeline.fps}fps")
        profile.set("width", str(timeline.width))
        profile.set("height", str(timeline.height))
        profile.set("progressive", "1")
        profile.set("sample_aspect_num", "1")
        profile.set("sample_aspect_den", "1")
        profile.set("display_aspect_num", "9")
        profile.set("display_aspect_den", "16")
        profile.set("frame_rate_num", str(timeline.fps))
        profile.set("frame_rate_den", "1")
        profile.set("colorspace", "709")

        # Producers
        bin_playlist = ET.SubElement(root, "playlist")
        bin_playlist.set("id", "main_bin")

        for idx, clip in enumerate(timeline.clips):
            prod_id = f"producer_{idx:02d}"
            producer = ET.SubElement(root, "producer")
            producer.set("id", prod_id)
            producer.set("in", "0")
            producer.set("out", str(clip.duration_frames - 1))

            len_prop = ET.SubElement(producer, "property")
            len_prop.set("name", "length")
            len_prop.text = str(clip.duration_frames)

            # Check resource path
            res_path = clip.asset_local_path.replace("\\", "/") if clip.asset_local_path else ""
            res_prop = ET.SubElement(producer, "property")
            res_prop.set("name", "resource")

            clip_name_prop = ET.SubElement(producer, "property")
            clip_name_prop.set("name", "kdenlive:clipname")
            clip_name_prop.text = clip.text_overlay or clip.asset_filename or clip.clip_id

            if clip.media_type == "image":
                res_prop.text = res_path
                eof_prop = ET.SubElement(producer, "property")
                eof_prop.set("name", "eof")
                eof_prop.text = "pause"
                aspect_prop = ET.SubElement(producer, "property")
                aspect_prop.set("name", "aspect_ratio")
                aspect_prop.text = "1"
            elif clip.media_type == "video":
                res_prop.text = res_path
            else:
                # Color placeholder (dark cinematic blue-gray)
                res_prop.text = "color:#10141d"
                svc_prop = ET.SubElement(producer, "property")
                svc_prop.set("name", "mlt_service")
                svc_prop.text = "color"

            # Add to bin
            bin_entry = ET.SubElement(bin_playlist, "entry")
            bin_entry.set("producer", prod_id)

        # Audio Track Playlist (Voice-over placeholder)
        audio_playlist = ET.SubElement(root, "playlist")
        audio_playlist.set("id", "playlist_audio")
        audio_name_prop = ET.SubElement(audio_playlist, "property")
        audio_name_prop.set("name", "kdenlive:track_name")
        audio_name_prop.text = "Voice Over (Audio)"
        audio_blank = ET.SubElement(audio_playlist, "blank")
        audio_blank.set("length", str(timeline.total_frames))

        # Main Video Track Playlist
        video_playlist = ET.SubElement(root, "playlist")
        video_playlist.set("id", "playlist_video")
        video_name_prop = ET.SubElement(video_playlist, "property")
        video_name_prop.set("name", "kdenlive:track_name")
        video_name_prop.text = "Visual Essay (Video)"

        for idx, clip in enumerate(timeline.clips):
            prod_id = f"producer_{idx:02d}"
            entry = ET.SubElement(video_playlist, "entry")
            entry.set("producer", prod_id)
            entry.set("in", "0")
            entry.set("out", str(clip.duration_frames - 1))

        # Tractor
        tractor = ET.SubElement(root, "tractor")
        tractor.set("id", "maintractor")
        tractor.set("in", "0")
        tractor.set("out", str(max(0, timeline.total_frames - 1)))

        doc_ver = ET.SubElement(tractor, "property")
        doc_ver.set("name", "kdenlive:docproperties.version")
        doc_ver.text = "1.1"

        seq_vert = ET.SubElement(tractor, "property")
        seq_vert.set("name", "kdenlive:sequenceproperties.vertical")
        seq_vert.text = "1"

        track_0_name = ET.SubElement(tractor, "property")
        track_0_name.set("name", "kdenlive:track:0")
        track_0_name.text = "Voice Over (Audio)"

        track_1_name = ET.SubElement(tractor, "property")
        track_1_name.set("name", "kdenlive:track:1")
        track_1_name.text = "Visual Essay (Video)"

        if srt_path:
            clean_srt = str(Path(srt_path).resolve()).replace("\\", "/")
            sub_prop = ET.SubElement(tractor, "property")
            sub_prop.set("name", "kdenlive:docproperties.subtitlesList")
            sub_prop.text = clean_srt

        multitrack = ET.SubElement(tractor, "multitrack")
        t_audio = ET.SubElement(multitrack, "track")
        t_audio.set("producer", "playlist_audio")
        t_audio.set("hide", "video")

        t_video = ET.SubElement(multitrack, "track")
        t_video.set("producer", "playlist_video")

        # Subtitle filter in MLT (relative to project file)
        if srt_path:
            srt_name = Path(srt_path).name
            sub_filter = ET.SubElement(tractor, "filter")
            sub_filter.set("id", "filter_subtitles")
            sub_filter.set("mlt_service", "avfilter.subtitles")
            sub_filter_filename = ET.SubElement(sub_filter, "property")
            sub_filter_filename.set("name", "av.filename")
            sub_filter_filename.text = srt_name

        # Pretty print XML
        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(raw_xml)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    def export_project(
        self,
        output_kdenlive_path: Path | str,
        timeline: TimelineData,
        srt_path: Optional[Path | str] = None,
    ) -> Path:
        """Save .kdenlive project file."""
        target = Path(output_kdenlive_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        xml_content = self.generate_kdenlive_xml(timeline, srt_path=srt_path)
        target.write_text(xml_content, encoding="utf-8")
        logger.info(f"Kdenlive project exported to: {target}")
        return target

    def export_timeline_json(
        self,
        output_json_path: Path | str,
        timeline: TimelineData,
    ) -> Path:
        """Save timeline.json metadata file."""
        target = Path(output_json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = timeline.to_dict()
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Timeline JSON exported to: {target}")
        return target
