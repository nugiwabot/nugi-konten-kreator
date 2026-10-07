"""
engine/pipeline/timeline_model.py
=================================
Unified Timeline Representation for Nugi Content Production.
Serves as the single canonical timeline model for:
  - Video production plans
  - Multi-clip B-roll placement (faceless documentaries)
  - Main footage + cutaway placement (talking head)
  - Subtitle alignment
  - Native CapCut project generation
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SubtitleCue:
    """A single subtitle line with precise time boundaries."""
    index: int
    start_seconds: float
    end_seconds: float
    text: str

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start": round(self.start_seconds, 3),
            "end": round(self.end_seconds, 3),
            "duration": round(self.duration_seconds, 3),
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubtitleCue:
        start = float(data.get("start", data.get("start_seconds", 0.0)))
        end = float(data.get("end", data.get("end_seconds", start + float(data.get("duration", 0.0)))))
        return cls(
            index=int(data.get("index", 1)),
            start_seconds=start,
            end_seconds=end,
            text=str(data.get("text", "")),
        )


@dataclass
class TimelineClip:
    """A media segment placed on a timeline track."""
    clip_id: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    shot_id: str = ""
    file_path: Optional[str] = None
    asset_title: str = ""
    media_type: str = "video"  # "video", "image", "motion_graphic", "color_placeholder"
    track: int = 0
    source_start: float = 0.0
    source_end: Optional[float] = None
    text_overlay: str = ""
    volume: float = 1.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    transform_x: float = 0.0
    transform_y: float = 0.0
    visual_requirement: str = "GENERIC_ALLOWED"
    match_score: float = 0.0

    # Backwards compatibility attributes for narrative video pipelines
    section_index: int = 0
    section_name: str = ""
    section_type: str = ""
    start_frame: int = 0
    end_frame: int = 0
    duration_frames: int = 0
    asset_filename: str = ""
    asset_local_path: str = ""
    visual_description: str = ""
    source_url: str = ""
    license: str = ""

    def __post_init__(self) -> None:
        if not self.file_path and self.asset_local_path:
            self.file_path = self.asset_local_path
        if not self.asset_local_path and self.file_path:
            self.asset_local_path = self.file_path
        if not self.shot_id and self.clip_id:
            self.shot_id = self.clip_id
        if self.start_frame == 0 and self.start_seconds > 0:
            self.start_frame = int(round(self.start_seconds * 30))
        if self.duration_frames == 0 and self.duration_seconds > 0:
            self.duration_frames = int(round(self.duration_seconds * 30))
        if self.end_frame == 0 and self.end_seconds > 0:
            self.end_frame = int(round(self.end_seconds * 30))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "shot_id": self.shot_id,
            "section_index": self.section_index,
            "section_name": self.section_name,
            "start": round(self.start_seconds, 3),
            "end": round(self.end_seconds, 3),
            "duration": round(self.duration_seconds, 3),
            "path": self.file_path or self.asset_local_path,
            "title": self.asset_title or self.asset_filename,
            "type": self.media_type,
            "track": self.track,
            "source_start": round(self.source_start, 3),
            "source_end": round(self.source_end, 3) if self.source_end is not None else None,
            "text_overlay": self.text_overlay,
            "visual_description": self.visual_description,
            "volume": self.volume,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "transform_x": self.transform_x,
            "transform_y": self.transform_y,
            "visual_requirement": self.visual_requirement,
            "match_score": round(self.match_score, 3),
            "source_url": self.source_url,
            "license": self.license,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TimelineClip:
        start = float(data.get("start", data.get("start_seconds", 0.0)))
        dur = float(data.get("duration", data.get("duration_seconds", 0.0)))
        end = float(data.get("end", data.get("end_seconds", start + dur)))
        p = data.get("path") or data.get("file_path") or data.get("asset_local_path")
        return cls(
            clip_id=str(data.get("clip_id", f"clip_{int(start * 1000)}")),
            shot_id=str(data.get("shot_id", "")),
            start_seconds=start,
            end_seconds=end,
            duration_seconds=dur if dur > 0 else max(0.1, end - start),
            file_path=p,
            asset_local_path=str(p or ""),
            asset_title=str(data.get("title", data.get("asset_title", ""))),
            asset_filename=str(data.get("asset_filename", Path(p).name if p else "")),
            media_type=str(data.get("type", data.get("media_type", "video"))),
            track=int(data.get("track", 0)),
            source_start=float(data.get("source_start", 0.0)),
            source_end=float(data["source_end"]) if data.get("source_end") is not None else None,
            text_overlay=str(data.get("text_overlay", "")),
            visual_description=str(data.get("visual_description", "")),
            section_index=int(data.get("section_index", 0)),
            section_name=str(data.get("section_name", "")),
            section_type=str(data.get("section_type", "")),
            volume=float(data.get("volume", 1.0)),
            scale_x=float(data.get("scale_x", 1.0)),
            scale_y=float(data.get("scale_y", 1.0)),
            transform_x=float(data.get("transform_x", 0.0)),
            transform_y=float(data.get("transform_y", 0.0)),
            visual_requirement=str(data.get("visual_requirement", "GENERIC_ALLOWED")),
            match_score=float(data.get("match_score", 0.0)),
            source_url=str(data.get("source_url", "")),
            license=str(data.get("license", "")),
        )


@dataclass
class MusicTrack:
    """An audio or background music track element."""
    file_path: str
    start_seconds: float = 0.0
    duration_seconds: float = 60.0
    volume: float = 0.2
    fade_in: float = 0.5
    fade_out: float = 1.0
    track: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.file_path,
            "start": round(self.start_seconds, 3),
            "duration": round(self.duration_seconds, 3),
            "volume": self.volume,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "track": self.track,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MusicTrack:
        return cls(
            file_path=str(data.get("path", data.get("file_path", ""))),
            start_seconds=float(data.get("start", data.get("start_seconds", 0.0))),
            duration_seconds=float(data.get("duration", data.get("duration_seconds", 60.0))),
            volume=float(data.get("volume", 0.2)),
            fade_in=float(data.get("fade_in", 0.5)),
            fade_out=float(data.get("fade_out", 1.0)),
            track=int(data.get("track", 0)),
        )


@dataclass
class TimelineData:
    """Complete blueprint of a video timeline ready for assembly and export."""
    project_name: str
    aspect_ratio: str = "9:16"
    width: int = 1080
    height: int = 1920
    fps: float = 30.0
    total_duration_seconds: float = 60.0
    total_frames: int = 1800
    subtitles_file: Optional[str] = "subtitles.srt"
    audio_placeholder: bool = True
    clips: List[TimelineClip] = field(default_factory=list)
    music: List[MusicTrack] = field(default_factory=list)
    subtitles: List[SubtitleCue] = field(default_factory=list)
    narrative_id: str = ""
    title: str = ""
    pillar: str = ""
    dna: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "narrative_id": self.narrative_id,
            "title": self.title,
            "pillar": self.pillar,
            "dna": self.dna,
            "canvas": {
                "aspect_ratio": self.aspect_ratio,
                "width": self.width,
                "height": self.height,
                "fps": self.fps,
                "total_duration_seconds": round(self.total_duration_seconds, 3),
                "total_frames": self.total_frames,
            },
            "subtitles_file": self.subtitles_file,
            "audio_placeholder": self.audio_placeholder,
            "clips": [c.to_dict() for c in self.clips],
            "music": [m.to_dict() for m in self.music],
            "subtitles": [s.to_dict() for s in self.subtitles],
        }

    def save(self, output_path: Path | str) -> Path:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    @classmethod
    def load(cls, file_path: Path | str) -> TimelineData:
        p = Path(file_path).resolve()
        data = json.loads(p.read_text(encoding="utf-8"))
        canvas = data.get("canvas", {})
        return cls(
            project_name=data.get("project_name", p.stem),
            narrative_id=data.get("narrative_id", ""),
            title=data.get("title", ""),
            pillar=data.get("pillar", ""),
            dna=data.get("dna", ""),
            aspect_ratio=canvas.get("aspect_ratio", data.get("aspect_ratio", "9:16")),
            width=int(canvas.get("width", data.get("width", 1080))),
            height=int(canvas.get("height", data.get("height", 1920))),
            fps=float(canvas.get("fps", data.get("fps", 30.0))),
            total_duration_seconds=float(canvas.get("total_duration_seconds", data.get("total_duration_seconds", 60.0))),
            total_frames=int(canvas.get("total_frames", data.get("total_frames", 1800))),
            subtitles_file=data.get("subtitles_file", "subtitles.srt"),
            audio_placeholder=bool(data.get("audio_placeholder", True)),
            clips=[TimelineClip.from_dict(c) for c in data.get("clips", [])],
            music=[MusicTrack.from_dict(m) for m in data.get("music", [])],
            subtitles=[SubtitleCue.from_dict(s) for s in data.get("subtitles", [])],
        )
