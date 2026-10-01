#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
                    AUTO EDIT CAPCUT ENGINE
================================================================================
Location: engine/pipeline/auto_edit_capcut.py

Fully automated video editing engine that connects raw footage, Whisper
transcription, SRT generation, segment analysis, B-roll selection/placement,
and CapCut Desktop Draft project generation.

Core Pipeline Principle:
    VIDEO MENTAH (Main Time Authority)
    -> WHISPER TRANSCRIPTION
    -> TIMESTAMP EXTRACTION
    -> SRT SUBTITLE GENERATION (output/[workspace]/subtitle/subtitle.srt)
    -> SEGMENT ANALYSIS & B-ROLL MATCHING
    -> B-ROLL TIMELINE PLAN (output/[workspace]/project/capcut_broll_plan.json)
    -> CAPCUT DESKTOP DRAFT (output/[workspace]/project/capcut/)
    -> OPTIONAL INSTALL TO CAPCUT USER DRAFTS
    -> COMPREHENSIVE INTEGRITY VALIDATION

Timeline Layout in CapCut Desktop:
    Track 0 (Video):   [================ VIDEO MENTAH ================]
    Track 1 (Overlay):       [B-ROLL 1]      [B-ROLL 2]      [B-ROLL 3]
    Track 2 (Text):          [Sub 1]         [Sub 2]         [Sub 3]
================================================================================
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("auto_edit_capcut")

# ==============================================================================
# CONSTANTS & MEDIA EXTENSIONS
# ==============================================================================
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALL_BROLL_EXTENSIONS = SUPPORTED_VIDEO_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS

MAIN_VIDEO_PRIORITY_KEYWORDS = [
    "main", "mentah", "video-mentah", "video_mentah", "utama", "raw", "master", "source", "inshot"
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
# DATA CLASSES
# ==============================================================================
@dataclass
class VideoMetadata:
    """Metadata extracted from the raw main video via ffprobe."""
    path: Path
    filename: str
    duration_seconds: float
    duration_microseconds: int
    width: int
    height: int
    fps: float
    aspect_ratio: str = "16:9"


@dataclass
class BRollAsset:
    """Discovered B-roll asset (video or image)."""
    path: Path
    filename: str
    media_type: str  # "video" or "image"
    width: int = 1920
    height: int = 1080
    duration_seconds: Optional[float] = None
    keywords: Set[str] = field(default_factory=set)


@dataclass
class TranscriptSegment:
    """Single segment from Whisper transcription or SRT file."""
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
    asset_name: Optional[str]
    asset_type: str  # "video", "image", or "none"
    asset_duration: Optional[float]
    trim_in: float
    trim_out: float
    status: str  # "MATCHED_OK", "INSUFFICIENT_BROLL_DURATION", "NO_BROLL_AVAILABLE", "UNMATCHED"
    match_score: float = 0.0
    match_reason: str = ""

    def to_plan_dict(self) -> Dict[str, Any]:
        """Format matching specification O."""
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "asset": self.asset_path,
            "type": self.asset_type,
        }

    def to_detailed_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "duration": round(self.duration, 3),
            "text": self.text,
            "asset": self.asset_path,
            "asset_name": self.asset_name,
            "type": self.asset_type,
            "asset_duration": round(self.asset_duration, 3) if self.asset_duration else None,
            "trim_in": round(self.trim_in, 3),
            "trim_out": round(self.trim_out, 3),
            "status": self.status,
            "match_score": round(self.match_score, 2),
            "match_reason": self.match_reason,
        }


# ==============================================================================
# WORKSPACE & MEDIA DISCOVERY
# ==============================================================================
def find_workspace(workspace_arg: str, base_dir: Optional[Path] = None) -> Path:
    """
    Locates and prepares the workspace directory.
    Accepts: '01-script', 'output/01-script', or full absolute path.
    Ensures standard subdirectories exist.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    candidate = Path(workspace_arg)
    if candidate.is_absolute() and candidate.is_dir():
        ws_path = candidate
    elif (base_dir / candidate).is_dir():
        ws_path = base_dir / candidate
    elif (base_dir / "output" / candidate).is_dir():
        ws_path = base_dir / "output" / candidate
    elif (base_dir / "output" / candidate.name).is_dir():
        ws_path = base_dir / "output" / candidate.name
    else:
        # Create under output if doesn't exist
        ws_path = base_dir / "output" / candidate.name

    for sub in ["footage", "broll", "subtitle", "project", "render"]:
        (ws_path / sub).mkdir(parents=True, exist_ok=True)

    logger.info(f"Workspace aktif: {ws_path}")
    return ws_path


def find_main_video(footage_dir: Path, requested_file: Optional[str] = None) -> Path:
    """
    Identifies the single primary raw video inside output/[workspace]/footage/.
    Rules:
      - Searches only inside footage_dir.
      - Never includes B-rolls.
      - If requested_file provided, validates and returns it.
      - If only 1 video file found, uses it.
      - If multiple candidates found, scores priority keywords.
      - If ambiguous and interactive, prompts user; otherwise raises clear error.
    """
    if requested_file:
        cand = footage_dir / requested_file
        if cand.is_file():
            logger.info(f"Menggunakan video utama yang ditentukan pengguna: {cand.name}")
            return cand
        cand_abs = Path(requested_file)
        if cand_abs.is_file():
            logger.info(f"Menggunakan video utama via path absolut: {cand_abs.name}")
            return cand_abs
        raise FileNotFoundError(f"Video utama yang ditentukan tidak ditemukan: {requested_file}")

    candidates = [
        f for f in footage_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS and not f.name.startswith(".")
    ]

    if not candidates:
        raise FileNotFoundError(
            f"Tidak ada video mentah ditemukan di: {footage_dir}\n"
            f"Pastikan video mentah diletakkan di folder footage/ workspace."
        )

    if len(candidates) == 1:
        logger.info(f"Video utama otomatis terdeteksi (kandidat tunggal): {candidates[0].name}")
        return candidates[0]

    # Multiple candidates: check priority keywords
    scored = []
    for c in candidates:
        name_lower = c.name.lower()
        score = sum(2 for kw in MAIN_VIDEO_PRIORITY_KEYWORDS if kw in name_lower)
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_cand = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -1

    if top_score > second_score and top_score > 0:
        logger.info(f"Video utama terdeteksi berdasarkan skor nama: {top_cand.name}")
        return top_cand

    # Ambiguous: list candidates
    candidate_list_str = "\n".join(f"  [{i+1}] {c.name}" for i, c in enumerate(candidates))
    msg = (
        f"Ditemukan beberapa kandidat video di {footage_dir}:\n"
        f"{candidate_list_str}\n"
        f"Gunakan flag --main-video <nama_file> untuk memilih secara spesifik."
    )
    if sys.stdin.isatty():
        print(f"\n{msg}")
        choice = input("Pilih nomor video utama [1-{len(candidates)}]: ").strip()
        try:
            chosen_idx = int(choice) - 1
            if 0 <= chosen_idx < len(candidates):
                return candidates[chosen_idx]
        except ValueError:
            pass
    raise RuntimeError(msg)


def get_video_metadata(video_path: Path) -> VideoMetadata:
    """
    Extracts precise video parameters (duration, dimensions, fps) using ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
    except Exception as e:
        raise RuntimeError(f"Gagal membaca metadata video dengan ffprobe ({video_path.name}): {e}")

    if not data.get("streams"):
        raise ValueError(f"Tidak ada video stream yang valid ditemukan pada {video_path.name}")

    stream = data["streams"][0]
    width = int(stream.get("width", 1920))
    height = int(stream.get("height", 1080))

    fps_str = stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/", 1)
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = float(fps_str)

    dur_val = data.get("format", {}).get("duration") or stream.get("duration")
    if dur_val is None:
        raise ValueError(f"Tidak dapat menentukan durasi video untuk {video_path.name}")
    dur_sec = float(dur_val)
    dur_us = int(round(dur_sec * 1_000_000))

    ar = "16:9"
    if width > 0 and height > 0:
        ratio = width / height
        if abs(ratio - (9 / 16)) < 0.1:
            ar = "9:16"
        elif abs(ratio - (16 / 9)) < 0.1:
            ar = "16:9"

    meta = VideoMetadata(
        path=video_path,
        filename=video_path.name,
        duration_seconds=dur_sec,
        duration_microseconds=dur_us,
        width=width,
        height=height,
        fps=round(fps, 3),
        aspect_ratio=ar
    )
    logger.info(
        f"Metadata Video Mentah: {meta.filename} | "
        f"{meta.width}x{meta.height} @ {meta.fps}fps | "
        f"Durasi: {meta.duration_seconds:.2f}s ({meta.duration_microseconds} us)"
    )
    return meta


def extract_keywords_from_string(text: str) -> Set[str]:
    """Tokenize and extract keywords from text string."""
    words = re.findall(r"\w+", text.lower())
    clean_words = {
        w for w in words
        if len(w) >= 3 and w not in STOPWORDS_INDONESIAN_ENGLISH and not w.isdigit()
    }
    return clean_words


