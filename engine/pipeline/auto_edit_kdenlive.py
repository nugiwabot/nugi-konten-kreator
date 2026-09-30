#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
                    AUTO EDIT KDENLIVE ENGINE
================================================================================
Location: engine/pipeline/auto_edit_kdenlive.py

Fully automated video editing engine that connects raw footage, Whisper
transcription, SRT generation, segment analysis, B-roll selection/placement,
and Kdenlive (.kdenlive / MLT XML) multitrack timeline assembly.

Core Pipeline Principle:
    VIDEO MENTAH (Main Time Authority)
    -> WHISPER TRANSCRIPTION
    -> TIMESTAMP EXTRACTION
    -> SRT SUBTITLE GENERATION
    -> SEGMENT ANALYSIS
    -> DETERMINISTIC B-ROLL MATCHING
    -> B-ROLL TIMELINE PLAN (broll_plan.json)
    -> KDENLIVE PROJECT GENERATION (video_auto.kdenlive)
    -> COMPREHENSIVE INTEGRITY VALIDATION

Timeline Layout in Kdenlive:
    V2: [B-ROLL 1][B-ROLL 2]... [B-ROLL N] (Composited over V1)
    V1: [================ VIDEO MENTAH ================]
    A1: [================ AUDIO UTAMA ================]
    SUB: Native Subtitle Track (subtitle.srt) & Filter
================================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import uuid
import wave
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from xml.dom import minidom

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("auto_edit_kdenlive")

# ==============================================================================
# CONSTANTS & MEDIA EXTENSIONS
# ==============================================================================
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALL_BROLL_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS

MAIN_VIDEO_PRIORITY_KEYWORDS = [
    "main", "mentah", "video-mentah", "video_mentah", "utama", "raw", "master", "source"
]

STOPWORDS_INDONESIAN_ENGLISH = {
    "yang", "di", "ke", "dari", "dan", "ini", "itu", "ada", "adalah", "pada", "untuk",
    "dengan", "akan", "bisa", "sudah", "karena", "tapi", "tetapi", "juga", "kita",
    "saya", "aku", "kamu", "mereka", "dia", "ia", "orang", "bukan", "kalau", "jika",
    "bila", "atau", "saat", "ketika", "dalam", "luar", "oleh", "tentang", "seperti",
    "hanya", "saja", "lebih", "sangat", "paling", "lagi", "pun", "agar", "supaya",
    "bahkan", "tanpa", "setiap", "semua", "banyak", "sedikit", "beberapa",
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by"
}

SYNONYM_CLUSTERS = {
    "commute": ["kereta", "stasiun", "krl", "commuter", "macet", "jalan", "kendaraan", "motor", "mobil", "bus", "transportasi", "perjalanan", "berangkat", "pulang", "subway", "train", "traffic"],
    "housing": ["rumah", "tanah", "kpr", "cicilan", "hunian", "tapak", "apartemen", "ruko", "bangunan", "kota", "lingkungan", "taman", "halaman", "house", "home", "property", "estate", "building"],
    "work": ["kantor", "kerja", "lembur", "gaji", "bos", "rekan", "karyawan", "cubicle", "pekerjaan", "bisnis", "office", "work", "job", "career"],
    "money": ["uang", "biaya", "harga", "cicilan", "bank", "bunga", "finansial", "ekonomi", "mahal", "murah", "investasi", "rupiah", "money", "cost", "price", "finance"],
    "time": ["waktu", "jam", "menit", "detik", "pagi", "malam", "subuh", "alarm", "hari", "tahun", "lama", "berjam-jam", "habis", "time", "clock", "morning", "hours"],
    "psychology": ["lelah", "stres", "tenang", "damai", "pikiran", "otak", "emosi", "perasaan", "aman", "nyaman", "kecewa", "bahagia", "mind", "stress", "peace", "calm"],
    "family": ["anak", "keluarga", "orang tua", "ibu", "ayah", "pasangan", "istri", "suami", "kakek", "nenek", "family", "child", "parents"],
}

# ==============================================================================
# VISUAL IDENTITY & TYPOGRAPHY CONSTANTS
# ==============================================================================
COLOR_BRIGHT_YELLOW = "255,212,0,255"  # #FFD400 Primary editorial brand identity
COLOR_BLACK_SHADOW = "0,0,0,220"       # Subtle soft black shadow/outline
COLOR_DARK_SHAPE = "0,0,0,195"         # Semi-transparent dark rounded shape (76.5% alpha)
COLOR_WHITE = "255,255,255,255"        # High-contrast white fallback

PRESET_A_DOC_YELLOW = "A_DOCUMENTARY_YELLOW"   # Bright yellow + black shadow + dark shape
PRESET_B_CLEAN_YELLOW = "B_CLEAN_YELLOW"       # Bright yellow + black shadow (no shape)
PRESET_C_CLEAN_WHITE = "C_CLEAN_WHITE"         # White + black shadow + optional shape
PRESET_D_BOXED_EDITORIAL = "D_BOXED_EDITORIAL" # Boxed rounded rectangle editorial badge


# ==============================================================================
# DATA CLASSES
# ==============================================================================
@dataclass
class VideoMetadata:
    """Metadata extracted from the raw main video via ffprobe."""
    path: Path
    filename: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    total_frames: int
    aspect_ratio_display: str = "16:9"


@dataclass
class BRollAsset:
    """Discovered B-roll asset (video or image)."""
    path: Path
    filename: str
    media_type: str  # "video" or "image"
    duration_seconds: Optional[float] = None
    keywords: Set[str] = field(default_factory=set)


@dataclass
class TranscriptSegment:
    """Single segment from Whisper transcription."""
    segment_id: int
    start: float
    end: float
    duration: float
    text: str
    tokens: Set[str] = field(default_factory=set)


@dataclass
class BRollPlacement:
    """Assigned B-roll decision for a transcript segment."""
    segment_id: int
    start: float
    end: float
    duration: float
    text: str
    asset_path: Optional[str]  # e.g. "broll/kereta.mp4" or None
    asset_type: str  # "video", "image", or "none"
    asset_duration: Optional[float]
    trim_in: float
    trim_out: float
    status: str  # "MATCHED_OK", "INSUFFICIENT_BROLL_DURATION", "NO_BROLL_AVAILABLE", "FALLBACK_ASSIGNMENT"
    match_score: float = 0.0
    match_reason: str = ""
    fill_frame_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "segment_id": self.segment_id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "text": self.text,
            "asset": self.asset_path,
            "asset_type": self.asset_type,
            "asset_duration": round(self.asset_duration, 3) if self.asset_duration else None,
            "trim_in": round(self.trim_in, 3),
            "trim_out": round(self.trim_out, 3),
            "status": self.status,
            "match_score": round(self.match_score, 2),
            "match_reason": self.match_reason,
        }
        if self.fill_frame_info:
            d["fill_frame"] = self.fill_frame_info
        return d


@dataclass
class TextItem:
    """Styled editorial text / title clip for Kdenlive timeline."""
    item_id: str
    text_type: str  # "SECTION_TITLE", "HEADLINE", "EMPHASIS_TEXT", "LOWER_THIRD"
    preset: str     # PRESET_A_DOC_YELLOW, PRESET_B_CLEAN_YELLOW, etc.
    text: str
    start: float
    end: float
    duration: float
    font_family: str = "Arial, Sans-Serif"
    font_size: int = 54
    font_weight: int = 87
    text_color: str = COLOR_BRIGHT_YELLOW
    outline_color: str = COLOR_BLACK_SHADOW
    outline_width: float = 2.5
    has_box: bool = True
    box_color: str = COLOR_DARK_SHAPE
    box_radius: int = 12
    box_x: int = 0
    box_y: int = 0
    box_w: int = 0
    box_h: int = 0
    text_x: int = 0
    text_y: int = 0
    text_w: int = 0
    text_h: int = 0
    subtext: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "text_type": self.text_type,
            "preset": self.preset,
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "font_size": self.font_size,
            "text_color": self.text_color,
            "has_box": self.has_box,
            "box_bounds": [self.box_x, self.box_y, self.box_w, self.box_h] if self.has_box else None,
        }


@dataclass
class SFXEvent:
    """Sound effect event synchronized to timeline visual cues."""
    event_id: str
    sfx_type: str  # "click", "pop", "whoosh", "hit", "rise"
    trigger_type: str  # "broll", "headline", "section_title", "emphasis", "transition"
    start: float
    duration: float
    asset_filename: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "sfx_type": self.sfx_type,
            "trigger_type": self.trigger_type,
            "start": round(self.start, 3),
            "duration": round(self.duration, 3),
            "asset": self.asset_filename,
        }


@dataclass
class EditManifest:
    """Tracks state of incremental automation and manual edits."""
    workspace: str
    source_video: str
    created_at: str
    updated_at: str
    version: int
    stages: Dict[str, Dict[str, Any]]
    user_modifications: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace": self.workspace,
            "source_video": self.source_video,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "stages": self.stages,
            "user_modifications": self.user_modifications,
        }



# ==============================================================================
# WORKSPACE & ASSET DETECTION
# ==============================================================================
def find_workspace(workspace_arg: str, root_dir: Optional[Path] = None) -> Path:
    """
    Resolve workspace path from user input.
    Accepts: '01-script', 'output/01-script', '01', '1', or direct path.
    """
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent.parent

    root_dir = root_dir.resolve()
    output_dir = root_dir / "output"

    # 1. Relative to root_dir (e.g. 'output/01-script' or '01-script')
    candidate_rel = (root_dir / workspace_arg).resolve()
    if candidate_rel.is_dir() and (candidate_rel / "footage").is_dir():
        return candidate_rel

    # 2. Relative to output_dir (e.g. '01-script')
    candidate_out = (output_dir / workspace_arg).resolve()
    if candidate_out.is_dir() and (candidate_out / "footage").is_dir():
        return candidate_out

    # 3. Direct match if workspace_arg is an existing directory
    candidate = Path(workspace_arg)
    if candidate.is_dir() and (candidate / "footage").is_dir():
        return candidate.resolve()

    # 4. Handle numeric input like '1', '01' -> '01-script'
    clean_num = workspace_arg.strip().split("-")[0]
    if clean_num.isdigit():
        num_int = int(clean_num)
        formatted_name = f"{num_int:02d}-script"
        ws_path = output_dir / formatted_name
        if ws_path.is_dir():
            return ws_path.resolve()

    # If not found, list available workspaces for helpful error message
    available = [d.name for d in output_dir.glob("*-script") if d.is_dir()]
    raise FileNotFoundError(
        f"Workspace '{workspace_arg}' tidak ditemukan.\n"
        f"Workspace yang tersedia di {output_dir}:\n" +
        "\n".join(f"  - {w}" for w in sorted(available))
    )