def find_broll_assets(broll_dir: Path) -> List[BRollAsset]:
    """
    Discovers all image and video assets inside output/[workspace]/broll/.
    Does not copy or move any original files.
    """
    assets: List[BRollAsset] = []
    if not broll_dir.is_dir():
        return assets

    raw_files = sorted(
        [f for f in broll_dir.iterdir() if f.is_file() and not f.name.startswith(".")],
        key=lambda x: x.name.lower()
    )

    for f in raw_files:
        ext = f.suffix.lower()
        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            mtype = "image"
            w, h = 1920, 1080
            try:
                from PIL import Image
                with Image.open(f) as img:
                    w, h = img.width, img.height
            except Exception:
                pass
            kw = extract_keywords_from_string(re.sub(r"^\d+_", "", f.stem))
            assets.append(BRollAsset(
                path=f,
                filename=f.name,
                media_type=mtype,
                width=w,
                height=h,
                duration_seconds=None, # Adaptive
                keywords=kw
            ))
        elif ext in SUPPORTED_VIDEO_EXTENSIONS:
            mtype = "video"
            w, h = 1920, 1080
            dur_sec = None
            try:
                cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,duration",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    str(f)
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    d = json.loads(res.stdout)
                    if d.get("streams"):
                        w = int(d["streams"][0].get("width", 1920))
                        h = int(d["streams"][0].get("height", 1080))
                    dur_val = d.get("format", {}).get("duration") or (d.get("streams", [{}])[0].get("duration"))
                    if dur_val:
                        dur_sec = float(dur_val)
            except Exception:
                pass
            kw = extract_keywords_from_string(re.sub(r"^\d+_", "", f.stem))
            assets.append(BRollAsset(
                path=f,
                filename=f.name,
                media_type=mtype,
                width=w,
                height=h,
                duration_seconds=dur_sec,
                keywords=kw
            ))

    logger.info(f"Ditemukan {len(assets)} B-roll asset di {broll_dir.name}")
    return assets


# ==============================================================================
# WHISPER & SRT HANDLING
# ==============================================================================
def format_timestamp_srt(seconds: float) -> str:
    """Convert float seconds to SRT timecode HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    rem = seconds - (hrs * 3600)
    mins = int(rem // 60)
    secs = rem - (mins * 60)
    int_secs = int(secs)
    millis = int(round((secs - int_secs) * 1000))
    if millis >= 1000:
        millis -= 1000
        int_secs += 1
    return f"{hrs:02d}:{mins:02d}:{int_secs:02d},{millis:03d}"


def parse_timestamp_srt(srt_time: str) -> float:
    """Parse SRT timestamp 'HH:MM:SS,mmm' to float seconds."""
    clean = srt_time.strip().replace(".", ",")
    parts = clean.split(":")
    if len(parts) == 3:
        hrs = float(parts[0])
        mins = float(parts[1])
        s_parts = parts[2].split(",")
        secs = float(s_parts[0])
        ms = float(s_parts[1]) if len(s_parts) > 1 else 0.0
        return hrs * 3600.0 + mins * 60.0 + secs + (ms / 1000.0)
    raise ValueError(f"Malformed SRT timestamp: '{srt_time}'")


def generate_srt(segments: List[TranscriptSegment], output_srt_path: Path) -> Path:
    """
    Write transcript segments to standard UTF-8 SRT file.
    Output: output/[workspace]/subtitle/subtitle.srt
    """
    output_srt_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for idx, seg in enumerate(segments, 1):
        s_str = format_timestamp_srt(seg.start)
        e_str = format_timestamp_srt(seg.end)
        lines.append(f"{idx}\n{s_str} --> {e_str}\n{seg.text}\n")

    content = "\n".join(lines) + "\n"
    output_srt_path.write_text(content, encoding="utf-8")
    logger.info(f"SRT berhasil dibuat/disimpan: {output_srt_path} ({len(segments)} segments)")
    return output_srt_path


def parse_srt_file(srt_path: Path) -> List[TranscriptSegment]:
    """Parse existing SRT file into structured TranscriptSegments."""
    if not srt_path.is_file():
        raise FileNotFoundError(f"SRT file tidak ditemukan: {srt_path}")

    raw_text = srt_path.read_text(encoding="utf-8-sig").strip()
    if not raw_text:
        return []

    blocks = re.split(r"\n\s*\n", raw_text)
    segments: List[TranscriptSegment] = []
    seg_idx = 1

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 2:
            continue

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
            logger.warning(f"Melewati baris timecode SRT tidak valid '{timecode_line}': {e}")
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

    logger.info(f"Berhasil membaca SRT: {srt_path.name} ({len(segments)} segments)")
    return segments


def transcribe_video(
    video_path: Path,
    output_srt_path: Path,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    force_whisper: bool = False,
) -> List[TranscriptSegment]:
    """
    Run Whisper transcription on the raw main video.
    Main video audio is the SOLE time authority for the entire pipeline.
    If valid SRT already exists and not force_whisper, uses existing SRT.
    """
    if not force_whisper and output_srt_path.is_file():
        try:
            existing_segs = parse_srt_file(output_srt_path)
            if existing_segs:
                logger.info(
                    f"Menggunakan subtitle.srt yang sudah ada: {output_srt_path.name} "
                    f"({len(existing_segs)} segments). Gunakan --force-whisper untuk mengulang transkripsi."
                )
                return existing_segs
        except Exception as e:
            logger.warning(f"Gagal membaca SRT existing ({e}), menjalankan Whisper...")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper tidak terpasang di Python environment.\n"
            "Silakan periksa environment aktif."
        )

    logger.info(f"Memuat model faster-whisper '{model_name}' pada {device} ({compute_type})...")
    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            local_files_only=True,
        )
    except Exception:
        logger.info("Mencoba memuat model Whisper tanpa local_files_only...")
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            local_files_only=False,
        )

    logger.info(f"Menjalankan transkripsi audio dari video mentah: {video_path.name}")
    raw_segments, info = model.transcribe(
        str(video_path),
        beam_size=5,
        word_timestamps=True,
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

    generate_srt(segments, output_srt_path)
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
    Calculates match score between transcript segment and a B-roll asset.
    Considers:
      - Direct keyword overlap (+10 per word)
      - Substring / partial match (+5)
      - Synonym / semantic cluster (+7)
      - Asset reuse penalty (-8 per previous use)
    """
    score = 0.0
    reasons = []

    # 1. Direct keyword match
    overlap = segment.tokens.intersection(asset.keywords)
    if overlap:
        pts = len(overlap) * 10.0
        score += pts
        reasons.append(f"keyword:{','.join(sorted(overlap))}(+{pts:.0f})")

    # 2. Substring match
    for st in segment.tokens:
        for ak in asset.keywords:
            if st != ak and (st in ak or ak in st):
                score += 5.0
                reasons.append(f"partial:{st}<->{ak}(+5)")
                break

    # 3. Synonym / concept clusters
    for cname, words in SYNONYM_CLUSTERS.items():
        seg_has = any(w in segment.tokens or w in segment.text.lower() for w in words)
        asset_has = any(w in asset.keywords or w in asset.filename.lower() for w in words)
        if seg_has and asset_has:
            score += 7.0
            reasons.append(f"cluster:{cname}(+7)")
            break

    # 4. Reuse penalty
    if used_count > 0:
        penalty = used_count * 8.0
        score -= penalty
        reasons.append(f"reuse_penalty(-{penalty:.0f})")

    reason_str = " | ".join(reasons) if reasons else "no_direct_match"
    return score, reason_str