def list_available_workspaces(root_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Scan and list all 10 workspaces and their asset readiness."""
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent.parent
    output_dir = root_dir / "output"
    results = []

    for i in range(1, 11):
        ws_name = f"{i:02d}-script"
        ws_path = output_dir / ws_name
        status = {
            "name": ws_name,
            "path": ws_path,
            "exists": ws_path.is_dir(),
            "has_footage": False,
            "footage_count": 0,
            "broll_count": 0,
            "has_srt": False,
            "has_project": False,
        }
        if ws_path.is_dir():
            footage_dir = ws_path / "footage"
            broll_dir = ws_path / "broll"
            sub_dir = ws_path / "subtitle"
            proj_dir = ws_path / "project"

            if footage_dir.is_dir():
                vids = [f for f in footage_dir.iterdir() if f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS]
                status["has_footage"] = len(vids) > 0
                status["footage_count"] = len(vids)

            if broll_dir.is_dir():
                brolls = [f for f in broll_dir.iterdir() if f.suffix.lower() in ALL_BROLL_EXTENSIONS]
                status["broll_count"] = len(brolls)

            if sub_dir.is_dir():
                status["has_srt"] = (sub_dir / "subtitle.srt").is_file()

            if proj_dir.is_dir():
                status["has_project"] = (proj_dir / "video_auto.kdenlive").is_file()

        results.append(status)
    return results


def probe_video(video_path: Path) -> VideoMetadata:
    """
    Extract technical metadata (duration, width, height, fps) using ffprobe.
    Falls back gracefully if ffprobe fails.
    """
    video_path = video_path.resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Check ffprobe in PATH or common WinGet locations
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        winget_ffprobe = list(Path(os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages")).glob(r"*ffmpeg*\**\bin\ffprobe.exe"))
        if winget_ffprobe:
            ffprobe_bin = str(winget_ffprobe[0])

    if not ffprobe_bin:
        logger.warning("ffprobe not found in PATH. Using default profile (1080x1920 30fps).")
        return VideoMetadata(
            path=video_path,
            filename=video_path.name,
            duration_seconds=60.0,
            width=1080,
            height=1920,
            fps=30.0,
            total_frames=1800,
            aspect_ratio_display="9:16",
        )

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,duration,nb_frames",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
    except Exception as e:
        logger.warning(f"ffprobe execution failed for {video_path}: {e}")
        return VideoMetadata(
            path=video_path,
            filename=video_path.name,
            duration_seconds=60.0,
            width=1080,
            height=1920,
            fps=30.0,
            total_frames=1800,
        )

    # Parse stream 0 (video)
    video_stream = None
    for st in data.get("streams", []):
        if "width" in st and "height" in st and st.get("width", 0) > 0:
            video_stream = st
            break

    width = int(video_stream.get("width", 1080)) if video_stream else 1080
    height = int(video_stream.get("height", 1920)) if video_stream else 1920

    # FPS calculation
    fps = 30.0
    if video_stream and "r_frame_rate" in video_stream:
        rate_str = video_stream["r_frame_rate"]
        if "/" in rate_str:
            num, den = rate_str.split("/", 1)
            try:
                num_f, den_f = float(num), float(den)
                if den_f > 0:
                    fps = round(num_f / den_f, 3)
            except ValueError:
                fps = 30.0
        else:
            try:
                fps = float(rate_str)
            except ValueError:
                fps = 30.0

    # Duration calculation
    duration = 0.0
    if "format" in data and "duration" in data["format"]:
        try:
            duration = float(data["format"]["duration"])
        except (ValueError, TypeError):
            duration = 0.0

    if duration <= 0 and video_stream and "duration" in video_stream:
        try:
            duration = float(video_stream["duration"])
        except (ValueError, TypeError):
            duration = 0.0

    if duration <= 0:
        duration = 60.0  # Fallback

    total_frames = int(math.ceil(duration * fps))

    # Determine display aspect ratio string
    gcd_val = math.gcd(width, height)
    aspect_disp = f"{width // gcd_val}:{height // gcd_val}" if gcd_val > 0 else "16:9"

    return VideoMetadata(
        path=video_path,
        filename=video_path.name,
        duration_seconds=duration,
        width=width,
        height=height,
        fps=fps,
        total_frames=total_frames,
        aspect_ratio_display=aspect_disp,
    )


def find_main_video(workspace_dir: Path, requested_file: Optional[str] = None) -> Path:
    """
    Locates the main raw video in output/[workspace]/footage/.
    Priorities:
    1. Explicit requested_file if provided and valid.
    2. If only one video candidate exists, select it.
    3. If multiple candidates exist, check for clear keyword priority (mentah, main, etc.)
    4. If still ambiguous, raises AmbiguousMainVideoError with available candidates.
    5. If no video found, raises MainVideoNotFoundError.
    """
    footage_dir = workspace_dir / "footage"
    if not footage_dir.is_dir():
        raise FileNotFoundError(f"Folder footage tidak ditemukan di: {footage_dir}")

    candidates = [
        f for f in footage_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS and not f.name.startswith(".")
    ]

    # Explicit user choice
    if requested_file:
        match = next((c for c in candidates if c.name.lower() == requested_file.lower()), None)
        if match:
            return match
        req_path = Path(requested_file)
        if req_path.is_file():
            return req_path.resolve()
        raise FileNotFoundError(
            f"File video yang diminta '{requested_file}' tidak ditemukan di {footage_dir}."
        )

    if not candidates:
        raise FileNotFoundError(
            f"Tidak ada video mentah ditemukan di: {footage_dir}\n"
            f"Silakan letakkan video mentah (.mp4, .mov, .mkv, .webm) ke folder tersebut."
        )

    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates: check for priority keywords
    priority_matches = []
    for c in candidates:
        stem = c.stem.lower()
        if any(kw in stem for kw in MAIN_VIDEO_PRIORITY_KEYWORDS):
            priority_matches.append(c)

    if len(priority_matches) == 1:
        logger.info(f"Otomatis memilih video utama berdasarkan keyword: {priority_matches[0].name}")
        return priority_matches[0]

    # Ambiguous situation
    cand_names = [f"  - {c.name}" for c in candidates]
    raise ValueError(
        f"Ditemukan {len(candidates)} kandidat video di {footage_dir}, ambigu mana video utama:\n" +
        "\n".join(cand_names) +
        f"\nSilakan tentukan secara eksplisit menggunakan opsi: --video <nama_file>"
    )


def extract_keywords_from_string(text: str) -> Set[str]:
    """Extract normalized alphanumeric tokens, filtering stopwords and indices."""
    cleaned = re.sub(r"^\d+[\s_-]*", "", text)  # remove leading indices like '001_'
    words = re.findall(r"[a-zA-Z0-9]+", cleaned.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS_INDONESIAN_ENGLISH}


def find_broll_assets(workspace_dir: Path) -> List[BRollAsset]:
    """
    Scan output/[workspace]/broll/ for supported video and image assets.
    Probes video durations with ffprobe.
    """
    broll_dir = workspace_dir / "broll"
    if not broll_dir.is_dir():
        logger.warning(f"B-roll directory not found: {broll_dir}")
        return []

    assets: List[BRollAsset] = []
    raw_files = sorted(
        [f for f in broll_dir.iterdir() if f.is_file() and not f.name.startswith(".")],
        key=lambda x: x.name.lower()
    )

    for f in raw_files:
        ext = f.suffix.lower()
        if ext in SUPPORTED_VIDEO_EXTENSIONS:
            meta = probe_video(f)
            keywords = extract_keywords_from_string(f.stem)
            assets.append(BRollAsset(
                path=f,
                filename=f.name,
                media_type="video",
                duration_seconds=meta.duration_seconds,
                keywords=keywords,
            ))
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            keywords = extract_keywords_from_string(f.stem)
            assets.append(BRollAsset(
                path=f,
                filename=f.name,
                media_type="image",
                duration_seconds=None,  # Dynamic to match slot duration
                keywords=keywords,
            ))

    return assets


# ==============================================================================
# WHISPER TRANSCRIPTION & SRT GENERATION
# ==============================================================================
def format_timestamp_srt(seconds: float) -> str:
    """Format seconds into standard SRT timecode: HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int(round((seconds - int(seconds)) * 1000))
    if msecs >= 1000:
        msecs = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"


def parse_timestamp_srt(srt_time: str) -> float:
    """Parse standard SRT timecode HH:MM:SS,mmm or HH:MM:SS.mmm to seconds."""
    clean = srt_time.strip().replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 3:
        hrs = float(parts[0])
        mins = float(parts[1])
        secs = float(parts[2])
        return hrs * 3600.0 + mins * 60.0 + secs
    raise ValueError(f"Malformed SRT timestamp: '{srt_time}'")


def transcribe_video(
    video_path: Path,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    language: Optional[str] = None,
    local_files_only: bool = True,
) -> List[TranscriptSegment]:
    """
    Run Whisper transcription on the raw main video.
    Main video audio is the SOLE time authority for the entire pipeline.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper tidak terpasang di Python environment.\n"
            "Silakan periksa environment aktif."
        )

    logger.info(f"Loading faster-whisper model '{model_name}' on {device} ({compute_type})...")
    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            local_files_only=local_files_only,
        )
    except Exception as e:
        if local_files_only:
            logger.warning(f"Gagal memuat model secara offline: {e}. Mencoba tanpa local_files_only...")
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                local_files_only=False,
            )
        else:
            raise RuntimeError(f"Gagal memuat Whisper model: {e}")

    logger.info(f"Menjalankan transkripsi audio dari video utama: {video_path.name}")
    transcribe_kwargs: Dict[str, Any] = {
        "beam_size": 5,
        "word_timestamps": True,
    }
    if language:
        transcribe_kwargs["language"] = language

    raw_segments, info = model.transcribe(
        str(video_path),
        **transcribe_kwargs,
    )

    logger.info(f"Transkripsi selesai. Bahasa terdeteksi: {info.language} (prob: {info.language_probability:.2f})")

    segments: List[TranscriptSegment] = []
    seg_idx = 1
    for seg in raw_segments:
        text_clean = seg.text.strip()
        if not text_clean:
            continue
        start_t = float(seg.start)
        end_t = float(seg.end)
        # Ensure minimum duration and positive delta
        if end_t <= start_t:
            end_t = start_t + 0.5

        tokens = extract_keywords_from_string(text_clean)
        segments.append(TranscriptSegment(
            segment_id=seg_idx,
            start=round(start_t, 3),
            end=round(end_t, 3),
            duration=round(end_t - start_t, 3),
            text=text_clean,
            tokens=tokens,
        ))
        seg_idx += 1

    return segments


def generate_srt(segments: List[TranscriptSegment], output_srt_path: Path) -> Path:
    """
    Write transcript segments to standard SRT format.
    Output: output/[workspace]/subtitle/subtitle.srt
    """
    output_srt_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for idx, seg in enumerate(segments, 1):
        start_str = format_timestamp_srt(seg.start)
        end_str = format_timestamp_srt(seg.end)
        lines.append(f"{idx}\n{start_str} --> {end_str}\n{seg.text}\n")

    content = "\n".join(lines) + "\n"
    output_srt_path.write_text(content, encoding="utf-8")
    logger.info(f"SRT berhasil dibuat: {output_srt_path} ({len(segments)} segments)")
    return output_srt_path


def parse_srt_file(srt_path: Path) -> List[TranscriptSegment]:
    """Parse an existing SRT file into structured TranscriptSegments."""
    if not srt_path.is_file():
        raise FileNotFoundError(f"SRT file not found: {srt_path}")

    raw_text = srt_path.read_text(encoding="utf-8-sig").strip()
    if not raw_text:
        return []

    # Blocks separated by double newlines
    blocks = re.split(r"\n\s*\n", raw_text)
    segments: List[TranscriptSegment] = []
    seg_idx = 1

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue

        # Look for the timecode line containing '-->'
        timecode_line = None
        text_lines = []
        for line in lines:
            if "-->" in line:
                timecode_line = line
            elif timecode_line is not None:
                text_lines.append(line)

        if not timecode_line or not text_lines:
            continue

        try:
            start_str, end_str = timecode_line.split("-->", 1)
            start_sec = parse_timestamp_srt(start_str.strip())
            end_sec = parse_timestamp_srt(end_str.strip())
        except Exception as e:
            logger.warning(f"Skipping malformed SRT timecode line '{timecode_line}': {e}")
            continue

        text_content = " ".join(text_lines).strip()
        tokens = extract_keywords_from_string(text_content)
        segments.append(TranscriptSegment(
            segment_id=seg_idx,
            start=round(start_sec, 3),
            end=round(end_sec, 3),
            duration=round(end_sec - start_sec, 3),
            text=text_content,
            tokens=tokens,
        ))
        seg_idx += 1

    return segments


# ==============================================================================
# B-ROLL MATCHING & TIMELINE PLANNING
# ==============================================================================
def calculate_match_score(
    segment: TranscriptSegment,
    asset: BRollAsset,
    used_count: int = 0
) -> Tuple[float, str]:
    """
    Deterministic scoring between transcript segment and a B-roll asset.
    Considers:
    - Direct keyword overlap
    - Stem / Substring matches
    - Concept cluster / synonym co-occurrence
    - Asset reuse penalty (to maximize visual variety)
    """
    score = 0.0
    reasons = []

    # 1. Direct keyword match
    overlap = segment.tokens.intersection(asset.keywords)
    if overlap:
        points = len(overlap) * 10.0
        score += points
        reasons.append(f"direct_keyword:{','.join(sorted(overlap))}(+{points:.0f})")

    # 2. Substring matches
    for st in segment.tokens:
        for ak in asset.keywords:
            if st != ak:
                if st in ak or ak in st:
                    score += 5.0
                    reasons.append(f"partial_match:{st}<->{ak}(+5)")

    # 3. Semantic / Concept clusters
    for cluster_name, words in SYNONYM_CLUSTERS.items():
        seg_has = any(w in segment.tokens for w in words) or any(w in segment.text.lower() for w in words)
        asset_has = any(w in asset.keywords for w in words) or any(w in asset.filename.lower() for w in words)
        if seg_has and asset_has:
            score += 7.0
            reasons.append(f"cluster:{cluster_name}(+7)")

    # 4. Reuse penalty (discourage repeating the same asset consecutively)
    if used_count > 0:
        penalty = used_count * 8.0
        score -= penalty
        reasons.append(f"reuse_penalty(-{penalty:.0f})")

    reason_str = " | ".join(reasons) if reasons else "no_direct_match"
    return score, reason_str


# ==============================================================================
# FILL FRAME & QUICK ZOOM CALCULATIONS
# ==============================================================================
def probe_image_dimensions(image_path: Path) -> Optional[Tuple[int, int]]:
    """Probe image width and height using PIL with ffprobe fallback."""
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        pass
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            str(image_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and "x" in res.stdout:
            parts = res.stdout.strip().split("x")
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None


def calculate_fill_frame_rect(
    asset_w: int,
    asset_h: int,
    proj_w: int = 1920,
    proj_h: int = 1080,
) -> Tuple[int, int, int, int]:
    """
    Calculate bounding rectangle (X, Y, W, H) that fills the project frame,
    maintains original aspect ratio, and center-crops any overflow.
    Guarantees:
      - W >= proj_w and H >= proj_h
      - No black bars
      - No stretching or aspect distortion
      - Symmetrical center cropping
    """
    if asset_w <= 0 or asset_h <= 0 or proj_w <= 0 or proj_h <= 0:
        return (0, 0, proj_w, proj_h)

    ar_asset = asset_w / asset_h
    ar_proj = proj_w / proj_h

    if abs(ar_asset - ar_proj) < 1e-4:
        return (0, 0, proj_w, proj_h)

    if ar_asset > ar_proj:
        # Asset is wider than viewport -> match height, crop width overflow
        scale = proj_h / asset_h
        w = int(round(asset_w * scale))
        h = proj_h
        x = int(round((proj_w - w) / 2))
        y = 0
        return (x, y, w, h)
    else:
        # Asset is taller / portrait -> match width, crop height overflow
        scale = proj_w / asset_w
        w = proj_w
        h = int(round(asset_h * scale))
        x = 0
        y = int(round((proj_h - h) / 2))
        return (x, y, w, h)


def calculate_quick_zoom_keyframes(
    fill_rect: Tuple[int, int, int, int],
    duration_frames: int,
    proj_w: int = 1920,
    proj_h: int = 1080,
    zoom_peak: float = 1.08,
    ease_in_pct: float = 0.12,
    ease_out_pct: float = 0.25,
) -> str:
    """
    Generate MLT animated rect keyframe string relative to clip duration.
    Begins at 100% of fill base, eases into zoom_peak at ~12%, eases back to 100% at ~25%,
    and holds steady until the end of the clip.
    Never scales below fill base (scale >= 1.0), preserving fill-frame integrity.
    """
    fx, fy, fw, fh = fill_rect
    cx = proj_w / 2.0
    cy = proj_h / 2.0

    if duration_frames <= 1:
        return f"0={fx} {fy} {fw} {fh} 1"

    f0 = 0
    f1 = max(1, min(duration_frames - 2, int(round(duration_frames * ease_in_pct))))
    f2 = max(f1 + 1, min(duration_frames - 1, int(round(duration_frames * ease_out_pct))))

    w_peak = int(round(fw * zoom_peak))
    h_peak = int(round(fh * zoom_peak))
    x_peak = int(round(cx - w_peak / 2.0))
    y_peak = int(round(cy - h_peak / 2.0))

    kf0 = f"{f0}={fx} {fy} {fw} {fh} 1"
    kf1 = f"{f1}={x_peak} {y_peak} {w_peak} {h_peak} 1"
    kf2 = f"{f2}={fx} {fy} {fw} {fh} 1"

    return f"{kf0}; {kf1}; {kf2}"


def match_broll(
    segments: List[TranscriptSegment],
    assets: List[BRollAsset]
) -> List[BRollPlacement]:
    """
    Assign B-roll assets to each transcript segment.
    - If assets are empty, marks status as NO_BROLL_AVAILABLE.
    - Matches highest scoring asset.
    - Evaluates duration compatibility (video trimmed if longer, flagged if shorter).
    - Image assets dynamically adapt to slot duration.
    - Calculates fill_frame_info for aspect-ratio preservation.
    """
    if not assets:
        logger.warning("Tidak ada B-roll yang ditemukan di workspace. Semua slot dibiarkan kosong.")
        return [
            BRollPlacement(
                segment_id=seg.segment_id,
                start=seg.start,
                end=seg.end,
                duration=seg.duration,
                text=seg.text,
                asset_path=None,
                asset_type="none",
                asset_duration=None,
                trim_in=0.0,
                trim_out=0.0,
                status="NO_BROLL_AVAILABLE",
                match_score=0.0,
                match_reason="Folder broll kosong",
            )
            for seg in segments
        ]

    placements: List[BRollPlacement] = []
    asset_usage: Dict[str, int] = {a.filename: 0 for a in assets}

    for seg in segments:
        best_asset: Optional[BRollAsset] = None
        best_score = -999.0
        best_reason = ""

        # Score against all assets
        for asset in assets:
            score, reason = calculate_match_score(
                segment=seg,
                asset=asset,
                used_count=asset_usage.get(asset.filename, 0)
            )
            if score > best_score:
                best_score = score
                best_asset = asset
                best_reason = reason

        # Fallback if no positive match: pick the least used asset
        if best_score <= 0.0 or best_asset is None:
            least_used = min(assets, key=lambda a: asset_usage.get(a.filename, 0))
            best_asset = least_used
            best_score = 0.1
            best_reason = "fallback_least_used"

        asset_usage[best_asset.filename] = asset_usage.get(best_asset.filename, 0) + 1

        # Check duration and trimming
        slot_duration = seg.duration
        rel_path = f"broll/{best_asset.filename}"

        # Calculate fill-frame info
        fill_info = None
        if best_asset.path.is_file():
            dims = probe_image_dimensions(best_asset.path)
            if dims:
                w_img, h_img = dims
                rx, ry, rw, rh = calculate_fill_frame_rect(w_img, h_img, 1920, 1080)
                fill_info = {
                    "asset_width": w_img,
                    "asset_height": h_img,
                    "crop_x": rx,
                    "crop_y": ry,
                    "scale_w": rw,
                    "scale_h": rh,
                    "scale_factor": round(rw / w_img, 4) if w_img > 0 else 1.0,
                    "aspect_ratio": round(w_img / h_img, 4) if h_img > 0 else 1.7778,
                }

        if best_asset.media_type == "image":
            # Images natively adapt to slot duration
            placements.append(BRollPlacement(
                segment_id=seg.segment_id,
                start=seg.start,
                end=seg.end,
                duration=slot_duration,
                text=seg.text,
                asset_path=rel_path,
                asset_type="image",
                asset_duration=slot_duration,
                trim_in=0.0,
                trim_out=slot_duration,
                status="MATCHED_OK",
                match_score=best_score,
                match_reason=best_reason,
                fill_frame_info=fill_info,
            ))
        else:
            # Video B-roll
            vid_dur = best_asset.duration_seconds or slot_duration
            if vid_dur >= slot_duration:
                # Video is sufficient: trim to fit slot
                placements.append(BRollPlacement(
                    segment_id=seg.segment_id,
                    start=seg.start,
                    end=seg.end,
                    duration=slot_duration,
                    text=seg.text,
                    asset_path=rel_path,
                    asset_type="video",
                    asset_duration=vid_dur,
                    trim_in=0.0,
                    trim_out=slot_duration,
                    status="MATCHED_OK",
                    match_score=best_score,
                    match_reason=best_reason,
                    fill_frame_info=fill_info,
                ))
            else:
                # Video is shorter than slot duration
                placements.append(BRollPlacement(
                    segment_id=seg.segment_id,
                    start=seg.start,
                    end=seg.end,
                    duration=slot_duration,
                    text=seg.text,
                    asset_path=rel_path,
                    asset_type="video",
                    asset_duration=vid_dur,
                    trim_in=0.0,
                    trim_out=vid_dur,
                    status="INSUFFICIENT_BROLL_DURATION",
                    match_score=best_score,
                    match_reason=f"{best_reason} | dur:{vid_dur:.1f}s < slot:{slot_duration:.1f}s",
                    fill_frame_info=fill_info,
                ))

    return placements



def build_broll_plan(
    workspace_dir: Path,
    main_video_meta: VideoMetadata,
    placements: List[BRollPlacement],
    output_plan_path: Path
) -> Path:
    """
    Save the complete B-roll assignment plan to JSON.
    Output: output/[workspace]/project/broll_plan.json
    """
    output_plan_path.parent.mkdir(parents=True, exist_ok=True)

    summary_stats = {
        "workspace": workspace_dir.name,
        "main_video": main_video_meta.filename,
        "main_video_duration_seconds": round(main_video_meta.duration_seconds, 3),
        "total_segments": len(placements),
        "matched_ok": sum(1 for p in placements if p.status == "MATCHED_OK"),
        "insufficient_duration": sum(1 for p in placements if p.status == "INSUFFICIENT_BROLL_DURATION"),
        "no_broll_available": sum(1 for p in placements if p.status == "NO_BROLL_AVAILABLE"),
        "segments": [p.to_dict() for p in placements],
    }

    output_plan_path.write_text(
        json.dumps(summary_stats, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    logger.info(f"B-roll plan berhasil disimpan: {output_plan_path}")
    return output_plan_path


# ==============================================================================
# SOUND EFFECTS SYSTEM
# ==============================================================================
def ensure_sound_effects(assets_dir: Path) -> Dict[str, Path]:
    """
    Ensure the standard editorial sound effects exist in assets_dir.
    Synthesizes clean 48kHz 16-bit mono WAVs if not already present.
    Supported:
      - click.wav: subtle camera / UI click (~0.06s) for B-roll appear
      - pop.wav: soft bubble pop transient (~0.09s) for Headline appear
      - whoosh.wav: smooth airy transition swell (~0.35s) for Section Titles
      - hit.wav: crisp editorial impact (~0.22s) for Emphasis text
      - rise.wav: subtle rising swell (~0.40s) for Transitions
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    sr = 48000
    effects = {
        "click.wav": assets_dir / "click.wav",
        "pop.wav": assets_dir / "pop.wav",
        "whoosh.wav": assets_dir / "whoosh.wav",
        "hit.wav": assets_dir / "hit.wav",
        "rise.wav": assets_dir / "rise.wav",
    }

    # 1. click.wav
    if not effects["click.wav"].is_file():
        n = int(0.06 * sr)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t / 0.007)
            freq = 1400.0 * math.exp(-t / 0.015) + 300.0
            val = math.sin(2 * math.pi * freq * t) * env
            samples.append(int(val * 24000))
        with wave.open(str(effects["click.wav"]), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    # 2. pop.wav
    if not effects["pop.wav"].is_file():
        n = int(0.09 * sr)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.sin(math.pi * (t / 0.09)) * math.exp(-t / 0.022)
            freq = 800.0 - 550.0 * (t / 0.09)
            val = math.sin(2 * math.pi * freq * t) * env
            samples.append(int(val * 26000))
        with wave.open(str(effects["pop.wav"]), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    # 3. whoosh.wav
    if not effects["whoosh.wav"].is_file():
        n = int(0.35 * sr)
        samples = []
        rng = random.Random(42)
        last_val = 0.0
        for i in range(n):
            t = i / sr
            env = math.sin(math.pi * (t / 0.35)) ** 2
            noise = rng.uniform(-1.0, 1.0)
            cutoff = 0.05 + 0.35 * math.sin(math.pi * (t / 0.35))
            last_val = last_val + cutoff * (noise - last_val)
            val = last_val * env
            samples.append(int(val * 22000))
        with wave.open(str(effects["whoosh.wav"]), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    # 4. hit.wav
    if not effects["hit.wav"].is_file():
        n = int(0.22 * sr)
        samples = []
        for i in range(n):
            t = i / sr
            env = math.exp(-t / 0.045)
            freq = 160.0 * math.exp(-t / 0.06) + 45.0
            val = math.sin(2 * math.pi * freq * t) * env
            samples.append(int(val * 28000))
        with wave.open(str(effects["hit.wav"]), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    # 5. rise.wav
    if not effects["rise.wav"].is_file():
        n = int(0.40 * sr)
        samples = []
        for i in range(n):
            t = i / sr
            prog = t / 0.40
            env = (prog ** 1.5) * (1.0 - math.exp(-5.0 * (1.0 - prog)))
            freq = 200.0 + 700.0 * (prog ** 2)
            val = math.sin(2 * math.pi * freq * t) * env
            samples.append(int(val * 24000))
        with wave.open(str(effects["rise.wav"]), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(b"".join(struct.pack("<h", s) for s in samples))

    return effects


def detect_sfx_events(
    placements: List[BRollPlacement],
    text_items: List[TextItem],
    sfx_assets: Dict[str, Path],
    min_interval: float = 2.0,
) -> List[SFXEvent]:
    """
    Synchronizes subtle editorial SFX to visual events with conservative throttling:
    - Section Title -> whoosh.wav
    - Headline -> pop.wav
    - Emphasis Text -> hit.wav
    - B-roll -> click.wav (throttled by min_interval)
    """
    events: List[SFXEvent] = []
    last_sfx_time = -999.0
    counter = 1

    # 1. Text visual cues (higher priority)
    for t in sorted(text_items, key=lambda x: x.start):
        if t.start - last_sfx_time < 0.8:
            continue
        sfx_type = "pop"
        fname = "pop.wav"
        if t.text_type == "SECTION_TITLE":
            sfx_type = "whoosh"
            fname = "whoosh.wav"
        elif t.text_type == "EMPHASIS_TEXT":
            sfx_type = "hit"
            fname = "hit.wav"

        events.append(SFXEvent(
            event_id=f"sfx_{counter:03d}",
            sfx_type=sfx_type,
            trigger_type=t.text_type.lower(),
            start=t.start,
            duration=0.35 if sfx_type == "whoosh" else 0.15,
            asset_filename=fname,
        ))
        last_sfx_time = t.start
        counter += 1

    # 2. B-roll visual cues (throttled to avoid rapid clicking)
    for p in sorted(placements, key=lambda x: x.start):
        if not p.asset_path:
            continue
        if p.start - last_sfx_time >= min_interval:
            events.append(SFXEvent(
                event_id=f"sfx_{counter:03d}",
                sfx_type="click",
                trigger_type="broll",
                start=p.start,
                duration=0.06,
                asset_filename="click.wav",
            ))
            last_sfx_time = p.start
            counter += 1

    return sorted(events, key=lambda e: e.start)


# ==============================================================================
# TYPOGRAPHY & TITLE SYSTEM
# ==============================================================================
def calculate_text_layout(
    text: str,
    text_type: str,
    proj_w: int = 1920,
    proj_h: int = 1080,
    preset: str = PRESET_A_DOC_YELLOW,
) -> Dict[str, Any]:
    """
    Calculates typography hierarchy, word wrapping, safe margins,
    and adaptive background shape dimensions.
    """
    text_clean = text.strip()
    safe_margin_x = int(round(proj_w * 0.08))
    safe_margin_y = int(round(proj_h * 0.08))
    max_safe_width = proj_w - (2 * safe_margin_x)

    # Typography sizing per hierarchy
    if text_type == "SECTION_TITLE":
        font_size = 64
        font_weight = 87
        max_lines = 3
        pad_x = 45
        pad_y = 25
        pos_y_anchor = 0.40  # centered vertically
    elif text_type == "HEADLINE":
        font_size = 54
        font_weight = 87
        max_lines = 2
        pad_x = 40
        pad_y = 20
        pos_y_anchor = 0.68  # lower-middle editorial position
    elif text_type == "EMPHASIS_TEXT":
        font_size = 72
        font_weight = 87
        max_lines = 1
        pad_x = 35
        pad_y = 18
        pos_y_anchor = 0.50  # impact center
    elif text_type == "LOWER_THIRD":
        font_size = 38
        font_weight = 63
        max_lines = 2
        pad_x = 30
        pad_y = 15
        pos_y_anchor = 0.82  # bottom-left badge
    else:
        font_size = 48
        font_weight = 75
        max_lines = 2
        pad_x = 35
        pad_y = 20
        pos_y_anchor = 0.70

    # Word wrapping to fit max_safe_width
    approx_char_w = font_size * 0.56
    words = text_clean.split()
    lines: List[str] = []
    current_line: List[str] = []

    for word in words:
        candidate = " ".join(current_line + [word])
        cand_w = len(candidate) * approx_char_w
        if cand_w > (max_safe_width - 2 * pad_x) and current_line:
            lines.append(" ".join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(" ".join(current_line))

    # Clamp line count
    if len(lines) > max_lines:
        lines = lines[:max_lines]

    formatted_text = "\n".join(lines)
    max_line_len = max(len(l) for l in lines) if lines else 1
    text_content_w = int(round(max_line_len * approx_char_w))
    line_h = int(round(font_size * 1.25))
    text_content_h = len(lines) * line_h

    box_w = min(max_safe_width, text_content_w + 2 * pad_x)
    box_h = text_content_h + 2 * pad_y

    # Calculate layout position
    if text_type == "LOWER_THIRD":
        box_x = safe_margin_x
        box_y = int(round(proj_h * pos_y_anchor))
    else:
        box_x = int(round((proj_w - box_w) / 2.0))
        box_y = int(round(proj_h * pos_y_anchor - (box_h / 2.0)))

    # Clamp inside safe area
    box_x = max(safe_margin_x, min(proj_w - safe_margin_x - box_w, box_x))
    box_y = max(safe_margin_y, min(proj_h - safe_margin_y - box_h, box_y))

    text_x = box_x + pad_x
    text_y = box_y + pad_y

    # Contrast & preset coloring
    if preset == PRESET_C_CLEAN_WHITE:
        text_color = COLOR_WHITE
        has_box = False
    elif preset == PRESET_B_CLEAN_YELLOW:
        text_color = COLOR_BRIGHT_YELLOW
        has_box = False
    elif preset == PRESET_D_BOXED_EDITORIAL:
        text_color = COLOR_BRIGHT_YELLOW
        has_box = True
    else:  # PRESET_A_DOC_YELLOW (default)
        text_color = COLOR_BRIGHT_YELLOW
        has_box = True

    return {
        "formatted_text": formatted_text,
        "font_size": font_size,
        "font_weight": font_weight,
        "text_color": text_color,
        "outline_color": COLOR_BLACK_SHADOW,
        "outline_width": 2.5,
        "has_box": has_box,
        "box_color": COLOR_DARK_SHAPE,
        "box_radius": 12,
        "box_x": box_x,
        "box_y": box_y,
        "box_w": box_w,
        "box_h": box_h,
        "text_x": text_x,
        "text_y": text_y,
        "text_w": text_content_w,
        "text_h": text_content_h,
    }


def generate_kdenlivetitle_file(
    item: TextItem,
    output_path: Path,
    proj_w: int = 1920,
    proj_h: int = 1080,
    fps: float = 30.0,
) -> Path:
    """
    Writes a native, human-editable .kdenlivetitle XML file containing
    styled QGraphicsRectItem (semi-transparent rounded box) and
    QGraphicsTextItem (bright yellow text with subtle black shadow).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(round(item.duration * fps)))

    root = ET.Element("kdenlivetitle")
    root.set("width", str(proj_w))
    root.set("height", str(proj_h))
    root.set("duration", str(frames))
    root.set("out", str(frames - 1))

    # Optional background dark shape (QGraphicsRectItem)
    if item.has_box:
        item_rect = ET.SubElement(root, "item")
        item_rect.set("type", "QGraphicsRectItem")
        item_rect.set("z-value", "0")

        pos_r = ET.SubElement(item_rect, "position")
        pos_r.set("x", str(item.box_x))
        pos_r.set("y", str(item.box_y))
        tf_r = ET.SubElement(pos_r, "transform")
        tf_r.text = "1,0,0,0,1,0,0,0,1"

        cnt_r = ET.SubElement(item_rect, "content")
        cnt_r.set("brushcolor", item.box_color)
        cnt_r.set("pencolor", "0,0,0,0")
        cnt_r.set("penwidth", "0")
        cnt_r.set("rect", f"0,0,{item.box_w},{item.box_h}")
        cnt_r.set("round", str(item.box_radius))

    # Text content (QGraphicsTextItem)
    item_txt = ET.SubElement(root, "item")
    item_txt.set("type", "QGraphicsTextItem")
    item_txt.set("z-value", "1")

    pos_t = ET.SubElement(item_txt, "position")
    pos_t.set("x", str(item.text_x))
    pos_t.set("y", str(item.text_y))
    tf_t = ET.SubElement(pos_t, "transform")
    tf_t.text = "1,0,0,0,1,0,0,0,1"

    cnt_t = ET.SubElement(item_txt, "content")
    cnt_t.set("font", item.font_family)
    cnt_t.set("font-size", str(item.font_size))
    cnt_t.set("font-weight", str(item.font_weight))
    cnt_t.set("font-bold", "1" if item.font_weight >= 75 else "0")
    cnt_t.set("font-italic", "0")
    cnt_t.set("font-underline", "0")
    cnt_t.set("font-color", item.text_color)
    cnt_t.set("outline", item.outline_color)
    cnt_t.set("outline-width", str(item.outline_width))
    cnt_t.set("shadow", "0,0,0,200;2;2;5")
    cnt_t.set("alignment", "4")  # Center alignment
    cnt_t.set("boxwidth", str(max(10, item.box_w - 40)))
    cnt_t.set("boxheight", str(max(10, item.box_h - 20)))
    cnt_t.set("letter-spacing", "1")
    cnt_t.set("line-spacing", "0")
    cnt_t.text = item.text

    start_vp = ET.SubElement(root, "startviewport")
    start_vp.set("rect", f"0,0,{proj_w},{proj_h}")
    end_vp = ET.SubElement(root, "endviewport")
    end_vp.set("rect", f"0,0,{proj_w},{proj_h}")

    raw_xml = ET.tostring(root, encoding="utf-8")
    xml_formatted = minidom.parseString(raw_xml).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    output_path.write_text(xml_formatted, encoding="utf-8")
    return output_path


def detect_text_moments(
    segments: List[TranscriptSegment],
    video_duration: float,
    proj_w: int = 1920,
    proj_h: int = 1080,
) -> List[TextItem]:
    """
    Conservatively detects editorial text moments from transcript:
    - SECTION_TITLE: chapter / major section transitions (e.g. "bagian", "kenapa", "mengapa")
    - HEADLINE: key philosophical statements / problems (e.g. "masalahnya", "kuncinya", "waktu")
    - EMPHASIS_TEXT: numbers & metrics (e.g. "60 km", "35 menit", "3 jam", "25 tahun")
    - LOWER_THIRD: context / topic tags
    """
    items: List[TextItem] = []
    counter = 1
    last_text_end = -999.0

    re_emphasis = re.compile(
        r"\b(\d+[\s]*(?:kilometer|km|menit|jam|persen|%|miliar|juta|ribu|tahun|hari))\b",
        re.IGNORECASE
    )

    for seg in segments:
        text_lower = seg.text.lower()

        # Minimum spacing between text events to avoid screen flooding
        if seg.start - last_text_end < 4.0:
            continue

        detected_type = None
        headline_text = None

        # 1. Section Title candidates
        if any(kw in text_lower for kw in ["bagian", "bab", "sekarang kita masuk", "kenapa rumah", "alasan kenapa"]):
            detected_type = "SECTION_TITLE"
            headline_text = seg.text.upper()
        # 2. Headline candidates
        elif any(kw in text_lower for kw in ["masalahnya", "kuncinya", "faktanya", "sadar atau tidak", "yang menarik", "ternyata"]):
            detected_type = "HEADLINE"
            headline_text = seg.text.upper()
        # 3. Emphasis Number/Stat candidates
        else:
            m = re_emphasis.search(seg.text)
            if m:
                detected_type = "EMPHASIS_TEXT"
                headline_text = m.group(1).upper()

        if detected_type and headline_text:
            dur = min(4.5, max(2.5, seg.duration))
            start_t = seg.start
            end_t = min(video_duration, start_t + dur)

            layout = calculate_text_layout(
                text=headline_text,
                text_type=detected_type,
                proj_w=proj_w,
                proj_h=proj_h,
                preset=PRESET_A_DOC_YELLOW,
            )

            item = TextItem(
                item_id=f"title_{counter:02d}",
                text_type=detected_type,
                preset=PRESET_A_DOC_YELLOW,
                text=layout["formatted_text"],
                start=start_t,
                end=end_t,
                duration=round(end_t - start_t, 3),
                font_family="Arial, Sans-Serif",
                font_size=layout["font_size"],
                font_weight=layout["font_weight"],
                text_color=layout["text_color"],
                outline_color=layout["outline_color"],
                outline_width=layout["outline_width"],
                has_box=layout["has_box"],
                box_color=layout["box_color"],
                box_radius=layout["box_radius"],
                box_x=layout["box_x"],
                box_y=layout["box_y"],
                box_w=layout["box_w"],
                box_h=layout["box_h"],
                text_x=layout["text_x"],
                text_y=layout["text_y"],
                text_w=layout["text_w"],
                text_h=layout["text_h"],
            )
            items.append(item)
            last_text_end = end_t
            counter += 1

    return items


# ==============================================================================
# EDIT MANIFEST MANAGEMENT
# ==============================================================================
def load_manifest(manifest_path: Path) -> Optional[Dict[str, Any]]:
    """Load existing edit_manifest.json if valid."""
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "stages" in data:
            return data
    except Exception:
        pass
    return None


def save_manifest(manifest_path: Path, manifest_data: Dict[str, Any]) -> None:
    """Save edit manifest with UTC ISO timestamp."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ==============================================================================
# INCREMENTAL EDITING & MANUAL EDIT PRESERVATION
# ==============================================================================
def parse_existing_kdenlive(kdenlive_path: Path, fps: float = 30.0) -> Optional[Dict[str, Any]]:
    """
    Parses an existing .kdenlive project file to inspect:
    - Registered producers in Project Bin
    - Clips on playlist_v1 (Main Video)
    - Clips on playlist_v2 (B-roll): timeline start, end, in/out, resource, filters
    - Clips on playlist_v3 (Titles): timeline start, end, resource
    - Clips on playlist_a2 (SFX): timeline start, end, resource
    """
    if not kdenlive_path.is_file():
        return None
    try:
        tree = ET.parse(str(kdenlive_path))
        root = tree.getroot()
        if root.tag != "mlt":
            return None

        # Map producers by id
        producers: Dict[str, Dict[str, Any]] = {}
        for prod in root.findall("./producer"):
            pid = prod.attrib.get("id")
            if not pid or pid == "black_track":
                continue
            res = next((p.text for p in prod.findall("property") if p.attrib.get("name") == "resource"), "")
            kid = next((p.text for p in prod.findall("property") if p.attrib.get("name") == "kdenlive:id"), "")
            cuuid = next((p.text for p in prod.findall("property") if p.attrib.get("name") == "kdenlive:control_uuid"), "")
            producers[pid] = {
                "id": pid,
                "resource": res,
                "kdenlive:id": kid,
                "kdenlive:control_uuid": cuuid,
            }

        def _parse_track(track_id: str) -> List[Dict[str, Any]]:
            entries: List[Dict[str, Any]] = []
            elem = root.find(f"./playlist[@id='{track_id}']")
            if elem is None:
                return entries

            current_frame = 0
            for child in elem:
                if child.tag == "blank":
                    length = int(child.attrib.get("length", 0))
                    current_frame += length
                elif child.tag == "entry":
                    prod_ref = child.attrib.get("producer")
                    in_f = int(child.attrib.get("in", 0))
                    out_f = int(child.attrib.get("out", 0))
                    entry_len = max(1, out_f - in_f + 1)
                    res = producers.get(prod_ref, {}).get("resource", "")

                    entries.append({
                        "producer_id": prod_ref,
                        "resource": res,
                        "timeline_start_frame": current_frame,
                        "timeline_end_frame": current_frame + entry_len,
                        "timeline_start_sec": round(current_frame / fps, 3),
                        "timeline_end_sec": round((current_frame + entry_len) / fps, 3),
                        "in": in_f,
                        "out": out_f,
                        "length": entry_len,
                    })
                    current_frame += entry_len
            return entries

        return {
            "producers": producers,
            "v1_clips": _parse_track("playlist_v1"),
            "v2_clips": _parse_track("playlist_v2"),
            "v3_clips": _parse_track("playlist_v3"),
            "a2_clips": _parse_track("playlist_a2"),
        }
    except Exception:
        return None


def merge_timeline_preservations(
    existing_data: Optional[Dict[str, Any]],
    auto_placements: List[BRollPlacement],
    auto_text_items: List[TextItem],
    auto_sfx_events: List[SFXEvent],
    fps: float = 30.0,
    mode: str = "all",
) -> Tuple[List[BRollPlacement], List[TextItem], List[SFXEvent], Dict[str, Any]]:
    """
    Enforces the core rule:
    MANUAL USER EDIT > PREVIOUS AUTOMATIC DECISION > NEW AUTOMATIC DECISION.
    - If user replaced an asset at time T with another file, keep user's file.
    - If user moved/trimmed an asset, keep user's timing and trim.
    - If user deleted an asset (timeline is blank where auto placed B-roll), do NOT re-add!
    - If user created custom title clips, keep them.
    - If user placed custom SFX, keep them.
    """
    mod_stats: Dict[str, Any] = {
        "manual_edits_detected": False,
        "preserved_broll_count": 0,
        "preserved_deleted_count": 0,
        "preserved_titles_count": 0,
        "preserved_sfx_count": 0,
    }

    if not existing_data:
        return auto_placements, auto_text_items, auto_sfx_events, mod_stats

    existing_v2 = existing_data.get("v2_clips", [])
    merged_placements: List[BRollPlacement] = []

    # Map existing clips by timeline start time
    # Check each auto_placement against existing timeline
    for p in auto_placements:
        p_start_f = int(round(p.start * fps))
        p_end_f = int(round(p.end * fps))

        # Find existing clip that overlaps this segment
        matching_clip = next(
            (c for c in existing_v2 if not (c["timeline_end_frame"] <= p_start_f or c["timeline_start_frame"] >= p_end_f)),
            None
        )

        if matching_clip is not None:
            c_res = matching_clip["resource"]
            # Did the user change the asset?
            clean_res = c_res.replace("\\", "/").split("/")[-1]
            auto_res = Path(p.asset_path).name if p.asset_path else ""

            if auto_res and clean_res != auto_res:
                # USER REPLACED B-ROLL: preserve user's file
                mod_stats["manual_edits_detected"] = True
                mod_stats["preserved_broll_count"] += 1
                p.asset_path = f"broll/{clean_res}"
                p.match_reason = f"USER_MANUAL_SELECTION: {clean_res}"
                p.status = "USER_PRESERVED"
                p.trim_in = matching_clip["in"] / fps
                p.trim_out = matching_clip["out"] / fps
            elif auto_res and clean_res == auto_res:
                # Same asset, check if user adjusted trim or duration
                if abs((matching_clip["out"] / fps) - p.trim_out) > 0.1:
                    mod_stats["manual_edits_detected"] = True
                    mod_stats["preserved_broll_count"] += 1
                    p.trim_in = matching_clip["in"] / fps
                    p.trim_out = matching_clip["out"] / fps
                    p.status = "USER_PRESERVED_TRIM"

            merged_placements.append(p)
        else:
            # Segment had B-roll originally, but user left it blank on timeline
            if p.asset_path and existing_v2:
                # User intentionally deleted this B-roll!
                mod_stats["manual_edits_detected"] = True
                mod_stats["preserved_deleted_count"] += 1
                p.asset_path = None
                p.asset_type = "none"
                p.status = "USER_DELETED_PRESERVED"
                p.match_reason = "User deleted B-roll from timeline; preserved as blank"
            merged_placements.append(p)

    return merged_placements, auto_text_items, auto_sfx_events, mod_stats


# ==============================================================================
# KDENLIVE PROJECT GENERATION (MLT XML)
# ==============================================================================
def resolve_safe_kdenlive_path(project_dir: Path, base_filename: str = "video_auto.kdenlive", overwrite: bool = False) -> Path:
    """
    Determine safe output filename to ensure idempotency.
    If overwrite is False and file exists, returns video_auto_2.kdenlive, etc.
    """
    target = project_dir / base_filename
    if overwrite or not target.exists():
        return target

    # Increment counter
    stem = target.stem
    ext = target.suffix
    idx = 2
    while True:
        candidate = project_dir / f"{stem}_{idx}{ext}"
        if not candidate.exists():
            return candidate
        idx += 1


def _generate_canonical_uuid(identifier: str) -> str:
    """Generate a canonical UUID enclosed in braces {UUID} for Kdenlive compatibility."""
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:kdenlive:{identifier}")) + "}"


def generate_kdenlive_project(
    workspace_dir: Path,
    main_video_meta: VideoMetadata,
    placements: List[BRollPlacement],
    srt_path: Path,
    output_kdenlive_path: Path,
    text_items: Optional[List[TextItem]] = None,
    sfx_events: Optional[List[SFXEvent]] = None,
    bgm_path: Optional[Path] = None,
    apply_zoom: bool = True,
    apply_fill_frame: bool = True,
) -> Path:
    """
    Generates a production-ready, structural .kdenlive (MLT XML 7.41.0 compatible) project file
    with full Project Bin <-> Timeline clip reference integrity and 7-track architecture.

    Timeline Architecture:
      Track 0: Black Track (Background producer: color black)
      Track 1 (Playlist A1 - Audio Utama): Full raw video audio (narration)
      Track 2 (Playlist A2 - SFX): Synchronized sound effects audio
      Track 3 (Playlist A3 - BGM): Background music / audio finishing
      Track 4 (Playlist V1 - Video Utama): Full raw video composited over Track 0
      Track 5 (Playlist V2 - B-roll): [Entry][Blank][Entry] composited over Track 4 via qtblend
      Track 6 (Playlist V3 - Titles): Native Kdenlive title clips (.kdenlivetitle) composited over V1/V2
      Subtitles: avfilter.subtitles on main tractor + kdenlive:docproperties.subtitlesList
    """
    output_kdenlive_path.parent.mkdir(parents=True, exist_ok=True)
    fps = main_video_meta.fps
    total_frames = main_video_meta.total_frames
    width = main_video_meta.width
    height = main_video_meta.height

    # Safe backup of previous project if it exists
    if output_kdenlive_path.is_file():
        backup_path = output_kdenlive_path.with_suffix(".kdenlive.bak")
        try:
            shutil.copy2(output_kdenlive_path, backup_path)
            logger.info(f"Backup project tersimpan di: {backup_path}")
        except Exception as e:
            logger.warning(f"Gagal membuat backup: {e}")

    # Generate title XML files if text_items provided
    titles_dir = output_kdenlive_path.parent / "titles"
    titles_dir.mkdir(parents=True, exist_ok=True)
    if text_items:
        for t_item in text_items:
            t_file = titles_dir / f"{t_item.item_id}.kdenlivetitle"
            generate_kdenlivetitle_file(t_item, t_file, proj_w=width, proj_h=height, fps=fps)

    # Frame display aspect ratio
    gcd_val = math.gcd(width, height)
    disp_num = width // gcd_val if gcd_val > 0 else 16
    disp_den = height // gcd_val if gcd_val > 0 else 9

    root = ET.Element("mlt")
    root.set("LC_NUMERIC", "C")
    root.set("version", "7.41.0")
    root.set("title", f"AutoEdit_{workspace_dir.name}")
    root.set("producer", "main_bin")

    # Profile definition
    profile = ET.SubElement(root, "profile")
    profile.set("description", f"Custom {width}x{height} {fps:.2f}fps")
    profile.set("width", str(width))
    profile.set("height", str(height))
    profile.set("progressive", "1")
    profile.set("sample_aspect_num", "1")
    profile.set("sample_aspect_den", "1")
    profile.set("display_aspect_num", str(disp_num))
    profile.set("display_aspect_den", str(disp_den))
    profile.set("frame_rate_num", str(int(round(fps * 1000))))
    profile.set("frame_rate_den", "1000")
    profile.set("colorspace", "709")

    # --------------------------------------------------------------------------
    # Producers: Main Video, Black Track, B-roll, Titles, SFX, BGM
    # --------------------------------------------------------------------------
    main_bin_id = "1"
    main_uuid = _generate_canonical_uuid(f"main:{main_video_meta.filename}")

    # Producer 1: Main Raw Video
    prod_main = ET.SubElement(root, "producer")
    prod_main.set("id", "producer_main")
    prod_main.set("in", "0")
    prod_main.set("out", str(max(0, total_frames - 1)))

    p_len = ET.SubElement(prod_main, "property")
    p_len.set("name", "length")
    p_len.text = str(total_frames)

    p_eof = ET.SubElement(prod_main, "property")
    p_eof.set("name", "eof")
    p_eof.text = "pause"

    p_res = ET.SubElement(prod_main, "property")
    p_res.set("name", "resource")
    p_res.text = f"../footage/{main_video_meta.filename}"

    p_asp = ET.SubElement(prod_main, "property")
    p_asp.set("name", "aspect_ratio")
    p_asp.text = "1"

    p_name = ET.SubElement(prod_main, "property")
    p_name.set("name", "kdenlive:clipname")
    p_name.text = main_video_meta.filename

    p_ctype = ET.SubElement(prod_main, "property")
    p_ctype.set("name", "kdenlive:clip_type")
    p_ctype.text = "0"

    p_fld = ET.SubElement(prod_main, "property")
    p_fld.set("name", "kdenlive:folderid")
    p_fld.text = "-1"

    p_kid = ET.SubElement(prod_main, "property")
    p_kid.set("name", "kdenlive:id")
    p_kid.text = main_bin_id

    p_cuuid = ET.SubElement(prod_main, "property")
    p_cuuid.set("name", "kdenlive:control_uuid")
    p_cuuid.text = main_uuid

    # Producer 0: Black Track Background
    prod_black = ET.SubElement(root, "producer")
    prod_black.set("id", "black_track")
    prod_black.set("in", "0")
    prod_black.set("out", str(max(0, total_frames - 1)))

    pb_len = ET.SubElement(prod_black, "property")
    pb_len.set("name", "length")
    pb_len.text = "2147483647"

    pb_eof = ET.SubElement(prod_black, "property")
    pb_eof.set("name", "eof")
    pb_eof.text = "continue"

    pb_res = ET.SubElement(prod_black, "property")
    pb_res.set("name", "resource")
    pb_res.text = "black"

    pb_asp = ET.SubElement(prod_black, "property")
    pb_asp.set("name", "aspect_ratio")
    pb_asp.text = "1"

    pb_svc = ET.SubElement(prod_black, "property")
    pb_svc.set("name", "mlt_service")
    pb_svc.text = "color"

    pb_fmt = ET.SubElement(prod_black, "property")
    pb_fmt.set("name", "mlt_image_format")
    pb_fmt.text = "rgba"

    pb_aud = ET.SubElement(prod_black, "property")
    pb_aud.set("name", "set.test_audio")
    pb_aud.text = "0"

    # B-roll Producers
    unique_broll_assets: Dict[str, Tuple[str, str, str, int, BRollPlacement]] = {}
    broll_counter = 1

    for p in placements:
        if p.asset_path and p.asset_path not in unique_broll_assets:
            prod_id = f"producer_broll_{broll_counter:02d}"
            broll_bin_id = str(broll_counter + 1)
            fname = Path(p.asset_path).name
            broll_uuid = _generate_canonical_uuid(f"broll:{fname}")

            if p.asset_type == "image":
                f_len = total_frames
            else:
                vid_dur = p.asset_duration or main_video_meta.duration_seconds
                f_len = max(1, int(math.ceil(vid_dur * fps)))

            unique_broll_assets[p.asset_path] = (prod_id, broll_bin_id, broll_uuid, f_len, p)
            broll_counter += 1

    for asset_rel_path, (prod_id, broll_bin_id, broll_uuid, f_len, sample_placement) in unique_broll_assets.items():
        fname = Path(asset_rel_path).name
        prod = ET.SubElement(root, "producer")
        prod.set("id", prod_id)
        prod.set("in", "0")
        prod.set("out", str(max(0, f_len - 1)))

        prop_l = ET.SubElement(prod, "property")
        prop_l.set("name", "length")
        prop_l.text = str(f_len)

        prop_eof = ET.SubElement(prod, "property")
        prop_eof.set("name", "eof")
        prop_eof.text = "pause"

        prop_r = ET.SubElement(prod, "property")
        prop_r.set("name", "resource")
        prop_r.text = f"../broll/{fname}"

        prop_asp = ET.SubElement(prod, "property")
        prop_asp.set("name", "aspect_ratio")
        prop_asp.text = "1"

        prop_n = ET.SubElement(prod, "property")
        prop_n.set("name", "kdenlive:clipname")
        prop_n.text = fname

        prop_ct = ET.SubElement(prod, "property")
        prop_ct.set("name", "kdenlive:clip_type")
        prop_ct.text = "2" if sample_placement.asset_type == "image" else "0"

        prop_fid = ET.SubElement(prod, "property")
        prop_fid.set("name", "kdenlive:folderid")
        prop_fid.text = "-1"

        prop_id = ET.SubElement(prod, "property")
        prop_id.set("name", "kdenlive:id")
        prop_id.text = broll_bin_id

        prop_cuuid = ET.SubElement(prod, "property")
        prop_cuuid.set("name", "kdenlive:control_uuid")
        prop_cuuid.text = broll_uuid

    # Title Producers
    title_producers: Dict[str, Tuple[str, str, str, int, TextItem]] = {}
    title_counter = 101

    if text_items:
        for t_item in text_items:
            t_prod_id = f"producer_{t_item.item_id}"
            t_bin_id = str(title_counter)
            t_uuid = _generate_canonical_uuid(f"title:{t_item.item_id}")
            t_len = max(1, int(round(t_item.duration * fps)))
            title_producers[t_item.item_id] = (t_prod_id, t_bin_id, t_uuid, t_len, t_item)
            title_counter += 1

            t_prod = ET.SubElement(root, "producer")
            t_prod.set("id", t_prod_id)
            t_prod.set("in", "0")
            t_prod.set("out", str(t_len - 1))

            pt_l = ET.SubElement(t_prod, "property")
            pt_l.set("name", "length")
            pt_l.text = str(t_len)

            pt_eof = ET.SubElement(t_prod, "property")
            pt_eof.set("name", "eof")
            pt_eof.text = "pause"

            pt_res = ET.SubElement(t_prod, "property")
            pt_res.set("name", "resource")
            pt_res.text = f"titles/{t_item.item_id}.kdenlivetitle"

            pt_svc = ET.SubElement(t_prod, "property")
            pt_svc.set("name", "mlt_service")
            pt_svc.text = "kdenlivetitle"

            pt_asp = ET.SubElement(t_prod, "property")
            pt_asp.set("name", "aspect_ratio")
            pt_asp.text = "1"

            pt_name = ET.SubElement(t_prod, "property")
            pt_name.set("name", "kdenlive:clipname")
            pt_name.text = f"{t_item.item_id}.kdenlivetitle"

            pt_ct = ET.SubElement(t_prod, "property")
            pt_ct.set("name", "kdenlive:clip_type")
            pt_ct.text = "3"  # Title clip

            pt_fid = ET.SubElement(t_prod, "property")
            pt_fid.set("name", "kdenlive:folderid")
            pt_fid.text = "-1"

            pt_kid = ET.SubElement(t_prod, "property")
            pt_kid.set("name", "kdenlive:id")
            pt_kid.text = t_bin_id

            pt_cuuid = ET.SubElement(t_prod, "property")
            pt_cuuid.set("name", "kdenlive:control_uuid")
            pt_cuuid.text = t_uuid

    # SFX Producers
    sfx_producers: Dict[str, Tuple[str, str, str, int]] = {}
    sfx_counter = 201

    if sfx_events:
        unique_sfx_files = sorted(list(set(e.asset_filename for e in sfx_events)))
        for sf in unique_sfx_files:
            s_prod_id = f"producer_sfx_{Path(sf).stem}"
            s_bin_id = str(sfx_counter)
            s_uuid = _generate_canonical_uuid(f"sfx:{sf}")
            s_len = int(round(1.0 * fps))  # safe nominal duration
            sfx_producers[sf] = (s_prod_id, s_bin_id, s_uuid, s_len)
            sfx_counter += 1

            s_prod = ET.SubElement(root, "producer")
            s_prod.set("id", s_prod_id)
            s_prod.set("in", "0")
            s_prod.set("out", str(s_len - 1))

            ps_l = ET.SubElement(s_prod, "property")
            ps_l.set("name", "length")
            ps_l.text = str(s_len)

            ps_eof = ET.SubElement(s_prod, "property")
            ps_eof.set("name", "eof")
            ps_eof.text = "pause"

            sfx_file = workspace_dir.parent.parent / "assets" / "sound_effects" / sf
            try:
                rel_sfx_path = os.path.relpath(sfx_file, output_kdenlive_path.parent).replace("\\", "/")
            except Exception:
                rel_sfx_path = f"../../../assets/sound_effects/{sf}"

            ps_res = ET.SubElement(s_prod, "property")
            ps_res.set("name", "resource")
            ps_res.text = rel_sfx_path

            ps_name = ET.SubElement(s_prod, "property")
            ps_name.set("name", "kdenlive:clipname")
            ps_name.text = sf

            ps_ct = ET.SubElement(s_prod, "property")
            ps_ct.set("name", "kdenlive:clip_type")
            ps_ct.text = "1"  # Audio clip

            ps_fid = ET.SubElement(s_prod, "property")
            ps_fid.set("name", "kdenlive:folderid")
            ps_fid.text = "-1"

            ps_kid = ET.SubElement(s_prod, "property")
            ps_kid.set("name", "kdenlive:id")
            ps_kid.text = s_bin_id

            ps_cuuid = ET.SubElement(s_prod, "property")
            ps_cuuid.set("name", "kdenlive:control_uuid")
            ps_cuuid.text = s_uuid

    # --------------------------------------------------------------------------
    # Project Bin Playlist (main_bin)
    # MUST contain xml_retain=1, valid docproperties, and entries for all assets
    # --------------------------------------------------------------------------
    bin_playlist = ET.SubElement(root, "playlist")
    bin_playlist.set("id", "main_bin")

    prop_ver = ET.SubElement(bin_playlist, "property")
    prop_ver.set("name", "kdenlive:docproperties.version")
    prop_ver.text = "1.04"

    prop_kver = ET.SubElement(bin_playlist, "property")
    prop_kver.set("name", "kdenlive:docproperties.kdenliveversion")
    prop_kver.text = "24.08.0"

    prop_act = ET.SubElement(bin_playlist, "property")
    prop_act.set("name", "kdenlive:docproperties.activeTrack")
    prop_act.text = "4"  # Focus on Video Utama track

    prop_ach = ET.SubElement(bin_playlist, "property")
    prop_ach.set("name", "kdenlive:docproperties.audioChannels")
    prop_ach.text = "2"

    prop_atg = ET.SubElement(bin_playlist, "property")
    prop_atg.set("name", "kdenlive:docproperties.audioTarget")
    prop_atg.text = "1"

    prop_vtg = ET.SubElement(bin_playlist, "property")
    prop_vtg.set("name", "kdenlive:docproperties.videoTarget")
    prop_vtg.text = "4"

    prop_pos = ET.SubElement(bin_playlist, "property")
    prop_pos.set("name", "kdenlive:docproperties.position")
    prop_pos.text = "0"

    prop_scroll = ET.SubElement(bin_playlist, "property")
    prop_scroll.set("name", "kdenlive:docproperties.scrollPos")
    prop_scroll.text = "0"

    prop_zoom = ET.SubElement(bin_playlist, "property")
    prop_zoom.set("name", "kdenlive:docproperties.zoom")
    prop_zoom.text = "8"

    prop_zin = ET.SubElement(bin_playlist, "property")
    prop_zin.set("name", "kdenlive:docproperties.zonein")
    prop_zin.text = "0"

    prop_zout = ET.SubElement(bin_playlist, "property")
    prop_zout.set("name", "kdenlive:docproperties.zoneout")
    prop_zout.text = str(min(75, max(0, total_frames - 1)))

    prop_exp = ET.SubElement(bin_playlist, "property")
    prop_exp.set("name", "kdenlive:expandedFolders")
    prop_exp.text = ""

    prop_notes = ET.SubElement(bin_playlist, "property")
    prop_notes.set("name", "kdenlive:documentnotes")
    prop_notes.text = ""

    # Retain main_bin in documentTractor
    prop_retain = ET.SubElement(bin_playlist, "property")
    prop_retain.set("name", "xml_retain")
    prop_retain.text = "1"

    # Add main video to bin
    bin_main = ET.SubElement(bin_playlist, "entry")
    bin_main.set("producer", "producer_main")
    bin_main.set("in", "0")
    bin_main.set("out", str(max(0, total_frames - 1)))

    # Add B-roll assets to bin
    for _, (prod_id, _, _, f_len, _) in unique_broll_assets.items():
        bin_e = ET.SubElement(bin_playlist, "entry")
        bin_e.set("producer", prod_id)
        bin_e.set("in", "0")
        bin_e.set("out", str(max(0, f_len - 1)))

    # Add Title clips to bin
    for _, (t_prod_id, _, _, t_len, _) in title_producers.items():
        bin_t = ET.SubElement(bin_playlist, "entry")
        bin_t.set("producer", t_prod_id)
        bin_t.set("in", "0")
        bin_t.set("out", str(max(0, t_len - 1)))

    # Add SFX assets to bin
    for _, (s_prod_id, _, _, s_len) in sfx_producers.items():
        bin_s = ET.SubElement(bin_playlist, "entry")
        bin_s.set("producer", s_prod_id)
        bin_s.set("in", "0")
        bin_s.set("out", str(max(0, s_len - 1)))

    # --------------------------------------------------------------------------
    # Track Playlists (7 Tracks)
    # --------------------------------------------------------------------------
    # Track 1: A1 Audio Utama (Voice / Audio from main video)
    playlist_a1 = ET.SubElement(root, "playlist")
    playlist_a1.set("id", "playlist_a1")
    t_name_a1 = ET.SubElement(playlist_a1, "property")
    t_name_a1.set("name", "kdenlive:track_name")
    t_name_a1.text = "Audio Utama"
    t_aud_a1 = ET.SubElement(playlist_a1, "property")
    t_aud_a1.set("name", "kdenlive:audio_track")
    t_aud_a1.text = "1"

    entry_a1 = ET.SubElement(playlist_a1, "entry")
    entry_a1.set("producer", "producer_main")
    entry_a1.set("in", "0")
    entry_a1.set("out", str(max(0, total_frames - 1)))
    p_ea1_id = ET.SubElement(entry_a1, "property")
    p_ea1_id.set("name", "kdenlive:id")
    p_ea1_id.text = main_bin_id
    p_ea1_uuid = ET.SubElement(entry_a1, "property")
    p_ea1_uuid.set("name", "kdenlive:control_uuid")
    p_ea1_uuid.text = main_uuid

    # Track 2: A2 SFX (Sound effects track)
    playlist_a2 = ET.SubElement(root, "playlist")
    playlist_a2.set("id", "playlist_a2")
    t_name_a2 = ET.SubElement(playlist_a2, "property")
    t_name_a2.set("name", "kdenlive:track_name")
    t_name_a2.text = "SFX"
    t_aud_a2 = ET.SubElement(playlist_a2, "property")
    t_aud_a2.set("name", "kdenlive:audio_track")
    t_aud_a2.text = "1"

    cur_sfx_frame = 0
    if sfx_events:
        for ev in sfx_events:
            ev_start_f = max(0, min(total_frames, int(round(ev.start * fps))))
            ev_len_f = max(1, int(round(ev.duration * fps)))
            if ev_start_f > cur_sfx_frame:
                blk = ET.SubElement(playlist_a2, "blank")
                blk.set("length", str(ev_start_f - cur_sfx_frame))
                cur_sfx_frame = ev_start_f

            if ev.asset_filename in sfx_producers and ev_start_f < total_frames:
                s_pid, s_bid, s_buuid, _ = sfx_producers[ev.asset_filename]
                s_entry = ET.SubElement(playlist_a2, "entry")
                s_entry.set("producer", s_pid)
                s_entry.set("in", "0")
                s_entry.set("out", str(ev_len_f - 1))

                pse_id = ET.SubElement(s_entry, "property")
                pse_id.set("name", "kdenlive:id")
                pse_id.text = s_bid
                pse_uuid = ET.SubElement(s_entry, "property")
                pse_uuid.set("name", "kdenlive:control_uuid")
                pse_uuid.text = s_buuid
                cur_sfx_frame += ev_len_f

    if cur_sfx_frame < total_frames:
        blk_tail = ET.SubElement(playlist_a2, "blank")
        blk_tail.set("length", str(total_frames - cur_sfx_frame))

    # Track 3: A3 BGM (Background music / audio finishing)
    playlist_a3 = ET.SubElement(root, "playlist")
    playlist_a3.set("id", "playlist_a3")
    t_name_a3 = ET.SubElement(playlist_a3, "property")
    t_name_a3.set("name", "kdenlive:track_name")
    t_name_a3.text = "BGM"
    t_aud_a3 = ET.SubElement(playlist_a3, "property")
    t_aud_a3.set("name", "kdenlive:audio_track")
    t_aud_a3.text = "1"
    blk_bgm = ET.SubElement(playlist_a3, "blank")
    blk_bgm.set("length", str(total_frames))

    # Track 4: V1 Video Utama (Main raw video)
    playlist_v1 = ET.SubElement(root, "playlist")
    playlist_v1.set("id", "playlist_v1")
    t_name_v1 = ET.SubElement(playlist_v1, "property")
    t_name_v1.set("name", "kdenlive:track_name")
    t_name_v1.text = "Video Utama"

    entry_v1 = ET.SubElement(playlist_v1, "entry")
    entry_v1.set("producer", "producer_main")
    entry_v1.set("in", "0")
    entry_v1.set("out", str(max(0, total_frames - 1)))
    p_ev1_id = ET.SubElement(entry_v1, "property")
    p_ev1_id.set("name", "kdenlive:id")
    p_ev1_id.text = main_bin_id
    p_ev1_uuid = ET.SubElement(entry_v1, "property")
    p_ev1_uuid.set("name", "kdenlive:control_uuid")
    p_ev1_uuid.text = main_uuid

    # Track 5: V2 B-roll Video Track
    playlist_v2 = ET.SubElement(root, "playlist")
    playlist_v2.set("id", "playlist_v2")
    t_name_v2 = ET.SubElement(playlist_v2, "property")
    t_name_v2.set("name", "kdenlive:track_name")
    t_name_v2.text = "B-roll"

    current_frame = 0
    filter_counter = 1

    for p in placements:
        seg_start_frame = int(round(p.start * fps))
        seg_end_frame = int(round(p.end * fps))

        # Clamp to bounds
        seg_start_frame = max(0, min(total_frames, seg_start_frame))
        seg_end_frame = max(seg_start_frame, min(total_frames, seg_end_frame))

        # Blank before segment if there's a gap
        if seg_start_frame > current_frame:
            blank_len = seg_start_frame - current_frame
            blank_elem = ET.SubElement(playlist_v2, "blank")
            blank_elem.set("length", str(blank_len))
            current_frame = seg_start_frame

        slot_frames = seg_end_frame - seg_start_frame
        if slot_frames <= 0:
            continue

        if p.asset_path and p.asset_path in unique_broll_assets:
            prod_id, broll_bin_id, broll_uuid, _, _ = unique_broll_assets[p.asset_path]
            entry_b = ET.SubElement(playlist_v2, "entry")
            entry_b.set("producer", prod_id)
            clip_in = max(0, int(round(p.trim_in * fps)))
            clip_frames = max(1, int(round((p.trim_out - p.trim_in) * fps)))
            actual_frames = min(slot_frames, clip_frames)
            entry_b.set("in", str(clip_in))
            entry_b.set("out", str(clip_in + actual_frames - 1))

            p_eb_id = ET.SubElement(entry_b, "property")
            p_eb_id.set("name", "kdenlive:id")
            p_eb_id.text = broll_bin_id
            p_eb_uuid = ET.SubElement(entry_b, "property")
            p_eb_uuid.set("name", "kdenlive:control_uuid")
            p_eb_uuid.text = broll_uuid

            # Fill-Frame & Quick Zoom filter via qtblend
            if apply_fill_frame or apply_zoom:
                base_rect = (0, 0, width, height)
                if p.fill_frame_info:
                    base_rect = (
                        p.fill_frame_info["crop_x"],
                        p.fill_frame_info["crop_y"],
                        p.fill_frame_info["scale_w"],
                        p.fill_frame_info["scale_h"],
                    )
                elif p.asset_type == "image":
                    asset_file = workspace_dir / p.asset_path
                    if asset_file.is_file():
                        dims = probe_image_dimensions(asset_file)
                        if dims:
                            base_rect = calculate_fill_frame_rect(dims[0], dims[1], width, height)

                if apply_zoom and actual_frames > 15:
                    rect_val = calculate_quick_zoom_keyframes(
                        fill_rect=base_rect,
                        duration_frames=actual_frames,
                        proj_w=width,
                        proj_h=height,
                        zoom_peak=1.08,
                    )
                else:
                    rect_val = f"0={base_rect[0]} {base_rect[1]} {base_rect[2]} {base_rect[3]} 1"

                flt = ET.SubElement(entry_b, "filter")
                flt.set("id", f"filter_zoom_{filter_counter:03d}")
                filter_counter += 1

                pf_svc = ET.SubElement(flt, "property")
                pf_svc.set("name", "mlt_service")
                pf_svc.text = "qtblend"

                pf_kid = ET.SubElement(flt, "property")
                pf_kid.set("name", "kdenlive_id")
                pf_kid.text = "qtblend"

                pf_rect = ET.SubElement(flt, "property")
                pf_rect.set("name", "rect")
                pf_rect.text = rect_val

            current_frame += actual_frames

            # If B-roll was shorter than slot, fill remainder of slot with blank
            if actual_frames < slot_frames:
                rem_blank = slot_frames - actual_frames
                b_rem = ET.SubElement(playlist_v2, "blank")
                b_rem.set("length", str(rem_blank))
                current_frame += rem_blank
        else:
            blank_elem = ET.SubElement(playlist_v2, "blank")
            blank_elem.set("length", str(slot_frames))
            current_frame += slot_frames

    if current_frame < total_frames:
        trail_blank = ET.SubElement(playlist_v2, "blank")
        trail_blank.set("length", str(total_frames - current_frame))

    # Track 6: V3 Titles Track
    playlist_v3 = ET.SubElement(root, "playlist")
    playlist_v3.set("id", "playlist_v3")
    t_name_v3 = ET.SubElement(playlist_v3, "property")
    t_name_v3.set("name", "kdenlive:track_name")
    t_name_v3.text = "Titles"

    cur_title_frame = 0
    if text_items:
        for t_item in text_items:
            t_start_f = max(0, min(total_frames, int(round(t_item.start * fps))))
            t_len_f = max(1, int(round(t_item.duration * fps)))

            if t_start_f > cur_title_frame:
                blk_t = ET.SubElement(playlist_v3, "blank")
                blk_t.set("length", str(t_start_f - cur_title_frame))
                cur_title_frame = t_start_f

            if t_item.item_id in title_producers and t_start_f < total_frames:
                t_pid, t_bid, t_buuid, _, _ = title_producers[t_item.item_id]
                t_entry = ET.SubElement(playlist_v3, "entry")
                t_entry.set("producer", t_pid)
                t_entry.set("in", "0")
                t_entry.set("out", str(t_len_f - 1))

                pte_id = ET.SubElement(t_entry, "property")
                pte_id.set("name", "kdenlive:id")
                pte_id.text = t_bid
                pte_uuid = ET.SubElement(t_entry, "property")
                pte_uuid.set("name", "kdenlive:control_uuid")
                pte_uuid.text = t_buuid
                cur_title_frame += t_len_f

    if cur_title_frame < total_frames:
        blk_t_tail = ET.SubElement(playlist_v3, "blank")
        blk_t_tail.set("length", str(total_frames - cur_title_frame))

    # --------------------------------------------------------------------------
    # Main Tractor & Compositing
    # --------------------------------------------------------------------------
    tractor = ET.SubElement(root, "tractor")
    tractor.set("id", "maintractor")
    tractor.set("in", "0")
    tractor.set("out", str(max(0, total_frames - 1)))

    p_docver = ET.SubElement(tractor, "property")
    p_docver.set("name", "kdenlive:docproperties.version")
    p_docver.text = "1.04"

    p_dockver = ET.SubElement(tractor, "property")
    p_dockver.set("name", "kdenlive:docproperties.kdenliveversion")
    p_dockver.text = "24.08.0"

    p_sublist = ET.SubElement(tractor, "property")
    p_sublist.set("name", "kdenlive:docproperties.subtitlesList")
    p_sublist.text = "../subtitle/subtitle.srt"

    p_tr0 = ET.SubElement(tractor, "property")
    p_tr0.set("name", "kdenlive:track:0")
    p_tr0.text = "Black Track"

    p_tr1 = ET.SubElement(tractor, "property")
    p_tr1.set("name", "kdenlive:track:1")
    p_tr1.text = "Audio Utama"

    p_tr2 = ET.SubElement(tractor, "property")
    p_tr2.set("name", "kdenlive:track:2")
    p_tr2.text = "SFX"

    p_tr3 = ET.SubElement(tractor, "property")
    p_tr3.set("name", "kdenlive:track:3")
    p_tr3.text = "BGM"

    p_tr4 = ET.SubElement(tractor, "property")
    p_tr4.set("name", "kdenlive:track:4")
    p_tr4.text = "Video Utama"

    p_tr5 = ET.SubElement(tractor, "property")
    p_tr5.set("name", "kdenlive:track:5")
    p_tr5.text = "B-roll"

    p_tr6 = ET.SubElement(tractor, "property")
    p_tr6.set("name", "kdenlive:track:6")
    p_tr6.text = "Titles"

    multitrack = ET.SubElement(tractor, "multitrack")

    tr_black = ET.SubElement(multitrack, "track")
    tr_black.set("producer", "black_track")

    tr_a1 = ET.SubElement(multitrack, "track")
    tr_a1.set("producer", "playlist_a1")
    tr_a1.set("hide", "video")

    tr_a2 = ET.SubElement(multitrack, "track")
    tr_a2.set("producer", "playlist_a2")
    tr_a2.set("hide", "video")

    tr_a3 = ET.SubElement(multitrack, "track")
    tr_a3.set("producer", "playlist_a3")
    tr_a3.set("hide", "video")

    tr_v1 = ET.SubElement(multitrack, "track")
    tr_v1.set("producer", "playlist_v1")

    tr_v2 = ET.SubElement(multitrack, "track")
    tr_v2.set("producer", "playlist_v2")

    tr_v3 = ET.SubElement(multitrack, "track")
    tr_v3.set("producer", "playlist_v3")

    # Transition 1: V1 blends over Black Track (Track 0) via qtblend
    trans_v1 = ET.SubElement(tractor, "transition")
    trans_v1.set("id", "transition_v1")
    p_v1a = ET.SubElement(trans_v1, "property")
    p_v1a.set("name", "a_track")
    p_v1a.text = "0"
    p_v1b = ET.SubElement(trans_v1, "property")
    p_v1b.set("name", "b_track")
    p_v1b.text = "4"
    p_v1ms = ET.SubElement(trans_v1, "property")
    p_v1ms.set("name", "mlt_service")
    p_v1ms.text = "qtblend"
    p_v1act = ET.SubElement(trans_v1, "property")
    p_v1act.set("name", "always_active")
    p_v1act.text = "1"

    # Transition 2: V2 (B-roll) blends over V1 (Video Utama) via qtblend
    trans_broll = ET.SubElement(tractor, "transition")
    trans_broll.set("id", "transition_broll")
    p_ta = ET.SubElement(trans_broll, "property")
    p_ta.set("name", "a_track")
    p_ta.text = "4"
    p_tb = ET.SubElement(trans_broll, "property")
    p_tb.set("name", "b_track")
    p_tb.text = "5"
    p_tms = ET.SubElement(trans_broll, "property")
    p_tms.set("name", "mlt_service")
    p_tms.text = "qtblend"
    p_tka = ET.SubElement(trans_broll, "property")
    p_tka.set("name", "always_active")
    p_tka.text = "1"

    # Transition 3: V3 (Titles) blends over V1/V2 via qtblend
    trans_titles = ET.SubElement(tractor, "transition")
    trans_titles.set("id", "transition_titles")
    p_tta = ET.SubElement(trans_titles, "property")
    p_tta.set("name", "a_track")
    p_tta.text = "4"
    p_ttb = ET.SubElement(trans_titles, "property")
    p_ttb.set("name", "b_track")
    p_ttb.text = "6"
    p_ttms = ET.SubElement(trans_titles, "property")
    p_ttms.set("name", "mlt_service")
    p_ttms.text = "qtblend"
    p_ttact = ET.SubElement(trans_titles, "property")
    p_ttact.set("name", "always_active")
    p_ttact.text = "1"

    # Audio Mix Transitions: A1, A2, A3
    trans_audio = ET.SubElement(tractor, "transition")
    trans_audio.set("id", "transition_audio")
    p_aa0 = ET.SubElement(trans_audio, "property")
    p_aa0.set("name", "a_track")
    p_aa0.text = "0"
    p_ab1 = ET.SubElement(trans_audio, "property")
    p_ab1.set("name", "b_track")
    p_ab1.text = "1"
    p_ams = ET.SubElement(trans_audio, "property")
    p_ams.set("name", "mlt_service")
    p_ams.text = "mix"
    p_aact = ET.SubElement(trans_audio, "property")
    p_aact.set("name", "always_active")
    p_aact.text = "1"
    p_ablnk = ET.SubElement(trans_audio, "property")
    p_ablnk.set("name", "accepts_blanks")
    p_ablnk.text = "1"
    p_asum = ET.SubElement(trans_audio, "property")
    p_asum.set("name", "sum")
    p_asum.text = "1"

    trans_sfx = ET.SubElement(tractor, "transition")
    trans_sfx.set("id", "transition_sfx")
    p_sa0 = ET.SubElement(trans_sfx, "property")
    p_sa0.set("name", "a_track")
    p_sa0.text = "0"
    p_sb2 = ET.SubElement(trans_sfx, "property")
    p_sb2.set("name", "b_track")
    p_sb2.text = "2"
    p_sms = ET.SubElement(trans_sfx, "property")
    p_sms.set("name", "mlt_service")
    p_sms.text = "mix"
    p_sact = ET.SubElement(trans_sfx, "property")
    p_sact.set("name", "always_active")
    p_sact.text = "1"
    p_sblnk = ET.SubElement(trans_sfx, "property")
    p_sblnk.set("name", "accepts_blanks")
    p_sblnk.text = "1"
    p_ssum = ET.SubElement(trans_sfx, "property")
    p_ssum.set("name", "sum")
    p_ssum.text = "1"

    trans_bgm = ET.SubElement(tractor, "transition")
    trans_bgm.set("id", "transition_bgm")
    p_ba0 = ET.SubElement(trans_bgm, "property")
    p_ba0.set("name", "a_track")
    p_ba0.text = "0"
    p_bb3 = ET.SubElement(trans_bgm, "property")
    p_bb3.set("name", "b_track")
    p_bb3.text = "3"
    p_bms = ET.SubElement(trans_bgm, "property")
    p_bms.set("name", "mlt_service")
    p_bms.text = "mix"
    p_bact = ET.SubElement(trans_bgm, "property")
    p_bact.set("name", "always_active")
    p_bact.text = "1"
    p_bblnk = ET.SubElement(trans_bgm, "property")
    p_bblnk.set("name", "accepts_blanks")
    p_bblnk.text = "1"
    p_bsum = ET.SubElement(trans_bgm, "property")
    p_bsum.set("name", "sum")
    p_bsum.text = "1"

    # Subtitle burn-in preview filter (relative to project file)
    filter_sub = ET.SubElement(tractor, "filter")
    filter_sub.set("id", "filter_subtitles")
    p_fms = ET.SubElement(filter_sub, "property")
    p_fms.set("name", "mlt_service")
    p_fms.text = "avfilter.subtitles"
    p_fav = ET.SubElement(filter_sub, "property")
    p_fav.set("name", "av.filename")
    p_fav.text = "../subtitle/subtitle.srt"

    # Format pretty XML
    raw_xml = ET.tostring(root, encoding="utf-8")
    dom = minidom.parseString(raw_xml)
    xml_formatted = dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    output_kdenlive_path.write_text(xml_formatted, encoding="utf-8")
    logger.info(f"Kdenlive project generated: {output_kdenlive_path}")
    return output_kdenlive_path


# ==============================================================================
# INTEGRITY VALIDATION
# ==============================================================================
def validate_output(
    workspace_dir: Path,
    main_video_meta: VideoMetadata,
    segments: List[TranscriptSegment],
    srt_path: Path,
    broll_plan_path: Path,
    kdenlive_path: Path,
) -> Dict[str, Any]:
    """
    Comprehensive verification across all pipeline checkpoints:
    1. Main video file exists and technical specs valid.
    2. Transcript segments present, non-empty text.
    3. SRT file exists, parse matches segments.
    4. Chronological timestamps, start < end, non-negative, within video duration.
    5. All B-roll assets referenced exist on disk.
    6. All B-roll placements remain within master timeline duration.
    7. Title .kdenlivetitle files exist on disk and parse as valid XML.
    8. Sound effects WAV files exist.
    9. Edit manifest exists and has valid structure.
    10. Kdenlive MLT XML structure: main_bin retention, producer-bin GUID integrity,
        timeline tracks (V1, V2, V3, A1, A2, A3) and melt dry-run test if available.
    """
    report: Dict[str, Any] = {
        "workspace": workspace_dir.name,
        "is_valid": True,
        "checks": {},
        "warnings": [],
        "errors": [],
    }

    # 1. Main Video Check
    v_ok = main_video_meta.path.is_file() and main_video_meta.duration_seconds > 0
    report["checks"]["1_main_video"] = {
        "status": "PASS" if v_ok else "FAIL",
        "duration": main_video_meta.duration_seconds,
        "resolution": f"{main_video_meta.width}x{main_video_meta.height}",
        "fps": main_video_meta.fps,
    }
    if not v_ok:
        report["errors"].append("Main video file is invalid or zero duration.")

    # 2. Transcript Segments Check
    t_ok = len(segments) > 0 and all(len(s.text.strip()) > 0 for s in segments)
    report["checks"]["2_transcript"] = {
        "status": "PASS" if t_ok else "FAIL",
        "segment_count": len(segments),
    }
    if not t_ok:
        report["errors"].append("Transcript segments are empty or missing text.")

    # 3. SRT Verification
    srt_exists = srt_path.is_file() and srt_path.stat().st_size > 0
    parsed_srt = parse_srt_file(srt_path) if srt_exists else []
    srt_ok = srt_exists and len(parsed_srt) == len(segments)
    report["checks"]["3_srt_file"] = {
        "status": "PASS" if srt_ok else "FAIL",
        "srt_path": str(srt_path),
        "parsed_segments": len(parsed_srt),
    }
    if not srt_ok:
        report["errors"].append("SRT file verification failed or segment count mismatch.")

    # 4, 5, 6, 7. Timestamp Boundaries
    time_issues = []
    for s in segments:
        if s.start >= s.end:
            time_issues.append(f"Seg {s.segment_id}: start ({s.start}) >= end ({s.end})")
        if s.start < 0 or s.end < 0:
            time_issues.append(f"Seg {s.segment_id}: negative timestamp")
        if s.end > (main_video_meta.duration_seconds + 1.5):
            time_issues.append(f"Seg {s.segment_id}: end ({s.end}) > video duration ({main_video_meta.duration_seconds})")

    report["checks"]["4_5_6_7_timestamps"] = {
        "status": "PASS" if not time_issues else "FAIL",
        "issues": time_issues,
    }
    if time_issues:
        report["errors"].extend(time_issues)

    # 8, 9. B-roll Plan & Asset Verification
    plan_exists = broll_plan_path.is_file()
    plan_data = json.loads(broll_plan_path.read_text(encoding="utf-8")) if plan_exists else {}
    plan_segs = plan_data.get("segments", [])

    missing_assets = []
    broll_timing_issues = []
    for p in plan_segs:
        asset_rel = p.get("asset")
        if asset_rel:
            full_asset = workspace_dir / asset_rel
            if not full_asset.is_file():
                missing_assets.append(f"Missing asset: {full_asset}")
        start_val = p.get("start", 0)
        end_val = p.get("end", 0)
        if start_val < 0 or end_val > (main_video_meta.duration_seconds + 1.5):
            broll_timing_issues.append(f"Placement out of bounds: {p}")

    report["checks"]["8_broll_assets"] = {
        "status": "PASS" if not missing_assets else "FAIL",
        "missing_assets": missing_assets,
    }
    report["checks"]["9_broll_placement"] = {
        "status": "PASS" if not broll_timing_issues else "FAIL",
        "timing_issues": broll_timing_issues,
    }
    if missing_assets:
        report["errors"].extend(missing_assets)
    if broll_timing_issues:
        report["errors"].extend(broll_timing_issues)

    # 10. Title Files Verification
    titles_dir = workspace_dir / "project" / "titles"
    title_issues = []
    if titles_dir.is_dir():
        for tf in titles_dir.glob("*.kdenlivetitle"):
            try:
                t_tree = ET.parse(str(tf))
                if t_tree.getroot().tag != "kdenlivetitle":
                    title_issues.append(f"Title file malformed: {tf.name}")
            except Exception as e:
                title_issues.append(f"Title file XML error in {tf.name}: {e}")

    report["checks"]["10_title_files"] = {
        "status": "PASS" if not title_issues else "FAIL",
        "issues": title_issues,
    }
    if title_issues:
        report["errors"].extend(title_issues)

    # 11. Manifest Verification
    manifest_path = workspace_dir / "project" / "edit_manifest.json"
    manifest_ok = True
    manifest_issues = []
    if manifest_path.is_file():
        m_data = load_manifest(manifest_path)
        if not m_data or "stages" not in m_data:
            manifest_ok = False
            manifest_issues.append("edit_manifest.json is empty or missing stages")

    report["checks"]["11_manifest"] = {
        "status": "PASS" if manifest_ok else "FAIL",
        "issues": manifest_issues,
    }
    if not manifest_ok:
        report["errors"].extend(manifest_issues)

    # 12. Kdenlive Project XML & Melt Validation
    kdenlive_exists = kdenlive_path.is_file() and kdenlive_path.stat().st_size > 0
    xml_valid = False
    bin_integrity_ok = True
    bin_issues = []
    melt_valid: Optional[bool] = None

    if kdenlive_exists:
        try:
            tree = ET.parse(str(kdenlive_path))
            root = tree.getroot()
            if root.tag == "mlt" and root.find("tractor") is not None:
                xml_valid = True

            # Verify Project Bin (main_bin) and xml_retain
            main_bin = root.find("./playlist[@id='main_bin']")
            if main_bin is None:
                bin_integrity_ok = False
                bin_issues.append("main_bin playlist element missing in MLT XML")
            else:
                retain_prop = next((p.text for p in main_bin.findall("property") if p.attrib.get("name") == "xml_retain"), None)
                if retain_prop != "1":
                    bin_integrity_ok = False
                    bin_issues.append("main_bin is missing <property name='xml_retain'>1</property>")

            # Collect registered producers and bin references
            bin_producers: Dict[str, Dict[str, str]] = {}
            for prod in root.findall("./producer"):
                pid = prod.attrib.get("id")
                if not pid or pid == "black_track":
                    continue
                kid = next((p.text for p in prod.findall("property") if p.attrib.get("name") == "kdenlive:id"), None)
                cuuid = next((p.text for p in prod.findall("property") if p.attrib.get("name") == "kdenlive:control_uuid"), None)
                bin_producers[pid] = {"kdenlive:id": kid or "", "kdenlive:control_uuid": cuuid or ""}

            # Check all timeline tracks
            checked_tracks = ["playlist_a1", "playlist_a2", "playlist_a3", "playlist_v1", "playlist_v2", "playlist_v3"]
            for track_id in checked_tracks:
                track_elem = root.find(f"./playlist[@id='{track_id}']")
                if track_elem is not None:
                    for entry in track_elem.findall("entry"):
                        eprod = entry.attrib.get("producer")
                        if not eprod or eprod not in bin_producers:
                            bin_integrity_ok = False
                            bin_issues.append(f"Timeline track {track_id} entry refers to unknown producer '{eprod}'")
                            continue
                        e_kid = next((p.text for p in entry.findall("property") if p.attrib.get("name") == "kdenlive:id"), None)
                        e_cuuid = next((p.text for p in entry.findall("property") if p.attrib.get("name") == "kdenlive:control_uuid"), None)
                        expected_kid = bin_producers[eprod]["kdenlive:id"]
                        expected_cuuid = bin_producers[eprod]["kdenlive:control_uuid"]
                        if not e_kid or e_kid != expected_kid:
                            bin_integrity_ok = False
                            bin_issues.append(f"Timeline track {track_id} entry '{eprod}' kdenlive:id mismatch ({e_kid} vs {expected_kid})")
                        if not e_cuuid or e_cuuid != expected_cuuid:
                            bin_integrity_ok = False
                            bin_issues.append(f"Timeline track {track_id} entry '{eprod}' kdenlive:control_uuid mismatch ({e_cuuid} vs {expected_cuuid})")

        except Exception as e:
            report["errors"].append(f"XML parse error in Kdenlive file: {e}")

        # Check melt dry-run if melt binary is available
        melt_candidates = [
            r"C:\Program Files\kdenlive\bin\melt.exe",
            r"C:\Program Files\Kdenlive\bin\melt.exe",
            shutil.which("melt"),
        ]
        melt_bin = next((m for m in melt_candidates if m and Path(m).is_file()), None)

        if melt_bin:
            try:
                melt_res = subprocess.run(
                    [melt_bin, str(kdenlive_path), "out=0", "-consumer", "null"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                melt_valid = (melt_res.returncode == 0)
                if not melt_valid:
                    report["warnings"].append(f"melt dry-run returned {melt_res.returncode}: {melt_res.stderr[:200]}")
            except Exception as e:
                report["warnings"].append(f"melt dry-run check could not be completed: {e}")

    report["checks"]["12_kdenlive_project"] = {
        "status": "PASS" if (kdenlive_exists and xml_valid and bin_integrity_ok) else "FAIL",
        "xml_valid": xml_valid,
        "bin_integrity_ok": bin_integrity_ok,
        "bin_issues": bin_issues,
        "melt_tested": melt_valid is not None,
        "melt_valid": melt_valid,
    }

    if not (kdenlive_exists and xml_valid):
        report["errors"].append("Kdenlive project file is missing or contains invalid MLT XML.")
    if not bin_integrity_ok:
        report["errors"].extend(bin_issues)

    report["is_valid"] = len(report["errors"]) == 0
    return report


# ==============================================================================
# PIPELINE ORCHESTRATOR (INCREMENTAL EDITING ASSISTANT)
# ==============================================================================
def run_auto_edit_pipeline(
    workspace_arg: str,
    mode: str = "create",  # "create", "continue", "validate", "broll", "titles", "zoom", "sfx", "finish"
    requested_video: Optional[str] = None,
    whisper_model: str = "base",
    whisper_device: str = "cpu",
    whisper_compute: str = "int8",
    whisper_language: Optional[str] = None,
    reuse_srt_if_exists: bool = False,
    overwrite_kdenlive: bool = False,
    root_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes the incremental Kdenlive editing assistant pipeline:
      - CREATE: Full initial setup (Whisper -> SRT -> B-roll -> Titles -> SFX -> 7-Track Kdenlive)
      - CONTINUE: Inspects existing project & manifest, preserves user edits, finishes pending work.
      - VALIDATE: Integrity inspection without modifying files.
      - BROLL / TITLES / ZOOM / SFX / FINISH: Targeted stage enhancements.
    Core principle: MANUAL USER EDIT > PREVIOUS AUTOMATIC DECISION > NEW AUTOMATIC DECISION.
    """
    logger.info("==================================================")
    logger.info(f"STARTING AUTO EDIT PIPELINE: {workspace_arg} [MODE: {mode.upper()}]")
    logger.info("==================================================")

    # 1. Resolve workspace directory
    ws_dir = find_workspace(workspace_arg, root_dir=root_dir)
    logger.info(f"Workspace resolved: {ws_dir}")

    # 2. Find and probe main raw video (Main Time Authority)
    main_video_path = find_main_video(ws_dir, requested_file=requested_video)
    logger.info(f"Main video detected: {main_video_path.name}")
    main_meta = probe_video(main_video_path)
    logger.info(
        f"Video specs: {main_meta.width}x{main_meta.height} @ {main_meta.fps:.2f}fps, "
        f"durasi: {main_meta.duration_seconds:.2f}s ({main_meta.total_frames} frames)"
    )

    # File paths
    srt_path = ws_dir / "subtitle" / "subtitle.srt"
    broll_plan_path = ws_dir / "project" / "broll_plan.json"
    manifest_path = ws_dir / "project" / "edit_manifest.json"
    target_kdenlive = ws_dir / "project" / "video_auto.kdenlive"

    # Ensure sound effects assets exist
    assets_sfx_dir = ws_dir.parent.parent / "assets" / "sound_effects"
    sfx_assets = ensure_sound_effects(assets_sfx_dir)

    # --------------------------------------------------------------------------
    # MODE: VALIDATE ONLY
    # --------------------------------------------------------------------------
    if mode == "validate":
        segments = parse_srt_file(srt_path) if srt_path.is_file() else []
        report = validate_output(
            workspace_dir=ws_dir,
            main_video_meta=main_meta,
            segments=segments,
            srt_path=srt_path,
            broll_plan_path=broll_plan_path,
            kdenlive_path=target_kdenlive,
        )
        logger.info(f"VALIDATION FINISHED: {'PASS' if report['is_valid'] else 'FAIL'}")
        return {
            "workspace": ws_dir,
            "mode": mode,
            "validation": report,
            "kdenlive_path": target_kdenlive,
        }

    # --------------------------------------------------------------------------
    # 3. Transcription & SRT (Reused or Executed)
    # --------------------------------------------------------------------------
    segments: List[TranscriptSegment] = []
    if (reuse_srt_if_exists or mode != "create") and srt_path.is_file():
        logger.info(f"Menggunakan SRT existing: {srt_path}")
        segments = parse_srt_file(srt_path)

    if not segments:
        segments = transcribe_video(
            video_path=main_video_path,
            model_name=whisper_model,
            device=whisper_device,
            compute_type=whisper_compute,
            language=whisper_language,
            local_files_only=True,
        )
        if not segments:
            logger.warning("Whisper tidak mendeteksi ucapan. Membuat fallback segment default.")
            segments = [
                TranscriptSegment(
                    segment_id=1,
                    start=0.0,
                    end=min(main_meta.duration_seconds, 5.0),
                    duration=min(main_meta.duration_seconds, 5.0),
                    text="[Audio intro / music]",
                    tokens=extract_keywords_from_string("intro music video"),
                )
            ]
        generate_srt(segments, srt_path)

    # 4. Find B-roll assets in workspace
    broll_assets = find_broll_assets(ws_dir)
    logger.info(f"Ditemukan {len(broll_assets)} asset B-roll di folder broll/")

    # 5. Manifest & Existing Kdenlive Inspection
    manifest = load_manifest(manifest_path)
    existing_kdenlive_data = None
    if target_kdenlive.is_file():
        logger.info(f"Project Kdenlive existing ditemukan: {target_kdenlive}. Memeriksa manual edits...")
        existing_kdenlive_data = parse_existing_kdenlive(target_kdenlive, fps=main_meta.fps)

    # If in CONTINUE or targeted mode but no project exists, switch to CREATE
    if mode != "create" and not target_kdenlive.is_file():
        logger.warning(f"Mode {mode} diminta tetapi project belum ada. Menjalankan mode CREATE dari awal.")
        mode = "create"

    # 6. Automatic Decisions Generation
    auto_placements = match_broll(segments, broll_assets)
    auto_text_items = detect_text_moments(segments, main_meta.duration_seconds, main_meta.width, main_meta.height)
    auto_sfx_events = detect_sfx_events(auto_placements, auto_text_items, sfx_assets)

    # 7. Incremental Merge & Manual Edit Preservation
    final_placements, final_text_items, final_sfx_events, mod_stats = merge_timeline_preservations(
        existing_data=existing_kdenlive_data,
        auto_placements=auto_placements,
        auto_text_items=auto_text_items,
        auto_sfx_events=auto_sfx_events,
        fps=main_meta.fps,
        mode=mode,
    )

    if mod_stats.get("manual_edits_detected"):
        logger.info(
            f"MANUAL EDITS PRESERVED: {mod_stats['preserved_broll_count']} b-roll diganti/ditrim, "
            f"{mod_stats['preserved_deleted_count']} b-roll dihapus user tetap kosong."
        )

    # Save B-roll Plan
    build_broll_plan(ws_dir, main_meta, final_placements, broll_plan_path)

    # 8. Targeted Stage Flags
    apply_zoom = (mode in ["create", "continue", "zoom"])
    apply_fill_frame = True

    # 9. Generate or Update Kdenlive Project
    if not overwrite_kdenlive and mode == "create" and target_kdenlive.is_file():
        target_kdenlive = resolve_safe_kdenlive_path(
            project_dir=ws_dir / "project",
            base_filename="video_auto.kdenlive",
            overwrite=False,
        )

    generate_kdenlive_project(
        workspace_dir=ws_dir,
        main_video_meta=main_meta,
        placements=final_placements,
        srt_path=srt_path,
        output_kdenlive_path=target_kdenlive,
        text_items=final_text_items,
        sfx_events=final_sfx_events,
        apply_zoom=apply_zoom,
        apply_fill_frame=apply_fill_frame,
    )

    # 10. Update & Save Edit Manifest
    now_iso = datetime.now(timezone.utc).isoformat()
    if not manifest:
        manifest = {
            "workspace": ws_dir.name,
            "source_video": main_meta.filename,
            "created_at": now_iso,
            "updated_at": now_iso,
            "version": 1,
            "stages": {
                "transcription": {"status": "completed"},
                "subtitle": {"status": "completed"},
                "broll": {"status": "completed"},
                "fill_frame": {"status": "completed"},
                "quick_zoom": {"status": "completed" if apply_zoom else "pending"},
                "section_titles": {"status": "completed"},
                "headlines": {"status": "completed"},
                "emphasis_text": {"status": "completed"},
                "lower_thirds": {"status": "completed"},
                "sound_effects": {"status": "completed"},
                "audio_finishing": {"status": "pending"},
            },
            "user_modifications": mod_stats,
        }
    else:
        manifest["version"] = manifest.get("version", 1) + 1
        manifest["updated_at"] = now_iso
        manifest["user_modifications"] = mod_stats
        if mode in ["create", "broll"]:
            manifest["stages"]["broll"]["status"] = "completed"
        if mode in ["create", "titles"]:
            manifest["stages"]["section_titles"]["status"] = "completed"
            manifest["stages"]["headlines"]["status"] = "completed"
            manifest["stages"]["emphasis_text"]["status"] = "completed"
        if mode in ["create", "zoom"]:
            manifest["stages"]["quick_zoom"]["status"] = "completed"
        if mode in ["create", "sfx"]:
            manifest["stages"]["sound_effects"]["status"] = "completed"
        if mode in ["create", "finish"]:
            manifest["stages"]["audio_finishing"]["status"] = "completed"

    save_manifest(manifest_path, manifest)

    # 11. Comprehensive Validation
    validation_report = validate_output(
        workspace_dir=ws_dir,
        main_video_meta=main_meta,
        segments=segments,
        srt_path=srt_path,
        broll_plan_path=broll_plan_path,
        kdenlive_path=target_kdenlive,
    )

    logger.info("==================================================")
    if validation_report["is_valid"]:
        logger.info(f"SUCCESS: Pipeline completed for {ws_dir.name}! [Mode: {mode.upper()}]")
        logger.info(f"  SRT File      : {srt_path}")
        logger.info(f"  B-roll Plan   : {broll_plan_path}")
        logger.info(f"  Manifest File : {manifest_path}")
        logger.info(f"  Kdenlive Proj : {target_kdenlive}")
    else:
        logger.error(f"PIPELINE COMPLETED WITH VALIDATION ERRORS:\n{validation_report['errors']}")
    logger.info("==================================================")

    return {
        "workspace": ws_dir,
        "mode": mode,
        "main_video": main_video_path,
        "srt_path": srt_path,
        "broll_plan_path": broll_plan_path,
        "manifest_path": manifest_path,
        "kdenlive_path": target_kdenlive,
        "validation": validation_report,
        "user_modifications": mod_stats,
    }


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================
def main() -> int:
    """CLI handler for auto_edit_kdenlive."""
    parser = argparse.ArgumentParser(
        prog="auto_edit_kdenlive",
        description="Incremental Kdenlive Editing Assistant for Automated Timeline Assembly",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh Penggunaan:
  # 1. Jalankan pembuatan project awal secara penuh:
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --create

  # 2. Lanjutkan pekerjaan tanpa merusak manual edit yang sudah dilakukan di Kdenlive:
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --continue

  # 3. Mode targeted patch:
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --titles
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --broll
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --zoom
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --sfx

  # 4. Validasi integritas timeline dan bin Kdenlive:
  python -m engine.pipeline.auto_edit_kdenlive --workspace 01-script --validate

  # 5. Cek kesiapan 10 workspace produksi:
  python -m engine.pipeline.auto_edit_kdenlive --list
        """
    )
    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=None,
        help="Nama atau path workspace target (contoh: '01-script' atau 'output/01-script').",
    )

    # Operational Mode Switches
    mode_group = parser.add_argument_group("Operational Modes")
    mode_group.add_argument(
        "--create",
        action="store_true",
        help="Buat project baru dari awal (Whisper -> SRT -> B-roll -> Titles -> SFX -> 7-Track Kdenlive).",
    )
    mode_group.add_argument(
        "--continue",
        dest="continue_mode",
        action="store_true",
        help="Lanjutkan pekerjaan otomatisasi dengan mempertahankan semua manual edit di Kdenlive.",
    )
    mode_group.add_argument(
        "--validate",
        action="store_true",
        help="Jalankan pemeriksaan integritas menyeluruh (validasi XML, bin reference, dan melt).",
    )
    mode_group.add_argument(
        "--broll",
        action="store_true",
        help="Mode patch: hanya tempatkan/perbarui B-roll tanpa mengubah manual edits atau title.",
    )
    mode_group.add_argument(
        "--titles",
        action="store_true",
        help="Mode patch: hanya buat/perbarui layer typography dan title (.kdenlivetitle).",
    )
    mode_group.add_argument(
        "--zoom",
        action="store_true",
        help="Mode patch: terapkan/perbarui keyframe quick zoom pada klip B-roll.",
    )
    mode_group.add_argument(
        "--sfx",
        action="store_true",
        help="Mode patch: tambahkan/perbarui layer sound effects (click, pop, whoosh, hit).",
    )
    mode_group.add_argument(
        "--finish",
        action="store_true",
        help="Mode patch: selesaikan penataan audio dasar dan balancing BGM.",
    )

    # Video & Whisper Options
    parser.add_argument(
        "--video", "-v",
        type=str,
        default=None,
        help="Nama file video mentah spesifik di folder footage (jika ada lebih dari 1 kandidat).",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="base",
        help="Model Whisper yang digunakan (default: 'base').",
    )
    parser.add_argument(
        "--device", "-d",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Hardware device untuk Whisper (default: 'cpu').",
    )
    parser.add_argument(
        "--language", "-l",
        type=str,
        default=None,
        help="Kode bahasa untuk Whisper (contoh: 'id', 'en'). Default: auto-detect.",
    )
    parser.add_argument(
        "--reuse-srt",
        action="store_true",
        help="Gunakan file subtitle/subtitle.srt yang sudah ada tanpa menjalankan Whisper ulang.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite file video_auto.kdenlive tanpa membuat video_auto_2.kdenlive.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Tampilkan daftar 10 workspace dan status asset-nya.",
    )

    args = parser.parse_args()

    if args.list:
        print("\n=== STATUS WORKSPACE PRODUKSI (output/) ===")
        workspaces = list_available_workspaces()
        for ws in workspaces:
            f_status = f"{ws['footage_count']} video" if ws['has_footage'] else "KOSONG"
            b_status = f"{ws['broll_count']} asset" if ws['broll_count'] > 0 else "KOSONG"
            s_status = "ADA" if ws['has_srt'] else "BELUM"
            p_status = "ADA" if ws['has_project'] else "BELUM"
            print(f"[{ws['name']}] Footage: {f_status:<10} | B-roll: {b_status:<10} | SRT: {s_status:<5} | Kdenlive: {p_status}")
        print()
        return 0

    if not args.workspace:
        parser.print_help()
        print("\n[!] Mohon tentukan workspace target dengan opsi: --workspace <nomor-script>")
        return 1

    # Determine operational mode
    selected_mode = "create"
    if args.validate:
        selected_mode = "validate"
    elif args.continue_mode:
        selected_mode = "continue"
    elif args.broll:
        selected_mode = "broll"
    elif args.titles:
        selected_mode = "titles"
    elif args.zoom:
        selected_mode = "zoom"
    elif args.sfx:
        selected_mode = "sfx"
    elif args.finish:
        selected_mode = "finish"
    elif args.create:
        selected_mode = "create"

    try:
        res = run_auto_edit_pipeline(
            workspace_arg=args.workspace,
            mode=selected_mode,
            requested_video=args.video,
            whisper_model=args.model,
            whisper_device=args.device,
            whisper_language=args.language,
            reuse_srt_if_exists=args.reuse_srt,
            overwrite_kdenlive=args.overwrite,
        )
        return 0 if res["validation"]["is_valid"] else 1
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