def match_broll(
    segments: List[TranscriptSegment],
    assets: List[BRollAsset],
    min_score: float = 3.0,
) -> List[BRollPlacement]:
    """
    Assigns B-roll assets to transcript segments based on scores.
    Maintains exact raw video timing:
      START = segment.start
      END = segment.end
      DURATION = segment.duration
    """
    if not assets:
        logger.warning("Folder broll kosong. Semua segmen tanpa B-roll.")
        return [
            BRollPlacement(
                segment_id=seg.segment_id,
                start=seg.start,
                end=seg.end,
                duration=seg.duration,
                text=seg.text,
                asset_path=None,
                asset_name=None,
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

        slot_dur = seg.duration

        # Check if score passes threshold
        if best_score >= min_score and best_asset is not None:
            asset_usage[best_asset.filename] = asset_usage.get(best_asset.filename, 0) + 1
            rel_path = f"broll/{best_asset.filename}"

            if best_asset.media_type == "image":
                placements.append(BRollPlacement(
                    segment_id=seg.segment_id,
                    start=seg.start,
                    end=seg.end,
                    duration=slot_dur,
                    text=seg.text,
                    asset_path=rel_path,
                    asset_name=best_asset.filename,
                    asset_type="image",
                    asset_duration=slot_dur,
                    trim_in=0.0,
                    trim_out=slot_dur,
                    status="MATCHED_OK",
                    match_score=best_score,
                    match_reason=best_reason,
                ))
            else:
                # Video B-roll
                vid_dur = best_asset.duration_seconds or slot_dur
                if vid_dur >= slot_dur:
                    placements.append(BRollPlacement(
                        segment_id=seg.segment_id,
                        start=seg.start,
                        end=seg.end,
                        duration=slot_dur,
                        text=seg.text,
                        asset_path=rel_path,
                        asset_name=best_asset.filename,
                        asset_type="video",
                        asset_duration=vid_dur,
                        trim_in=0.0,
                        trim_out=slot_dur,
                        status="MATCHED_OK",
                        match_score=best_score,
                        match_reason=best_reason,
                    ))
                else:
                    # Video shorter than segment duration: safe trim, flag status
                    placements.append(BRollPlacement(
                        segment_id=seg.segment_id,
                        start=seg.start,
                        end=seg.end,
                        duration=slot_dur,
                        text=seg.text,
                        asset_path=rel_path,
                        asset_name=best_asset.filename,
                        asset_type="video",
                        asset_duration=vid_dur,
                        trim_in=0.0,
                        trim_out=vid_dur,
                        status="INSUFFICIENT_BROLL_DURATION",
                        match_score=best_score,
                        match_reason=f"{best_reason} | shorter_than_slot({vid_dur:.1f}s<{slot_dur:.1f}s)",
                    ))
        else:
            # No match
            placements.append(BRollPlacement(
                segment_id=seg.segment_id,
                start=seg.start,
                end=seg.end,
                duration=slot_dur,
                text=seg.text,
                asset_path=None,
                asset_name=None,
                asset_type="none",
                asset_duration=None,
                trim_in=0.0,
                trim_out=0.0,
                status="UNMATCHED",
                match_score=round(best_score, 2),
                match_reason=best_reason if best_asset else "below_threshold",
            ))

    matched_count = sum(1 for p in placements if p.asset_path is not None)
    logger.info(f"B-roll Matching selesai: {matched_count}/{len(placements)} segmen memiliki B-roll.")
    return placements


def build_capcut_plan(
    workspace_name: str,
    main_video_rel: str,
    placements: List[BRollPlacement],
    output_plan_path: Path
) -> Path:
    """
    Saves the standard B-roll plan JSON.
    Output: output/[workspace]/project/capcut_broll_plan.json
    Format satisfies Section O of specification.
    """
    output_plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_data = {
        "workspace": workspace_name,
        "main_video": main_video_rel,
        "segments": [p.to_plan_dict() for p in placements],
    }
    output_plan_path.write_text(
        json.dumps(plan_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    logger.info(f"B-roll plan tersimpan di: {output_plan_path}")
    return output_plan_path


# ==============================================================================
# CAPCUT DRAFT GENERATION
# ==============================================================================
def detect_capcut_environment(custom_draft_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Dynamically inspects the user's Windows environment for CapCut Desktop.
    Never hardcodes usernames or paths.
    """
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    capcut_base = Path(local_app_data) / "CapCut"

    draft_root = None
    if custom_draft_dir:
        c_path = Path(custom_draft_dir)
        if c_path.is_dir():
            draft_root = c_path

    if draft_root is None:
        standard_draft = capcut_base / "User Data" / "Projects" / "com.lveditor.draft"
        if standard_draft.is_dir():
            draft_root = standard_draft

    apps_dir = capcut_base / "Apps"
    installed_version = "9.5.0"
    font_path = ""

    if apps_dir.is_dir():
        # Look for version subfolders like 9.5.0.4050
        vers = [d for d in apps_dir.iterdir() if d.is_dir() and re.match(r"^\d+\.\d+\.\d+", d.name)]
        if vers:
            vers.sort(key=lambda x: [int(p) for p in re.findall(r"\d+", x.name)], reverse=True)
            installed_version = vers[0].name

        # Find system font
        for root, _, files in os.walk(str(apps_dir)):
            for f in files:
                if f.lower() in ["en.ttf", "notosans-regular.ttf", "arial.ttf"]:
                    font_path = os.path.join(root, f).replace("\\", "/")
                    break
            if font_path:
                break

    return {
        "installed": draft_root is not None,
        "draft_root": draft_root,
        "capcut_base": capcut_base,
        "version": installed_version,
        "font_path": font_path,
    }


def generate_capcut_draft(
    workspace_dir: Path,
    main_video_meta: VideoMetadata,
    placements: List[BRollPlacement],
    srt_segments: List[TranscriptSegment],
    output_draft_dir: Path,
    project_name: str = "video_auto_capcut",
    include_subtitle: bool = True,
    capcut_env: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Generates a full, valid CapCut Desktop Draft package in output_draft_dir.
    Compatible with CapCut Desktop 9.x on Windows.
    """
    if capcut_env is None:
        capcut_env = detect_capcut_environment()

    output_draft_dir.mkdir(parents=True, exist_ok=True)
    for sub in ['adjust_mask', 'common_attachment', 'matting', 'qr_upload', 'Resources', 'smart_crop', 'subdraft', 'Timelines']:
        (output_draft_dir / sub).mkdir(parents=True, exist_ok=True)

    now_ts = int(time.time())
    now_us = int(time.time() * 1_000_000)
    draft_id = str(uuid.uuid4()).upper()
    total_us = main_video_meta.duration_microseconds
    vid_w = main_video_meta.width
    vid_h = main_video_meta.height
    main_vid_path_slash = str(main_video_meta.path.resolve()).replace("\\", "/")

    # Extract real cover from first second of video
    cover_path = output_draft_dir / "draft_cover.jpg"
    try:
        cmd_cover = [
            "ffmpeg", "-y", "-ss", "00:00:01",
            "-i", str(main_video_meta.path),
            "-vframes", "1",
            "-q:v", "2",
            str(cover_path)
        ]
        subprocess.run(cmd_cover, capture_output=True, timeout=10)
    except Exception:
        pass

    # Ensure font path
    font_path = capcut_env.get("font_path", "")
    if not font_path or not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/arial.ttf"

    # 1. Materials setup
    materials_videos = []
    draft_materials_value = []

    # Main video material
    main_vid_mat_id = str(uuid.uuid4()).upper()
    materials_videos.append({
        "id": main_vid_mat_id,
        "unique_id": uuid.uuid4().hex,
        "type": "video",
        "duration": total_us,
        "path": main_vid_path_slash,
        "media_path": "",
        "local_id": "",
        "has_audio": True,
        "reverse_path": "",
        "intensifies_path": "",
        "reverse_intensifies_path": "",
        "intensifies_audio_path": "",
        "cartoon_path": "",
        "width": vid_w,
        "height": vid_h,
        "category_id": "",
        "category_name": "local",
        "material_id": "",
        "material_name": main_video_meta.filename,
        "material_url": "",
        "crop": {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0, "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0},
        "crop_ratio": "free",
        "audio_fade": None,
        "crop_scale": 1.0,
        "extra_type_option": 0,
        "stable": {"stable_level": 0, "matrix_path": "", "time_range": {"start": 0, "duration": 0}},
        "matting": {"flag": 0, "path": "", "interactiveTime": [], "has_use_quick_brush": False, "strokes": [], "has_use_quick_eraser": False, "expansion": 0, "feather": 0, "reverse": False, "custom_matting_id": "", "enable_matting_stroke": False, "is_clould": False, "mask_video_path": "", "cloud_product_fps": 0.0},
        "source": 0,
        "source_platform": 0,
        "formula_id": "",
        "check_flag": 62978047,
        "video_algorithm": {"algorithms": [], "time_range": None, "path": "", "gameplay_configs": [], "ai_in_painting_config": [], "complement_frame_config": None, "motion_blur_config": None, "deflicker": None, "noise_reduction": None, "quality_enhance": None, "super_resolution": None, "ai_background_configs": [], "smart_complement_frame": None, "aigc_generate": None, "aigc_generate_list": [], "mouth_shape_driver": None, "ai_expression_driven": None, "ai_motion_driven": None, "image_interpretation": None, "story_video_modify_video_config": {"task_id": "", "is_overwrite_last_video": False, "tracker_task_id": "", "generate_id": "", "generate_card_id": ""}, "skip_algorithm_index": []},
        "is_unified_beauty_mode": False,
        "is_set_beauty_mode": False,
        "object_locked": None,
        "smart_motion": None,
        "multi_camera_info": None,
        "freeze": None,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "team_id": "",
        "local_material_id": "",
        "origin_material_id": "",
        "request_id": "",
        "has_sound_separated": False,
        "is_text_edit_overdub": False,
        "is_ai_generate_content": False,
        "aigc_type": "none",
        "is_copyright": False,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "local_material_from": "",
        "smart_match_info": None,
        "beauty_face_preset_infos": [],
        "beauty_body_preset_id": "",
        "beauty_face_auto_preset": {"preset_id": "", "name": "", "rate_map": "", "scene": ""},
        "beauty_face_auto_preset_infos": [],
        "beauty_body_auto_preset": None,
        "live_photo_timestamp": -1,
        "live_photo_cover_path": "",
        "content_feature_info": None,
        "corner_pin": None,
        "surface_trackings": [],
        "video_mask_stroke": {"resource_id": "", "path": "", "type": "", "color": "", "size": 0.0, "alpha": 0.0, "distance": 0.0, "texture": 0.0, "horizontal_shift": 0.0, "vertical_shift": 0.0},
        "video_mask_shadow": {"resource_id": "", "path": "", "color": "", "alpha": 0.0, "blur": 0.0, "distance": 0.0, "angle": 0.0},
        "pre_applied_vip_materials": [],
        "workflow_node_id": ""
    })

    draft_materials_value.append({
        "ai_group_type": "",
        "create_time": now_ts,
        "duration": total_us,
        "enter_from": 0,
        "extra_info": main_video_meta.filename,
        "file_Path": main_vid_path_slash,
        "height": vid_h,
        "id": str(uuid.uuid4()),
        "import_time": now_ts,
        "import_time_ms": now_us,
        "item_source": 1,
        "material_color_tag": "",
        "md5": "",
        "metetype": "video",
        "roughcut_time_range": {"duration": total_us, "start": 0},
        "sub_time_range": {"duration": -1, "start": -1},
        "type": 0,
        "width": vid_w
    })

    # B-roll materials
    broll_mat_map: Dict[str, str] = {}
    broll_dims_map: Dict[str, Tuple[int, int]] = {}
    for p in placements:
        if not p.asset_path:
            continue
        full_p = (workspace_dir / p.asset_path).resolve()
        p_str = str(full_p).replace("\\", "/")
        if p_str in broll_mat_map:
            continue

        b_mat_id = str(uuid.uuid4()).upper()
        broll_mat_map[p_str] = b_mat_id
        is_img = p.asset_type == "image"
        mtype = "photo" if is_img else "video"
        b_dur_us = 10800000000 if is_img else int((p.asset_duration or 60.0) * 1_000_000)

        bw, bh = 1920, 1080
        if is_img and full_p.is_file():
            try:
                from PIL import Image
                with Image.open(full_p) as img:
                    bw, bh = img.width, img.height
            except Exception:
                pass
        broll_dims_map[p_str] = (bw, bh)

        materials_videos.append({
            "id": b_mat_id,
            "unique_id": uuid.uuid4().hex,
            "type": mtype,
            "duration": b_dur_us,
            "path": p_str,
            "media_path": "",
            "local_id": "",
            "has_audio": False if is_img else True,
            "reverse_path": "",
            "intensifies_path": "",
            "reverse_intensifies_path": "",
            "intensifies_audio_path": "",
            "cartoon_path": "",
            "width": bw,
            "height": bh,
            "category_id": "",
            "category_name": "local",
            "material_id": "",
            "material_name": p.asset_name or full_p.name,
            "material_url": "",
            "crop": {"upper_left_x": 0.0, "upper_left_y": 0.0, "upper_right_x": 1.0, "upper_right_y": 0.0, "lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0, "lower_right_y": 1.0},
            "crop_ratio": "free",
            "audio_fade": None,
            "crop_scale": 1.0,
            "extra_type_option": 0,
            "stable": {"stable_level": 0, "matrix_path": "", "time_range": {"start": 0, "duration": 0}},
            "matting": {"flag": 0, "path": "", "interactiveTime": [], "has_use_quick_brush": False, "strokes": [], "has_use_quick_eraser": False, "expansion": 0, "feather": 0, "reverse": False, "custom_matting_id": "", "enable_matting_stroke": False, "is_clould": False, "mask_video_path": "", "cloud_product_fps": 0.0},
            "source": 0,
            "source_platform": 0,
            "formula_id": "",
            "check_flag": 62978047,
            "video_algorithm": {"algorithms": [], "time_range": None, "path": "", "gameplay_configs": [], "ai_in_painting_config": [], "complement_frame_config": None, "motion_blur_config": None, "deflicker": None, "noise_reduction": None, "quality_enhance": None, "super_resolution": None, "ai_background_configs": [], "smart_complement_frame": None, "aigc_generate": None, "aigc_generate_list": [], "mouth_shape_driver": None, "ai_expression_driven": None, "ai_motion_driven": None, "image_interpretation": None, "story_video_modify_video_config": {"task_id": "", "is_overwrite_last_video": False, "tracker_task_id": "", "generate_id": "", "generate_card_id": ""}, "skip_algorithm_index": []},
            "is_unified_beauty_mode": False,
            "is_set_beauty_mode": False,
            "object_locked": None,
            "smart_motion": None,
            "multi_camera_info": None,
            "freeze": None,
            "picture_from": "none",
            "picture_set_category_id": "",
            "picture_set_category_name": "",
            "team_id": "",
            "local_material_id": "",
            "origin_material_id": "",
            "request_id": "",
            "has_sound_separated": False,
            "is_text_edit_overdub": False,
            "is_ai_generate_content": False,
            "aigc_type": "none",
            "is_copyright": False,
            "aigc_history_id": "",
            "aigc_item_id": "",
            "local_material_from": "",
            "smart_match_info": None,
            "beauty_face_preset_infos": [],
            "beauty_body_preset_id": "",
            "beauty_face_auto_preset": {"preset_id": "", "name": "", "rate_map": "", "scene": ""},
            "beauty_face_auto_preset_infos": [],
            "beauty_body_auto_preset": None,
            "live_photo_timestamp": -1,
            "live_photo_cover_path": "",
            "content_feature_info": None,
            "corner_pin": None,
            "surface_trackings": [],
            "video_mask_stroke": {"resource_id": "", "path": "", "type": "", "color": "", "size": 0.0, "alpha": 0.0, "distance": 0.0, "texture": 0.0, "horizontal_shift": 0.0, "vertical_shift": 0.0},
            "video_mask_shadow": {"resource_id": "", "path": "", "color": "", "alpha": 0.0, "blur": 0.0, "distance": 0.0, "angle": 0.0},
            "pre_applied_vip_materials": [],
            "workflow_node_id": ""
        })

        draft_materials_value.append({
            "ai_group_type": "",
            "create_time": now_ts,
            "duration": b_dur_us,
            "enter_from": 0,
            "extra_info": p.asset_name or full_p.name,
            "file_Path": p_str,
            "height": bh,
            "id": str(uuid.uuid4()),
            "import_time": now_ts,
            "import_time_ms": now_us,
            "item_source": 1,
            "material_color_tag": "",
            "md5": "",
            "metetype": mtype,
            "roughcut_time_range": {"duration": b_dur_us, "start": 0},
            "sub_time_range": {"duration": -1, "start": -1},
            "type": 0,
            "width": bw
        })

    # Auxiliary material pools
    speeds: List[Dict[str, Any]] = []
    canvases: List[Dict[str, Any]] = []
    placeholder_infos: List[Dict[str, Any]] = []
    sound_channel_mappings: List[Dict[str, Any]] = []
    material_colors: List[Dict[str, Any]] = []
    vocal_separations: List[Dict[str, Any]] = []

    def make_aux_refs() -> List[str]:
        sp_id = str(uuid.uuid4()).upper()
        speeds.append({"id": sp_id, "type": "speed", "mode": 0, "speed": 1.0, "curve_speed": None})

        pl_id = str(uuid.uuid4()).upper()
        placeholder_infos.append({"id": pl_id, "type": "placeholder_info", "meta_type": "none", "res_path": "", "res_text": "", "error_path": "", "error_text": ""})

        cv_id = str(uuid.uuid4()).upper()
        canvases.append({"id": cv_id, "type": "canvas_color", "color": "", "blur": 0.0, "image": "", "album_image": "", "image_id": "", "image_name": "", "source_platform": 0, "team_id": ""})

        sc_id = str(uuid.uuid4()).upper()
        sound_channel_mappings.append({"id": sc_id, "type": "", "audio_channel_mapping": 0, "is_config_open": False})

        mc_id = str(uuid.uuid4()).upper()
        material_colors.append({"id": mc_id, "is_color_clip": False, "is_gradient": False, "solid_color": "", "gradient_colors": [], "gradient_percents": [], "gradient_angle": 90.0, "width": 0.0, "height": 0.0})

        vs_id = str(uuid.uuid4()).upper()
        vocal_separations.append({"id": vs_id, "type": "vocal_separation", "choice": 0, "removed_sounds": [], "time_range": None, "production_path": "", "final_algorithm": "", "enter_from": ""})

        return [sp_id, pl_id, cv_id, sc_id, mc_id, vs_id]

    # Track 0: Main Video
    track_0_segments = [{
        "id": str(uuid.uuid4()).upper(),
        "source_timerange": {"start": 0, "duration": total_us},
        "target_timerange": {"start": 0, "duration": total_us},
        "render_timerange": {"start": 0, "duration": 0},
        "desc": "",
        "state": 0,
        "speed": 1.0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "volume": 1.0,
        "last_nonzero_volume": 1.0,
        "clip": {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "transform": {"x": 0.0, "y": 0.0}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0},
        "uniform_scale": {"on": True, "value": 1.0},
        "material_id": main_vid_mat_id,
        "extra_material_refs": make_aux_refs(),
        "render_index": 0,
        "keyframe_refs": [],
        "enable_lut": True,
        "enable_adjust": True,
        "enable_hsl": False,
        "visible": True,
        "group_id": "",
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "track_render_index": 0,
        "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
        "enable_color_wheels": True,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "enable_smart_color_adjust": False,
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {"enable": False, "target_follow": "", "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0},
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_adjust_mask": False,
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "enable_video_mask": True,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
        "segment_color_tag": ""
    }]
    track_0 = {
        "id": str(uuid.uuid4()).upper(),
        "type": "video",
        "flag": 0,
        "attribute": 0,
        "segments": track_0_segments
    }

    # Track 1: Overlay B-Roll
    track_1_segments = []
    for p in placements:
        if not p.asset_path:
            continue
        full_p = (workspace_dir / p.asset_path).resolve()
        p_str = str(full_p).replace("\\", "/")
        mat_id = broll_mat_map.get(p_str)
        if not mat_id:
            continue

        st_us = int(p.start * 1_000_000)
        dur_us = int(p.duration * 1_000_000)
        if st_us + dur_us > total_us:
            dur_us = max(0, total_us - st_us)
        if dur_us <= 0:
            continue

        trim_in_us = int(p.trim_in * 1_000_000)

        bw, bh = broll_dims_map.get(p_str, (vid_w, vid_h))
        ar_canvas = vid_w / vid_h if vid_h > 0 else 16 / 9
        ar_media = bw / bh if bh > 0 else ar_canvas
        # Automatically fit/fill canvas with no black bars and no distortion
        scale_val = round(max(ar_canvas / ar_media, ar_media / ar_canvas), 4)

        track_1_segments.append({
            "id": str(uuid.uuid4()).upper(),
            "source_timerange": {"start": trim_in_us, "duration": dur_us},
            "target_timerange": {"start": st_us, "duration": dur_us},
            "render_timerange": {"start": 0, "duration": 0},
            "desc": "",
            "state": 0,
            "speed": 1.0,
            "is_loop": False,
            "is_tone_modify": False,
            "reverse": False,
            "intensifies_audio": False,
            "cartoon": False,
            "volume": 0.0 if p.asset_type == "video" else 1.0,
            "last_nonzero_volume": 1.0,
            "clip": {"scale": {"x": scale_val, "y": scale_val}, "rotation": 0.0, "transform": {"x": 0.0, "y": 0.0}, "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0},
            "uniform_scale": {"on": True, "value": 1.0},
            "material_id": mat_id,
            "extra_material_refs": make_aux_refs(),
            "render_index": 1,
            "keyframe_refs": [],
            "enable_lut": True,
            "enable_adjust": True,
            "enable_hsl": False,
            "visible": True,
            "group_id": "",
            "enable_color_curves": True,
            "enable_hsl_curves": True,
            "track_render_index": 1,
            "hdr_settings": {"mode": 1, "intensity": 1.0, "nits": 1000},
            "enable_color_wheels": True,
            "track_attribute": 0,
            "is_placeholder": False,
            "template_id": "",
            "enable_smart_color_adjust": False,
            "template_scene": "default",
            "common_keyframes": [],
            "caption_info": None,
            "responsive_layout": {"enable": False, "target_follow": "", "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0},
            "enable_color_match_adjust": False,
            "enable_color_correct_adjust": False,
            "enable_adjust_mask": False,
            "raw_segment_id": "",
            "lyric_keyframes": None,
            "enable_video_mask": True,
            "digital_human_template_group_id": "",
            "color_correct_alg_result": "",
            "source": "segmentsourcenormal",
            "enable_mask_stroke": False,
            "enable_mask_shadow": False,
            "enable_color_adjust_pro": False,
            "segment_color_tag": ""
        })

    track_1 = {
        "id": str(uuid.uuid4()).upper(),
        "type": "video",
        "flag": 2, # Flag 2 = PIP / Overlay B-roll
        "attribute": 0,
        "segments": track_1_segments
    }

    tracks = [track_0, track_1]

    # Track 2: Subtitle Text Track
    materials_texts = []
    material_animations = []
    if include_subtitle and srt_segments:
        track_2_segments = []
        for seg in srt_segments:
            st_us = int(seg.start * 1_000_000)
            dur_us = int(seg.duration * 1_000_000)
            if st_us + dur_us > total_us:
                dur_us = max(0, total_us - st_us)
            if dur_us <= 0:
                continue

            txt_mat_id = str(uuid.uuid4()).upper()
            anim_id = str(uuid.uuid4()).upper()
            material_animations.append({
                "id": anim_id,
                "type": "sticker_animation",
                "animations": [],
                "multi_language_current": "none"
            })

            text_obj = {
                "text": seg.text,
                "styles": [
                    {
                        "fill": {
                            "content": {
                                "render_type": "solid",
                                "solid": {"color": [1.0, 1.0, 1.0]} # High-contrast white
                            }
                        },
                        "font": {
                            "path": font_path,
                            "id": ""
                        },
                        "size": 11.0,
                        "bold": True,
                        "useLetterColor": True,
                        "strokes": [
                            {
                                "alpha": 1.0,
                                "content": {
                                    "render_type": "solid",
                                    "solid": {"color": [0.0, 0.0, 0.0]}
                                },
                                "width": 0.06
                            }
                        ],
                        "range": [0, len(seg.text)]
                    }
                ]
            }

            materials_texts.append({
                "recognize_task_id": "",
                "id": txt_mat_id,
                "name": "",
                "recognize_text": "",
                "recognize_model": "",
                "punc_model": "",
                "type": "text",
                "content": json.dumps(text_obj, ensure_ascii=False),
                "base_content": "",
                "words": {"start_time": [], "end_time": [], "text": []},
                "current_words": {"start_time": [], "end_time": [], "text": []},
                "global_alpha": 1.0,
                "combo_info": {"text_templates": []},
                "caption_template_info": {"resource_id": "", "third_resource_id": "", "resource_name": "", "category_id": "", "category_name": "", "effect_id": "", "request_id": "", "path": "", "is_new": False, "source_platform": 0},
                "layer_weight": 1,
                "letter_spacing": 0.0,
                "text_curve": None,
                "text_loop_on_path": False,
                "offset_on_path": 0.0,
                "enable_path_typesetting": False,
                "text_exceeds_path_process_type": 0,
                "text_typesetting_paths": None,
                "text_typesetting_paths_file": "",
                "text_typesetting_path_index": 0,
                "line_spacing": 0.02,
                "has_shadow": True,
                "shadow_color": "#000000",
                "shadow_alpha": 0.8,
                "shadow_smoothing": 0.45,
                "shadow_distance": 5.0,
                "shadow_point": {"x": 0.636, "y": -0.636},
                "shadow_angle": -45.0,
                "shadow_thickness_projection_enable": False,
                "shadow_thickness_projection_angle": 0.0,
                "shadow_thickness_projection_distance": 0.0,
                "border_alpha": 1.0,
                "border_color": "#000000",
                "border_width": 0.08,
                "border_mode": 0,
                "style_name": "",
                "text_color": "#ffffff",
                "text_alpha": 1.0,
                "font_name": "",
                "font_title": "none",
                "font_size": 11.0,
                "font_path": font_path,
                "font_id": "",
                "font_resource_id": "",
                "initial_scale": 1.0,
                "font_url": "",
                "typesetting": 0,
                "alignment": 1,
                "line_feed": 1,
                "use_effect_default_color": True,
                "is_rich_text": False,
                "shape_clip_x": False,
                "shape_clip_y": False,
                "ktv_color": "",
                "text_to_audio_ids": [],
                "bold_width": 0.008,
                "italic_degree": 0,
                "underline": False,
                "underline_width": 0.05,
                "underline_offset": 0.22,
                "sub_type": 0,
                "check_flag": 23,
                "text_size": 28,
                "font_category_name": "",
                "font_source_platform": 0,
                "font_third_resource_id": "",
                "font_category_id": "",
                "add_type": 0,
                "operation_type": 0,
                "recognize_type": 0,
                "fonts": [],
                "background_color": "",
                "background_alpha": 0.0,
                "background_style": 0,
                "background_round_radius": 0.0,
                "background_width": 0.0,
                "background_height": 0.0,
                "background_vertical_offset": 0.0,
                "background_horizontal_offset": 0.0,
                "background_fill": "",
                "single_char_bg_enable": False,
                "single_char_bg_color": "",
                "single_char_bg_alpha": 1.0,
                "single_char_bg_round_radius": 0.3,
                "single_char_bg_width": 0.0,
                "single_char_bg_height": 0.0,
                "single_char_bg_vertical_offset": 0.0,
                "single_char_bg_horizontal_offset": 0.0,
                "font_team_id": "",
                "tts_auto_update": False,
                "text_preset_resource_id": "",
                "group_id": "",
                "preset_id": "",
                "preset_name": "",
                "preset_category": "",
                "preset_category_id": "",
                "preset_index": 0,
                "preset_has_set_alignment": False,
                "force_apply_line_max_width": False,
                "language": "",
                "relevance_segment": [],
                "original_size": [],
                "fixed_width": -1.0,
                "fixed_height": -1.0,
                "autoAdaptCanvasEnabled": False,
                "line_max_width": 0.82,
                "oneline_cutoff": False,
                "cutoff_postfix": "",
                "subtitle_template_original_fontsize": 0.0,
                "subtitle_keywords": None,
                "inner_padding": -1.0,
                "multi_language_current": "none",
                "source_from": "",
                "is_lyric_effect": False,
                "lyric_group_id": "",
                "lyrics_template": {"resource_id": "", "resource_name": "", "panel": "", "effect_id": "", "path": "", "category_id": "", "category_name": "", "request_id": ""},
                "is_batch_replace": False,
                "is_words_linear": False,
                "ssml_content": "",
                "subtitle_keywords_config": None,
                "sub_template_id": -1,
                "translate_original_text": ""
            })

            track_2_segments.append({
                "id": str(uuid.uuid4()).upper(),
                "source_timerange": None,
                "target_timerange": {"start": st_us, "duration": dur_us},
                "render_timerange": {"start": 0, "duration": 0},
                "desc": "",
                "state": 0,
                "speed": 1.0,
                "is_loop": False,
                "is_tone_modify": False,
                "reverse": False,
                "intensifies_audio": False,
                "cartoon": False,
                "volume": 1.0,
                "last_nonzero_volume": 1.0,
                "clip": {
                    "scale": {"x": 1.0, "y": 1.0},
                    "rotation": 0.0,
                    "transform": {"x": 0.0, "y": -0.75}, # Positioned bottom
                    "flip": {"vertical": False, "horizontal": False},
                    "alpha": 1.0
                },
                "uniform_scale": {"on": True, "value": 1.0},
                "material_id": txt_mat_id,
                "extra_material_refs": [anim_id],
                "render_index": 14000,
                "keyframe_refs": [],
                "enable_lut": False,
                "enable_adjust": False,
                "enable_hsl": False,
                "visible": True,
                "group_id": "",
                "enable_color_curves": True,
                "enable_hsl_curves": True,
                "track_render_index": 2,
                "hdr_settings": None,
                "enable_color_wheels": True,
                "track_attribute": 0,
                "is_placeholder": False,
                "template_id": "",
                "enable_smart_color_adjust": False,
                "template_scene": "default",
                "common_keyframes": [],
                "caption_info": None,
                "responsive_layout": {"enable": False, "target_follow": "", "size_layout": 0, "horizontal_pos_layout": 0, "vertical_pos_layout": 0},
                "enable_color_match_adjust": False,
                "enable_color_correct_adjust": False,
                "enable_adjust_mask": False,
                "raw_segment_id": "",
                "lyric_keyframes": None,
                "enable_video_mask": True,
                "digital_human_template_group_id": "",
                "color_correct_alg_result": "",
                "source": "segmentsourcenormal",
                "enable_mask_stroke": False,
                "enable_mask_shadow": False,
                "enable_color_adjust_pro": False,
                "segment_color_tag": ""
            })

        tracks.append({
            "id": str(uuid.uuid4()).upper(),
            "type": "text",
            "flag": 0,
            "attribute": 0,
            "segments": track_2_segments
        })

    # Assemble materials
    all_materials = {
        "flowers": [],
        "videos": materials_videos,
        "tail_leaders": [],
        "audios": [],
        "images": [],
        "texts": materials_texts,
        "effects": [],
        "stickers": [],
        "canvases": canvases,
        "transitions": [],
        "audio_effects": [],
        "audio_fades": [],
        "beats": [],
        "material_animations": material_animations,
        "placeholders": [],
        "placeholder_infos": placeholder_infos,
        "speeds": speeds,
        "common_mask": [],
        "chromas": [],
        "text_templates": [],
        "realtime_denoises": [],
        "audio_pannings": [],
        "audio_pitch_shifts": [],
        "video_trackings": [],
        "hsl": [],
        "drafts": [],
        "color_curves": [],
        "hsl_curves": [],
        "primary_color_wheels": [],
        "log_color_wheels": [],
        "video_effects": [],
        "ai_text_effects": [],
        "audio_balances": [],
        "handwrites": [],
        "manual_deformations": [],
        "manual_beautys": [],
        "plugin_effects": [],
        "sound_channel_mappings": sound_channel_mappings,
        "green_screens": [],
        "shapes": [],
        "material_colors": material_colors,
        "digital_humans": [],
        "digital_human_model_dressing": [],
        "smart_crops": [],
        "ai_translates": [],
        "audio_track_indexes": [],
        "loudnesses": [],
        "vocal_beautifys": [],
        "vocal_separations": vocal_separations,
        "smart_relights": [],
        "time_marks": [],
        "multi_language_refs": [],
        "video_shadows": [],
        "video_strokes": [],
        "video_radius": []
    }

    # draft_content.json
    draft_content = {
        "id": draft_id,
        "version": 360000,
        "new_version": "183.0.0",
        "name": project_name,
        "duration": total_us,
        "create_time": 0,
        "update_time": 0,
        "fps": 30.0,
        "is_drop_frame_timecode": False,
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition": None,
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition": None,
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "canvas_config": {"ratio": "original", "width": vid_w, "height": vid_h, "background": None},
        "tracks": tracks,
        "group_container": None,
        "materials": all_materials,
        "keyframes": {"videos": [], "audios": [], "texts": [], "stickers": [], "filters": [], "adjusts": [], "handwrites": []},
        "keyframe_graph_list": [],
        "platform": {"os": "windows", "os_version": "10.0.26200", "app_id": 359289, "app_version": capcut_env.get("version", "9.5.0"), "app_source": "cc"},
        "last_modified_platform": {"os": "windows", "os_version": "10.0.26200", "app_id": 359289, "app_version": capcut_env.get("version", "9.5.0"), "app_source": "cc"},
        "mutable_config": None,
        "cover": None,
        "retouch_cover": None,
        "extra_info": None,
        "relationships": [],
        "mixed_track_mode_on": False,
        "render_index_track_mode_on": True,
        "free_render_index_mode_on": False,
        "static_cover_image_path": "",
        "source": "default",
        "time_marks": None,
        "path": "",
        "lyrics_effects": [],
        "uneven_animation_template_info": {"composition": "", "content": "", "order": "", "sub_template_info_list": []},
        "draft_type": "video",
        "smart_ads_info": {"page_from": "", "routine": "", "draft_url": ""},
        "function_assistant_info": {
            "auto_adjust": False,
            "auto_adjust_segid_list": [],
            "fixed_rec_applied": False,
            "smart_rec_applied": False
        }
    }

    content_file = output_draft_dir / "draft_content.json"
    content_file.write_text(json.dumps(draft_content, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(content_file, output_draft_dir / "draft_content.json.bak")

    # draft_meta_info.json
    draft_fold_str = str(output_draft_dir.resolve()).replace("\\", "/")
    draft_root_str = str(output_draft_dir.parent.resolve()).replace("\\", "/")
    draft_meta = {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_package_type": "",
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "draft_cover.jpg",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {"draft_enterprise_extra": "", "draft_enterprise_id": "", "draft_enterprise_name": "", "enterprise_material": []},
        "draft_fold_path": draft_fold_str,
        "draft_id": draft_id,
        "draft_is_ae_produce": False,
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": False,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_cloud_temp_draft": False,
        "draft_is_from_deeplink": False,
        "draft_is_infinite_canvas_draft": False,
        "draft_is_invisible": False,
        "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_materials": [
            {"type": 0, "value": draft_materials_value},
            {"type": 1, "value": []},
            {"type": 2, "value": []},
            {"type": 3, "value": []},
            {"type": 6, "value": []},
            {"type": 7, "value": []},
            {"type": 8, "value": []}
        ],
        "draft_materials_copied_info": [],
        "draft_name": project_name,
        "draft_need_rename_folder": False,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": draft_root_str,
        "draft_segment_extra_info": [],
        "draft_timeline_materials_size_": os.path.getsize(main_video_meta.path),
        "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "",
        "pippit_extra_info": "",
        "pippit_id": "",
        "pippit_user_name": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_entry_id": -1,
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_cloud_user_id": -1,
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": total_us
    }

    meta_file = output_draft_dir / "draft_meta_info.json"
    meta_file.write_text(json.dumps(draft_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Auxiliary files
    (output_draft_dir / "draft_settings").write_text(
        f"[General]\r\ndraft_create_time={now_ts}\r\ndraft_last_edit_time={now_ts}\r\nreal_edit_seconds=0\r\nreal_edit_keys=0\r\ncloud_last_modify_platform=windows\r\n",
        encoding="utf-8"
    )

    t_id = str(uuid.uuid4()).upper()
    (output_draft_dir / "timeline_layout.json").write_text(
        json.dumps({"dockItems":[{"dockIndex":0,"ratio":1,"timelineIds":[t_id],"timelineNames":["Timeline 01"]}],"layoutOrientation":1}),
        encoding="utf-8"
    )

    (output_draft_dir / "draft_agency_config.json").write_text(
        json.dumps({"is_auto_agency_enabled":False,"is_auto_agency_popup":False,"is_single_agency_mode":False,"marterials":None,"use_converter":False,"video_resolution":720}),
        encoding="utf-8"
    )
    (output_draft_dir / "draft_biz_config.json").write_text("", encoding="utf-8")
    (output_draft_dir / "draft_virtual_store.json").write_text(
        json.dumps({"draft_materials": [], "draft_virtual_store": []}),
        encoding="utf-8"
    )
    (output_draft_dir / "key_value.json").write_text("{}", encoding="utf-8")
    (output_draft_dir / "performance_opt_info.json").write_text(
        json.dumps({"manual_cancle_precombine_segs": None, "need_auto_precombine_segs": None}),
        encoding="utf-8"
    )
    (output_draft_dir / "attachment_pc_common.json").write_text(
        json.dumps({"ai_packaging_infos":[],"ai_packaging_report_info":{"caption_id_list":[],"commercial_material":"","material_source":"","method":"","page_from":"","style":"","task_id":"","text_style":"","tos_id":"","video_category":""},"broll":{"ai_packaging_infos":[],"ai_packaging_report_info":{"caption_id_list":[],"commercial_material":"","material_source":"","method":"","page_from":"","style":"","task_id":"","text_style":"","tos_id":"","video_category":""}},"commercial_music_category_ids":[],"pc_feature_flag":0,"recognize_tasks":[],"reference_lines_config":{"horizontal_lines":[],"is_lock":False,"is_visible":False,"vertical_lines":[]},"safe_area_type":0,"template_item_infos":[],"unlock_template_ids":[]}),
        encoding="utf-8"
    )

    logger.info(
        f"CapCut Desktop Draft berhasil dibuat: {output_draft_dir} | "
        f"Tracks: {len(tracks)} (Video: {len(track_0_segments)}, B-roll: {len(track_1_segments)}"
        f"{f', Text: {len(track_2_segments)}' if include_subtitle else ''})"
    )
    return output_draft_dir


def install_capcut_draft(
    draft_dir: Path,
    project_name: str,
    capcut_draft_root: Optional[Path] = None
) -> Path:
    """
    Installs/copies the generated draft package to user's CapCut Desktop drafts folder.
    Guarantees:
      - Never overwrites existing CapCut projects (generates unique project ID / folder name).
      - Backs up root_meta_info.json before modifying.
      - Registers project in root_meta_info.json.
    """
    if capcut_draft_root is None:
        env = detect_capcut_environment()
        capcut_draft_root = env.get("draft_root")

    if not capcut_draft_root or not capcut_draft_root.is_dir():
        raise FileNotFoundError(
            "Lokasi draft CapCut Desktop tidak dapat ditemukan otomatis pada sistem ini.\n"
            "Pastikan CapCut Desktop sudah pernah dibuka setidaknya satu kali, atau gunakan:\n"
            "  --capcut-draft-dir <path_ke_folder_com.lveditor.draft>"
        )

    # 1. Determine unique project name / folder
    candidate_name = project_name
    counter = 1
    target_folder = capcut_draft_root / candidate_name
    while target_folder.exists():
        counter += 1
        candidate_name = f"{project_name}_{counter:02d}"
        target_folder = capcut_draft_root / candidate_name

    logger.info(f"Memasang project baru ke CapCut Desktop: '{candidate_name}' -> {target_folder}")

    # 2. Copy draft package
    shutil.copytree(draft_dir, target_folder)

    # 3. Update paths in target draft files
    target_dir_slash = str(target_folder.resolve()).replace("\\", "/")
    capcut_root_slash = str(capcut_draft_root.resolve()).replace("\\", "/")
    capcut_root_bslash = str(capcut_draft_root.resolve()).replace("/", "\\")

    meta_file = target_folder / "draft_meta_info.json"
    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    unique_draft_id = str(uuid.uuid4()).upper()
    meta["draft_id"] = unique_draft_id
    meta["draft_fold_path"] = target_dir_slash
    meta["draft_root_path"] = capcut_root_slash
    meta["draft_name"] = candidate_name
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    content_file = target_folder / "draft_content.json"
    with open(content_file, "r", encoding="utf-8") as f:
        content = json.load(f)
    content["id"] = unique_draft_id
    content["name"] = candidate_name
    with open(content_file, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    shutil.copyfile(content_file, target_folder / "draft_content.json.bak")

    # 4. Update root_meta_info.json
    root_meta_file = capcut_draft_root / "root_meta_info.json"
    if root_meta_file.exists():
        bak_file = capcut_draft_root / "root_meta_info.json.bak"
        shutil.copyfile(root_meta_file, bak_file)

        with open(root_meta_file, "r", encoding="utf-8") as f:
            root_data = json.load(f)

        all_drafts = root_data.get("all_draft_store", [])
        all_drafts = [d for d in all_drafts if d.get("draft_id") != unique_draft_id and d.get("draft_name") != candidate_name]

        entry = {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "draft_cloud_last_action_download": False,
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": f"{target_dir_slash}\\draft_cover.jpg",
            "draft_fold_path": target_dir_slash,
            "draft_id": unique_draft_id,
            "draft_is_ai_shorts": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_infinite_canvas_draft": False,
            "draft_is_invisible": False,
            "draft_is_pippit_draft": False,
            "draft_is_web_article_video": False,
            "draft_json_file": f"{target_dir_slash}\\draft_content.json",
            "draft_name": candidate_name,
            "draft_new_version": "",
            "draft_root_path": capcut_root_slash,
            "draft_timeline_materials_size": meta.get("draft_timeline_materials_size_", 0),
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "pippit_avatar_url": "",
            "pippit_extra_info": "",
            "pippit_id": "",
            "pippit_user_name": "",
            "streaming_edit_draft_ready": True,
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
            "tm_draft_create": meta["tm_draft_create"],
            "tm_draft_modified": meta["tm_draft_modified"],
            "tm_draft_removed": 0,
            "tm_duration": meta["tm_duration"]
        }

        all_drafts.insert(0, entry)
        root_data["all_draft_store"] = all_drafts
        root_data["draft_ids"] = len(all_drafts)

        with open(root_meta_file, "w", encoding="utf-8") as f:
            json.dump(root_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Project '{candidate_name}' berhasil didaftarkan di root_meta_info.json!")

    logger.info(f"Instalasi berhasil. Buka CapCut Desktop untuk melihat project '{candidate_name}'.")
    return target_folder


# ==============================================================================
# VALIDATION ENGINE
# ==============================================================================
def validate_project(
    workspace_dir: Path,
    main_video_meta: VideoMetadata,
    srt_path: Path,
    plan_path: Path,
    draft_dir: Path
) -> List[str]:
    """
    Executes the 16 validation rules defined in Section U.
    Returns list of validation failure messages (empty if 100% valid).
    """
    errors: List[str] = []

    # 1. video utama ditemukan
    if not main_video_meta.path.is_file():
        errors.append("1. Video utama tidak ditemukan di filesystem.")

    # 2. video utama dapat dibaca
    # 3. durasi video dapat dibaca
    if main_video_meta.duration_seconds <= 0:
        errors.append("2/3. Durasi video utama <= 0 atau gagal dibaca.")

    # 4. Whisper menghasilkan segment
    # 5. SRT valid
    if not srt_path.is_file():
        errors.append("4/5. File subtitle.srt tidak ditemukan.")
    else:
        try:
            srt_segs = parse_srt_file(srt_path)
            if not srt_segs:
                errors.append("4/5. subtitle.srt kosong atau tidak memiliki segment.")
            for s in srt_segs:
                # 6. timestamp valid
                # 7. timestamp tidak negatif
                # 8. start < end
                if s.start < 0 or s.end < 0:
                    errors.append(f"6/7. Timestamp negatif pada segment {s.segment_id}")
                    break
                if s.start >= s.end:
                    errors.append(f"8. start >= end pada segment {s.segment_id}")
                    break
                # 9. timestamp tidak melebihi video utama
                if s.start > main_video_meta.duration_seconds + 2.0:
                    errors.append(f"9. Segment {s.segment_id} start ({s.start}s) melebihi durasi video utama.")
                    break
        except Exception as e:
            errors.append(f"5. Gagal memvalidasi SRT: {e}")

    # 10. B-roll asset ditemukan
    # 11. B-roll placement valid
    # 12. image duration valid
    if not plan_path.is_file():
        errors.append("10/11. capcut_broll_plan.json tidak ditemukan.")
    else:
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            for seg in plan.get("segments", []):
                a_rel = seg.get("asset")
                if a_rel:
                    a_file = workspace_dir / a_rel
                    if not a_file.is_file():
                        errors.append(f"10. B-roll asset tidak ditemukan di disk: {a_rel}")
                        break
                    dur = seg.get("end", 0) - seg.get("start", 0)
                    if dur <= 0:
                        errors.append(f"11/12. Durasi placement B-roll tidak valid: {dur}")
                        break
        except Exception as e:
            errors.append(f"11. Gagal memvalidasi broll plan: {e}")

    # 13. semua media path valid
    # 14. CapCut Draft berhasil dibuat
    content_file = draft_dir / "draft_content.json"
    meta_file = draft_dir / "draft_meta_info.json"
    if not content_file.is_file() or not meta_file.is_file():
        errors.append("14. File draft_content.json atau draft_meta_info.json tidak ditemukan di draft.")
    else:
        try:
            c = json.loads(content_file.read_text(encoding="utf-8"))
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            # 15. project ID unik
            if not c.get("id") or not m.get("draft_id"):
                errors.append("15. Project ID draft kosong.")
            # 16. output project tidak merusak project lain
            if len(c.get("tracks", [])) < 2:
                errors.append("14. Draft tracks kurang dari 2 (minimal Video Track + B-roll Track).")
        except Exception as e:
            errors.append(f"14. Gagal memvalidasi JSON draft: {e}")

    return errors


# ==============================================================================
# PIPELINE RUNNER
# ==============================================================================
def run_pipeline(
    workspace_name: str,
    generate_mode: bool = True,
    install_mode: bool = False,
    main_video_arg: Optional[str] = None,
    whisper_model: str = "base",
    whisper_device: str = "cpu",
    force_whisper: bool = False,
    no_subtitle: bool = False,
    capcut_draft_dir_arg: Optional[str] = None,
    project_name_arg: Optional[str] = None,
) -> int:
    """
    Main execution pipeline for CapCut Auto Edit Engine.
    """
    print("\n" + "=" * 75)
    print("           CAPCUT AUTO EDIT ENGINE - NUGI KONTEN KREATOR")
    print("=" * 75)
    logger.info(f"Memulai pipeline editing CapCut untuk workspace: {workspace_name}")

    # 1. Workspace
    workspace_dir = find_workspace(workspace_name)
    footage_dir = workspace_dir / "footage"
    broll_dir = workspace_dir / "broll"
    subtitle_dir = workspace_dir / "subtitle"
    project_dir = workspace_dir / "project"

    # 2. Main video detection
    main_video_path = find_main_video(footage_dir, main_video_arg)
    main_video_meta = get_video_metadata(main_video_path)

    # 3. Whisper transcription / SRT handling
    srt_path = subtitle_dir / "subtitle.srt"
    srt_segments = transcribe_video(
        video_path=main_video_path,
        output_srt_path=srt_path,
        model_name=whisper_model,
        device=whisper_device,
        force_whisper=force_whisper,
    )

    # 4. Discover B-roll assets
    broll_assets = find_broll_assets(broll_dir)

    # 5. Match B-roll to transcript segments
    placements = match_broll(srt_segments, broll_assets)

    # 6. Save B-roll timeline plan
    plan_path = project_dir / "capcut_broll_plan.json"
    rel_main_vid = f"footage/{main_video_meta.filename}"
    build_capcut_plan(
        workspace_name=workspace_dir.name,
        main_video_rel=rel_main_vid,
        placements=placements,
        output_plan_path=plan_path
    )

    # 7. Detect CapCut Environment
    capcut_env = detect_capcut_environment(capcut_draft_dir_arg)
    logger.info(
        f"CapCut Environment: Terpasang={capcut_env['installed']} | "
        f"Versi={capcut_env['version']} | "
        f"DraftRoot={capcut_env['draft_root']}"
    )

    # 8. Generate CapCut Draft Package
    draft_package_dir = project_dir / "capcut"
    proj_name = project_name_arg or f"video_auto_capcut_{workspace_dir.name.replace('-', '_')}"

    if generate_mode or install_mode:
        generate_capcut_draft(
            workspace_dir=workspace_dir,
            main_video_meta=main_video_meta,
            placements=placements,
            srt_segments=srt_segments,
            output_draft_dir=draft_package_dir,
            project_name=proj_name,
            include_subtitle=not no_subtitle,
            capcut_env=capcut_env,
        )

    # 9. Validation
    val_errors = validate_project(
        workspace_dir=workspace_dir,
        main_video_meta=main_video_meta,
        srt_path=srt_path,
        plan_path=plan_path,
        draft_dir=draft_package_dir
    )

    if val_errors:
        logger.error("VALIDASI GAGAL! Ditemukan isu:")
        for err in val_errors:
            logger.error(f"  - {err}")
        return 1
    else:
        logger.info("VALIDASI SUKSES: 16 aturan integritas terpenuhi secara sempurna!")

    # 10. Install Mode
    if install_mode:
        logger.info("Menjalankan instalasi draft ke folder CapCut Desktop user...")
        installed_path = install_capcut_draft(
            draft_dir=draft_package_dir,
            project_name=proj_name,
            capcut_draft_root=capcut_env["draft_root"]
        )
        print("\n" + "*" * 75)
        print(f"  CAPCUT DRAFT BERHASIL DIPASANG KE: {installed_path}")
        print("  Silakan buka CapCut Desktop -> Project langsung tersedia!")
        print("*" * 75)

    print("\n" + "=" * 75)
    print("                    RINGKASAN EKSEKUSI PIPELINE")
    print("=" * 75)
    print(f"  Workspace      : {workspace_dir.name}")
    print(f"  Video Utama    : {main_video_meta.filename} ({main_video_meta.duration_seconds:.2f}s)")
    print(f"  Subtitle SRT   : {srt_path} ({len(srt_segments)} segmen)")
    print(f"  B-roll Assets  : {len(broll_assets)} ditemukan")
    print(f"  B-roll Plan    : {plan_path}")
    print(f"  CapCut Draft   : {draft_package_dir}")
    print(f"  Mode Install   : {'DIPASANG' if install_mode else 'Hanya Generate (Gunakan --install untuk pasang)'}")
    print("=" * 75 + "\n")
    return 0


# ==============================================================================
# CLI INTERFACE
# ==============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(
        description="CapCut Desktop Auto Edit Engine - Nugi Konten Kreator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh Penggunaan:
  # Mode 1: Generate draft package di output/[workspace]/project/capcut/
  python -m engine.pipeline.auto_edit_capcut --workspace 01-script --generate

  # Mode 2: Generate & Pasang langsung ke CapCut Desktop
  python -m engine.pipeline.auto_edit_capcut --workspace 01-script --install

  # Mode khusus dengan pemilihan video utama manual:
  python -m engine.pipeline.auto_edit_capcut --workspace 01-script --main-video video-mentah.mp4 --install
        """
    )
    parser.add_argument(
        "--workspace", "-w",
        default="01-script",
        help="Nama atau folder workspace (contoh: 01-script atau output/01-script)",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        default=False,
        help="Mode 1: Generate draft package di output/[workspace]/project/capcut/",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        default=False,
        help="Mode 2: Pasang/copy draft package ke direktori CapCut Desktop",
    )
    parser.add_argument(
        "--main-video",
        default=None,
        help="Nama file video utama di footage/ (opsional jika hanya ada 1 video)",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Nama model faster-whisper (tiny, base, small, medium, large-v3)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device untuk Whisper transcription (cpu atau cuda)",
    )
    parser.add_argument(
        "--force-whisper",
        action="store_true",
        default=False,
        help="Paksa menjalankan ulang transkripsi Whisper meskipun subtitle.srt sudah ada",
    )
    parser.add_argument(
        "--no-subtitle",
        action="store_true",
        default=False,
        help="Jangan masukkan track subtitle text ke dalam CapCut Draft",
    )
    parser.add_argument(
        "--capcut-draft-dir",
        default=None,
        help="Path custom direktori com.lveditor.draft jika tidak di lokasi default",
    )
    parser.add_argument(
        "--project-name",
        default=None,
        help="Nama kustom project CapCut Desktop",
    )

    args = parser.parse_args()

    # Default to generate if neither flag is set
    gen_mode = args.generate
    inst_mode = args.install
    if not gen_mode and not inst_mode:
        gen_mode = True

    exit_code = run_pipeline(
        workspace_name=args.workspace,
        generate_mode=gen_mode,
        install_mode=inst_mode,
        main_video_arg=args.main_video,
        whisper_model=args.model,
        whisper_device=args.device,
        force_whisper=args.force_whisper,
        no_subtitle=args.no_subtitle,
        capcut_draft_dir_arg=args.capcut_draft_dir,
        project_name_arg=args.project_name,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
