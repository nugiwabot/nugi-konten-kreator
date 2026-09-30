#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
                         NUGI SUBTITLE GENERATOR
              Tool Subtitle Lokal & Offline untuk VN Video Editor
================================================================================
Target File  : C:\\Users\\Nugi\\Videos\\VN\\nugi-subtitle.py
Output Folder: C:\\Users\\Nugi\\Videos\\VN\\
Fitur Utama  :
  1. 100% Offline & Lokal (Tidak ada upload cloud/API eksternal)
  2. Menggunakan Whisper lokal yang sudah terpasang (faster-whisper)
  3. Tanpa download model otomatis (local_files_only=True)
  4. Format SRT standar & valid untuk VN Video Editor (HH:MM:SS,mmm)
  5. Segmentasi subtitle optimal: Max 2 baris, Max 42 char/baris, Max 5 detik
  6. Mendukung GUI (Tkinter) dan CLI (Command Line)
================================================================================
"""

import os
import sys
import time
import re
import math
import shutil
import textwrap
import threading
import subprocess
import glob
from pathlib import Path

# Tkinter GUI Imports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ==============================================================================
# KONFIGURASI DEFAULT
# ==============================================================================
DEFAULT_OUTPUT_DIR = r"C:\Users\Nugi\Videos\VN"
SUPPORTED_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")

# Batasan Subtitle VN Video Editor
MAX_LINES_PER_SUBTITLE = 2
MAX_CHARS_PER_LINE = 42
MAX_SUBTITLE_DURATION = 5.0  # detik
MIN_SUBTITLE_DURATION = 0.5  # detik


# ==============================================================================
# FUNGSI INSPEKSI & DETEKSI ENGINE & MODEL LOKAL
# ==============================================================================
def detect_system_environment():
    """
    Inspeksi menyeluruh environment komputer:
    - FFmpeg
    - CUDA / GPU support
    - Faster-whisper / Whisper package
    - Model Whisper lokal yang sudah ada di cache / disk
    """
    info = {
        "ffmpeg": False,
        "ffmpeg_path": None,
        "engine": None,
        "cuda_available": False,
        "device": "cpu",
        "models": [],
        "error": None
    }

    # 1. Cek FFmpeg
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        info["ffmpeg"] = True
        info["ffmpeg_path"] = ffmpeg_bin
    else:
        winget_ffmpeg = glob.glob(r"C:\Users\*\AppData\Local\Microsoft\WinGet\Packages\*ffmpeg*\**\bin\ffmpeg.exe", recursive=True)
        if winget_ffmpeg:
            info["ffmpeg"] = True
            info["ffmpeg_path"] = winget_ffmpeg[0]
            os.environ["PATH"] = os.path.dirname(winget_ffmpeg[0]) + os.pathsep + os.environ.get("PATH", "")

    # 2. Cek Engine & Hardware
    try:
        import faster_whisper
        import ctranslate2
        info["engine"] = "faster-whisper"
        
        try:
            cuda_count = ctranslate2.get_cuda_device_count()
            if cuda_count > 0:
                info["cuda_available"] = True
                info["device"] = "cuda"
            else:
                info["cuda_available"] = False
                info["device"] = "cpu"
        except Exception:
            info["cuda_available"] = False
            info["device"] = "cpu"

    except ImportError:
        try:
            import whisper
            info["engine"] = "openai-whisper"
            try:
                import torch
                if torch.cuda.is_available():
                    info["cuda_available"] = True
                    info["device"] = "cuda"
            except Exception:
                pass
        except ImportError:
            info["engine"] = None

    # 3. Cari model lokal yang sudah terunduh
    info["models"] = find_local_whisper_models()

    return info


def find_local_whisper_models():
    """
    Mencari model Whisper yang sudah tersimpan secara lokal di komputer,
    tanpa melakukan request internet atau mengunduh model baru.
    """
    discovered = []
    seen_paths = set()

    # Lokasi 1: Cache Hugging Face Hub (untuk faster-whisper)
    hf_hub = os.path.expanduser(r"~/.cache/huggingface/hub")
    if os.path.isdir(hf_hub):
        for entry in os.listdir(hf_hub):
            if "faster-whisper" in entry or "whisper" in entry:
                entry_dir = os.path.join(hf_hub, entry)
                snapshots_dir = os.path.join(entry_dir, "snapshots")
                if os.path.isdir(snapshots_dir):
                    for snap in os.listdir(snapshots_dir):
                        snap_path = os.path.join(snapshots_dir, snap)
                        bin_file = os.path.join(snap_path, "model.bin")
                        if os.path.isfile(bin_file) and snap_path not in seen_paths:
                            seen_paths.add(snap_path)
                            size_mb = os.path.getsize(bin_file) / (1024 * 1024)
                            clean_name = entry.replace("models--Systran--faster-whisper-", "").replace("models--", "")
                            discovered.append({
                                "id": clean_name,
                                "name": f"{clean_name} (Lokal, {size_mb:.0f} MB)",
                                "path": snap_path,
                                "engine": "faster-whisper"
                            })

    # Lokasi 2: Cache Torch / OpenAI Whisper
    whisper_cache = os.path.expanduser(r"~/.cache/whisper")
    if os.path.isdir(whisper_cache):
        for f in os.listdir(whisper_cache):
            if f.endswith(".pt"):
                pt_path = os.path.join(whisper_cache, f)
                if pt_path not in seen_paths:
                    seen_paths.add(pt_path)
                    size_mb = os.path.getsize(pt_path) / (1024 * 1024)
                    m_name = f.replace(".pt", "")
                    discovered.append({
                        "id": m_name,
                        "name": f"{m_name} (Torch .pt, {size_mb:.0f} MB)",
                        "path": pt_path,
                        "engine": "openai-whisper"
                    })

    # Lokasi 3: Folder C:\Users\Nugi\Videos\VN\models jika ada
    vn_models = os.path.join(DEFAULT_OUTPUT_DIR, "models")
    if os.path.isdir(vn_models):
        for d in os.listdir(vn_models):
            m_path = os.path.join(vn_models, d)
            bin_file = os.path.join(m_path, "model.bin")
            if os.path.isfile(bin_file) and m_path not in seen_paths:
                seen_paths.add(m_path)
                size_mb = os.path.getsize(bin_file) / (1024 * 1024)
                discovered.append({
                    "id": d,
                    "name": f"{d} (Folder VN, {size_mb:.0f} MB)",
                    "path": m_path,
                    "engine": "faster-whisper"
                })

    return discovered


# ==============================================================================
# PEMFORMATAN SRT & SEGMENTASI SUBTITLE
# ==============================================================================
def format_srt_timestamp(seconds: float) -> str:
    """
    Format detik ke format waktu standar SRT: HH:MM:SS,mmm
    Contoh: 00:01:23,456 (menggunakan koma, bukan titik).
    """
    if seconds < 0.0:
        seconds = 0.0
    
    total_seconds = int(seconds)
    millis = int(round((seconds - total_seconds) * 1000))
    if millis >= 1000:
        total_seconds += 1
        millis -= 1000
        
    hrs = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def wrap_text_for_subtitle(text: str, max_chars: int = MAX_CHARS_PER_LINE, max_lines: int = MAX_LINES_PER_SUBTITLE) -> str:
    """
    Membungkus teks menjadi maksimal 2 baris dengan batas max_chars per baris,
    memecah pada spasi atau tanda baca secara alami tanpa memotong kata.
    """
    text = " ".join(text.strip().split())
    if not text:
        return ""
    if len(text) <= max_chars:
        return text

    wrapped = textwrap.wrap(text, width=max_chars)
    if len(wrapped) <= max_lines:
        return "\n".join(wrapped)

    # Jika lebih dari 2 baris, potong menjadi 2 baris pada titik tengah terbaik
    words = text.split(" ")
    mid_char = len(text) // 2
    best_idx = 0
    cur_len = 0
    min_dist = float("inf")
    
    for i, w in enumerate(words[:-1]):
        cur_len += len(w) + (1 if i > 0 else 0)
        dist = abs(cur_len - mid_char)
        if dist < min_dist:
            min_dist = dist
            best_idx = i

    line1 = " ".join(words[:best_idx + 1])
    line2 = " ".join(words[best_idx + 1:])
    return f"{line1}\n{line2}"


def split_segment_into_srt_chunks(start: float, end: float, text: str, words=None,
                                  max_chars_line: int = MAX_CHARS_PER_LINE,
                                  max_lines: int = MAX_LINES_PER_SUBTITLE,
                                  max_dur: float = MAX_SUBTITLE_DURATION,
                                  min_dur: float = MIN_SUBTITLE_DURATION):
    """
    Mengubah segmen Whisper menjadi potongan subtitle yang nyaman dibaca di VN:
    - Tidak memecah secara agresif jika Whisper memberikan durasi & panjang yang sudah pas.
    - Max 2 baris.
    - Max 42 karakter per baris.
    - Max 5.0 detik per subtitle.
    - Min 0.5 detik per subtitle.
    """
    text = " ".join(text.strip().split())
    if not text:
        return []

    duration = max(end - start, min_dur)
    max_block_chars = max_chars_line * max_lines

    # Kasus A: Segmen asli sudah ringkas dan durasi <= max_dur
    if duration <= max_dur and len(text) <= max_block_chars:
        formatted_text = wrap_text_for_subtitle(text, max_chars_line, max_lines)
        return [{"start": start, "end": max(start + min_dur, end), "text": formatted_text}]

    # Kasus B: Gunakan word timestamps jika tersedia
    if words and len(words) > 1 and all(hasattr(w, "start") and hasattr(w, "end") for w in words):
        chunks = []
        cur_words = []
        cur_text = ""
        c_start = words[0].start

        for w in words:
            w_str = w.word.strip()
            if not w_str:
                continue
            cand_text = (cur_text + " " + w_str).strip()
            cand_dur = w.end - c_start

            # Batas: durasi > max_dur atau panjang karakter melebihi 2 baris atau jeda tanda baca
            if cur_words and (cand_dur > max_dur or len(cand_text) > max_block_chars or (cand_dur >= min_dur and cur_text and cur_text[-1] in ".?!")):
                f_text = wrap_text_for_subtitle(cur_text, max_chars_line, max_lines)
                c_end = max(c_start + min_dur, cur_words[-1].end)
                chunks.append({"start": c_start, "end": c_end, "text": f_text})
                cur_words = [w]
                cur_text = w_str
                c_start = max(c_end, w.start)
            else:
                cur_words.append(w)
                cur_text = cand_text

        if cur_words:
            f_text = wrap_text_for_subtitle(cur_text, max_chars_line, max_lines)
            c_end = max(c_start + min_dur, cur_words[-1].end)
            chunks.append({"start": c_start, "end": c_end, "text": f_text})
        return chunks

    # Kasus C: Fallback tanpa word timestamps - bagi teks dan waktu secara proporsional terkendali
    words_list = text.split(" ")
    num_chunks = max(math.ceil(duration / max_dur), math.ceil(len(text) / max_block_chars))
    num_chunks = max(1, min(num_chunks, len(words_list)))
    words_per_chunk = math.ceil(len(words_list) / num_chunks)

    chunks = []
    chunk_dur = duration / num_chunks
    for i in range(num_chunks):
        c_words = words_list[i * words_per_chunk : (i + 1) * words_per_chunk]
        if not c_words:
            continue
        c_text = " ".join(c_words)
        c_start = start + (i * chunk_dur)
        c_end = start + ((i + 1) * chunk_dur)
        if i == num_chunks - 1:
            c_end = max(c_end, end)
        f_text = wrap_text_for_subtitle(c_text, max_chars_line, max_lines)
        chunks.append({"start": c_start, "end": c_end, "text": f_text})

    return chunks


def build_srt_content(raw_segments) -> str:
    """
    Mengonversi raw segments Whisper menjadi isi file SRT lengkap yang valid.
    """
    all_chunks = []
    for seg in raw_segments:
        start = getattr(seg, "start", 0.0)
        end = getattr(seg, "end", start + 1.0)
        text = getattr(seg, "text", "")
        words = getattr(seg, "words", None)
        
        chunks = split_segment_into_srt_chunks(start, end, text, words)
        all_chunks.extend(chunks)

    # Susun teks SRT
    srt_lines = []
    entry_index = 1
    prev_end = 0.0

    for chunk in all_chunks:
        c_start = chunk["start"]
        c_end = chunk["end"]
        text = chunk["text"].strip()
        if not text:
            continue

        # Hindari start < prev_end yang bertabrakan
        if c_start < prev_end:
            c_start = prev_end
        if c_end <= c_start:
            c_end = c_start + MIN_SUBTITLE_DURATION

        start_str = format_srt_timestamp(c_start)
        end_str = format_srt_timestamp(c_end)

        srt_lines.append(str(entry_index))
        srt_lines.append(f"{start_str} --> {end_str}")
        srt_lines.append(text)
        srt_lines.append("")  # Baris kosong pemisah standar SRT

        prev_end = c_end
        entry_index += 1

    return "\n".join(srt_lines)


# ==============================================================================
# VALIDASI FILE SRT
# ==============================================================================
def validate_srt_file(srt_path: str) -> tuple[bool, str]:
    """
    Validasi otomatis file SRT yang dihasilkan:
    1. File benar-benar ada dan tidak kosong.
    2. Encoding valid UTF-8.
    3. Numbering sequential (1, 2, 3...).
    4. Format timestamp valid: HH:MM:SS,mmm --> HH:MM:SS,mmm.
    5. start < end.
    6. Tidak ada timestamp negatif.
    7. Teks subtitle dapat dibaca dan tidak kosong.
    8. Tidak ada overlap yang tidak wajar.
    """
    if not os.path.isfile(srt_path):
        return False, "File SRT tidak ditemukan di disk."

    size = os.path.getsize(srt_path)
    if size == 0:
        return False, "File SRT kosong (0 bytes)."

    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return False, "File SRT gagal didecode sebagai UTF-8."
    except Exception as e:
        return False, f"Gagal membaca file SRT: {e}"

    blocks = content.strip().split("\n\n")
    if not blocks or blocks == [""]:
        return False, "Tidak ada blok subtitle di dalam file SRT."

    timestamp_pattern = re.compile(
        r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
    )

    prev_start_ms = -1
    for i, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 3:
            return False, f"Blok {i} memiliki format tidak lengkap (minimal index, waktu, teks)."

        try:
            block_idx = int(lines[0])
            if block_idx != i:
                return False, f"Urutan nomor tidak sesuai: diharapkan {i}, tertulis {block_idx}."
        except ValueError:
            return False, f"Nomor urut blok {i} bukan integer yang valid: '{lines[0]}'."

        time_match = timestamp_pattern.match(lines[1])
        if not time_match:
            return False, f"Format timestamp pada blok {i} tidak valid: '{lines[1]}'."

        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, time_match.groups())
        start_ms = ((h1 * 3600) + (m1 * 60) + s1) * 1000 + ms1
        end_ms = ((h2 * 3600) + (m2 * 60) + s2) * 1000 + ms2

        if start_ms < 0:
            return False, f"Timestamp negatif ditemukan pada blok {i}."
        if end_ms <= start_ms:
            return False, f"Waktu berakhir lebih kecil atau sama dengan waktu mulai pada blok {i}."
        if start_ms < prev_start_ms:
            return False, f"Timestamp mulai mundur tidak wajar pada blok {i}."

        prev_start_ms = start_ms

        text = "\n".join(lines[2:]).strip()
        if not text:
            return False, f"Teks subtitle kosong pada blok {i}."

    return True, f"Valid: {len(blocks)} subtitle blocks terverifikasi secara standar."


# ==============================================================================
# PIPELINE TRANSKRIPSI UTAMA
# ==============================================================================
def transcribe_video_process(video_path: str, model_info: dict, language: str = "id",
                             device: str = "cpu", progress_cb=None) -> tuple[bool, str, str]:
    """
    Eksekusi transkripsi video secara 100% offline & lokal:
    - Return: (success: bool, srt_path_or_err: str, validation_msg: str)
    """
    video_p = Path(video_path)
    if not video_p.is_file():
        return False, "Video tidak dapat dibaca atau file tidak ditemukan.", ""

    # Pastikan output folder ada
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    srt_output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{video_p.stem}.srt")

    lang_code = None if language == "auto" else language

    try:
        if progress_cb:
            progress_cb("Membaca video...", 5)

        # 1. Panggil faster-whisper dengan model lokal
        import faster_whisper
        
        model_target = model_info.get("path") or model_info.get("id", "base")
        compute_type = "int8" if device == "cpu" else "float16"

        if progress_cb:
            progress_cb("Memuat model Whisper lokal...", 15)

        # Load model secara ketat OFFLINE tanpa download otomatis
        model = faster_whisper.WhisperModel(
            model_target,
            device=device,
            compute_type=compute_type,
            local_files_only=True
        )

        if progress_cb:
            progress_cb("Mengekstrak audio & memulai transkripsi...", 25)

        # Transcribe
        segments_gen, transcription_info = model.transcribe(
            str(video_p),
            language=lang_code,
            task="transcribe",
            beam_size=5,
            word_timestamps=True
        )

        total_audio_dur = getattr(transcription_info, "duration", 0.0) or 1.0

        raw_segments = []
        for seg in segments_gen:
            raw_segments.append(seg)
            if progress_cb:
                # Progres dinamis antara 25% s.d. 85% berdasarkan timestamp audio yang sedang diproses
                audio_pct = min(1.0, max(0.0, seg.end / total_audio_dur))
                cur_prog = int(25 + (audio_pct * 60))
                time_info = f"[{format_srt_timestamp(seg.end)} / {format_srt_timestamp(total_audio_dur)}]"
                snippet = seg.text.strip().replace("\n", " ")[:38]
                progress_cb(f"Transcribing {time_info}: {snippet}...", cur_prog)

        if progress_cb:
            progress_cb("Membuat SRT standar VN...", 90)

        # 2. Susun SRT
        srt_content = build_srt_content(raw_segments)
        if not srt_content.strip():
            return False, "Transkripsi menghasilkan teks kosong (tidak ada suara/dialog terdeteksi).", ""

        # 3. Tulis file SRT dengan UTF-8
        with open(srt_output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        if progress_cb:
            progress_cb("Memvalidasi file SRT...", 96)

        # 4. Validasi SRT
        is_valid, val_msg = validate_srt_file(srt_output_path)
        if not is_valid:
            return False, f"File SRT dibuat namun validasi gagal: {val_msg}", ""

        if progress_cb:
            progress_cb("Selesai.", 100)

        return True, srt_output_path, val_msg

    except Exception as e:
        print(f"[ERROR] Exception saat transkripsi: {e}", file=sys.stderr)
        return False, f"Transkripsi gagal: {str(e)}", ""


# ==============================================================================
# GUI TKINTER
# ==============================================================================
class NugiSubtitleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NUGI SUBTITLE - Local Whisper for VN")
        self.root.geometry("640x580")
        self.root.minsize(580, 520)
        self.root.configure(bg="#F8F9FA")

        self.selected_video_path = None
        self.env_info = detect_system_environment()
        self.is_processing = False

        self._setup_style()
        self._build_ui()
        self._evaluate_environment_state()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#F8F9FA")
        style.configure("Card.TFrame", background="#FFFFFF", relief="flat")
        style.configure("TLabel", background="#F8F9FA", font=("Segoe UI", 10), foreground="#212529")
        style.configure("Card.TLabel", background="#FFFFFF", font=("Segoe UI", 10), foreground="#212529")
        style.configure("Header.TLabel", background="#F8F9FA", font=("Segoe UI", 16, "bold"), foreground="#1A1D20")
        style.configure("SubHeader.TLabel", background="#F8F9FA", font=("Segoe UI", 9), foreground="#6C757D")
        
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), background="#0D6EFD", foreground="#FFFFFF")
        style.map("Primary.TButton",
                  background=[("active", "#0B5ED7"), ("disabled", "#ADB5BD")],
                  foreground=[("disabled", "#E9ECEF")])

        style.configure("Outline.TButton", font=("Segoe UI", 10), background="#E9ECEF", foreground="#212529")
        style.map("Outline.TButton", background=[("active", "#DEE2E6")])

        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background="#198754", foreground="#FFFFFF")
        style.map("Success.TButton", background=[("active", "#157347")])

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="24")
        main_frame.pack(fill=tk.BOTH, expand=True)

        lbl_title = ttk.Label(main_frame, text="NUGI SUBTITLE", style="Header.TLabel")
        lbl_title.pack(anchor="w")

        lbl_desc = ttk.Label(main_frame, text="Local Offline Whisper Transcription for VN Video Editor", style="SubHeader.TLabel")
        lbl_desc.pack(anchor="w", pady=(2, 16))

        # CARD 1: Pemilihan Video
        card_video = ttk.Frame(main_frame, style="Card.TFrame", padding="14")
        card_video.pack(fill=tk.X, pady=(0, 14))

        lbl_v_sec = ttk.Label(card_video, text="Video:", font=("Segoe UI", 10, "bold"), style="Card.TLabel")
        lbl_v_sec.pack(anchor="w", pady=(0, 6))

        btn_pick_row = ttk.Frame(card_video, style="Card.TFrame")
        btn_pick_row.pack(fill=tk.X)

        self.btn_pick = ttk.Button(btn_pick_row, text="Pilih Video", style="Outline.TButton", command=self._on_pick_video)
        self.btn_pick.pack(side=tk.LEFT)

        self.lbl_selected_file = ttk.Label(btn_pick_row, text="Tidak ada video dipilih", style="Card.TLabel", foreground="#6C757D")
        self.lbl_selected_file.pack(side=tk.LEFT, padx=(12, 0))

        # CARD 2: Konfigurasi (Bahasa, Model, Device)
        card_cfg = ttk.Frame(main_frame, style="Card.TFrame", padding="14")
        card_cfg.pack(fill=tk.X, pady=(0, 16))

        grid_frame = ttk.Frame(card_cfg, style="Card.TFrame")
        grid_frame.pack(fill=tk.X)

        # 1. Bahasa
        ttk.Label(grid_frame, text="Bahasa:", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.combo_lang = ttk.Combobox(grid_frame, values=["Indonesia (id)", "English (en)", "Auto Detect"], state="readonly", width=24)
        self.combo_lang.current(0)
        self.combo_lang.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=4)

        # 2. Model
        ttk.Label(grid_frame, text="Model:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        self.combo_model = ttk.Combobox(grid_frame, state="readonly", width=36)
        self.combo_model.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=4)

        # 3. Device
        ttk.Label(grid_frame, text="Device:", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        self.combo_device = ttk.Combobox(grid_frame, state="readonly", width=24)
        self.combo_device.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=4)

        # TOMBOL UTAMA GENERATE SUBTITLE
        self.btn_generate = ttk.Button(
            main_frame,
            text="GENERATE SUBTITLE",
            style="Primary.TButton",
            command=self._on_generate_clicked
        )
        self.btn_generate.pack(fill=tk.X, ipady=8, pady=(0, 16))

        # CARD 3: STATUS & PROGRESS
        card_status = ttk.Frame(main_frame, style="Card.TFrame", padding="14")
        card_status.pack(fill=tk.BOTH, expand=True)

        lbl_stat_title = ttk.Label(card_status, text="Status:", font=("Segoe UI", 10, "bold"), style="Card.TLabel")
        lbl_stat_title.pack(anchor="w")

        self.lbl_status = ttk.Label(card_status, text="Menunggu video...", style="Card.TLabel", foreground="#495057")
        self.lbl_status.pack(anchor="w", pady=(4, 8))

        self.prog_bar = ttk.Progressbar(card_status, mode="determinate", maximum=100)
        self.prog_bar.pack(fill=tk.X, pady=(0, 10))

        # AREA HASIL
        self.frame_result = ttk.Frame(card_status, style="Card.TFrame")
        self.frame_result.pack(fill=tk.X, pady=(4, 0))

        self.lbl_result_path = ttk.Label(self.frame_result, text="", style="Card.TLabel", font=("Segoe UI", 9, "italic"), foreground="#198754")
        self.lbl_result_path.pack(anchor="w")

        self.btn_open_folder = ttk.Button(self.frame_result, text="Buka Folder", style="Success.TButton", command=self._on_open_folder)
        self.btn_open_folder.pack_forget()

    def _evaluate_environment_state(self):
        """Mengisi pilihan model dan device berdasarkan hasil inspeksi lokal."""
        if self.env_info["cuda_available"]:
            self.combo_device["values"] = ["Automatic (CUDA)", "CUDA", "CPU"]
            self.combo_device.current(0)
        else:
            self.combo_device["values"] = ["Automatic (CPU)", "CPU"]
            self.combo_device.current(0)

        if not self.env_info["engine"]:
            self.lbl_status.config(
                text="Whisper lokal tidak ditemukan.\nSilakan pasang Whisper terlebih dahulu.",
                foreground="#DC3545"
            )
            self.btn_generate.config(state="disabled")
            return

        if not self.env_info["ffmpeg"]:
            self.lbl_status.config(
                text="Peringatan: FFmpeg tidak terdeteksi. Transkripsi mungkin gagal mengekstrak audio.",
                foreground="#DC3545"
            )

        models = self.env_info["models"]
        if not models:
            self.lbl_status.config(
                text="Model Whisper lokal tidak ditemukan di cache.\nSilakan sediakan model lokal terlebih dahulu.",
                foreground="#DC3545"
            )
            self.combo_model["values"] = ["Tidak ada model lokal"]
            self.combo_model.current(0)
            self.btn_generate.config(state="disabled")
        else:
            model_names = [m["name"] for m in models]
            self.combo_model["values"] = model_names
            self.combo_model.current(0)
            self.lbl_status.config(text="Siap. Silakan pilih video untuk diproses.")

    def _on_pick_video(self):
        filetypes = [
            ("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),
            ("MP4 Files", "*.mp4"),
            ("All Files", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Pilih File Video", filetypes=filetypes)
        if chosen:
            self.selected_video_path = chosen
            fname = os.path.basename(chosen)
            self.lbl_selected_file.config(text=fname, foreground="#212529")
            self.lbl_status.config(text=f"Video siap: {fname}")
            self.btn_open_folder.pack_forget()
            self.lbl_result_path.config(text="")
            self.prog_bar["value"] = 0

    def _on_open_folder(self):
        """Membuka Windows Explorer dan menyeleksi file SRT yang dihasilkan."""
        if hasattr(self, "latest_srt_path") and os.path.isfile(self.latest_srt_path):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.latest_srt_path)}"')
                return
            except Exception:
                pass
        try:
            os.startfile(DEFAULT_OUTPUT_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuka folder: {e}")

    def _on_generate_clicked(self):
        if not self.selected_video_path:
            messagebox.showwarning("Pilih Video", "Silakan pilih file video terlebih dahulu.")
            return

        if not os.path.isfile(self.selected_video_path):
            messagebox.showerror("File Error", "File video yang dipilih tidak ditemukan.")
            return

        models = self.env_info["models"]
        if not models:
            messagebox.showerror("Model Tidak Ada", "Whisper lokal tidak ditemukan.\nSilakan pasang Whisper terlebih dahulu.")
            return

        selected_idx = self.combo_model.current()
        if selected_idx < 0 or selected_idx >= len(models):
            selected_idx = 0
        model_obj = models[selected_idx]

        stem = Path(self.selected_video_path).stem
        target_srt = os.path.join(DEFAULT_OUTPUT_DIR, f"{stem}.srt")
        if os.path.exists(target_srt):
            answer = messagebox.askyesno(
                "File SRT Sudah Ada",
                f"File SRT sudah ada di:\n{target_srt}\n\nOverwrite file ini?"
            )
            if not answer:
                self.lbl_status.config(text="Dibatalkan oleh user (tidak overwrite).")
                return

        lang_choice = self.combo_lang.get()
        if "Indonesia" in lang_choice:
            lang_code = "id"
        elif "English" in lang_choice:
            lang_code = "en"
        else:
            lang_code = "auto"

        dev_choice = self.combo_device.get()
        if "CUDA" in dev_choice:
            device = "cuda"
        else:
            device = "cpu"

        self.is_processing = True
        self.btn_generate.config(state="disabled")
        self.btn_pick.config(state="disabled")
        self.btn_open_folder.pack_forget()
        self.lbl_result_path.config(text="")
        self.prog_bar["value"] = 5

        thread = threading.Thread(
            target=self._run_transcription_worker,
            args=(self.selected_video_path, model_obj, lang_code, device),
            daemon=True
        )
        thread.start()

    def _run_transcription_worker(self, video_path: str, model_obj: dict, lang_code: str, device: str):
        def update_progress(msg: str, percent: int):
            self.root.after(0, lambda: self._update_ui_progress(msg, percent))

        success, result_or_err, val_msg = transcribe_video_process(
            video_path=video_path,
            model_info=model_obj,
            language=lang_code,
            device=device,
            progress_cb=update_progress
        )

        self.root.after(0, lambda: self._on_transcription_finished(success, result_or_err, val_msg))

    def _update_ui_progress(self, msg: str, percent: int):
        self.lbl_status.config(text=msg, foreground="#212529")
        self.prog_bar["value"] = percent

    def _on_transcription_finished(self, success: bool, result_or_err: str, val_msg: str):
        self.is_processing = False
        self.btn_generate.config(state="normal")
        self.btn_pick.config(state="normal")

        if success:
            self.latest_srt_path = result_or_err
            self.lbl_status.config(text="Subtitle berhasil dibuat dan divalidasi.", foreground="#198754")
            self.lbl_result_path.config(text=f"Output: {result_or_err}\n({val_msg})")
            self.btn_open_folder.pack(anchor="w", pady=(8, 0))
            self.prog_bar["value"] = 100
        else:
            self.lbl_status.config(text=result_or_err, foreground="#DC3545")
            self.prog_bar["value"] = 0
            messagebox.showerror("Transkripsi Gagal", result_or_err)


# ==============================================================================
# MODE COMMAND LINE (CLI)
# ==============================================================================
def run_cli_mode(video_file: str, language: str = "id", model_choice: str = None):
    """Menjalankan proses langsung dari terminal tanpa menampilkan window GUI."""
    print("=" * 60)
    print("           NUGI SUBTITLE - LOCAL WHISPER (CLI)")
    print("=" * 60)

    video_p = Path(video_file)
    if not video_p.is_file():
        print(f"[ERROR] Video tidak dapat dibaca: '{video_file}'", file=sys.stderr)
        sys.exit(1)

    env = detect_system_environment()
    if not env["engine"]:
        print("\nWhisper lokal tidak ditemukan.\nSilakan pasang Whisper terlebih dahulu.", file=sys.stderr)
        sys.exit(1)

    models = env["models"]
    if not models:
        print("\nModel Whisper lokal tidak ditemukan di cache.", file=sys.stderr)
        sys.exit(1)

    selected_model = models[0]
    if model_choice:
        for m in models:
            if model_choice.lower() in m["name"].lower() or model_choice.lower() in m["id"].lower():
                selected_model = m
                break

    device = env["device"]

    print(f"Input Video : {video_p.resolve()}")
    print(f"Engine      : {env['engine']}")
    print(f"Model       : {selected_model['name']}")
    print(f"Device      : {device.upper()}")
    print(f"Bahasa      : {language}")
    print(f"Output Dir  : {DEFAULT_OUTPUT_DIR}")
    print("-" * 60)

    def cli_progress(msg: str, percent: int):
        print(f"[{percent:3d}%] {msg}", flush=True)

    success, result, val_msg = transcribe_video_process(
        video_path=str(video_p),
        model_info=selected_model,
        language=language,
        device=device,
        progress_cb=cli_progress
    )

    print("-" * 60)
    if success:
        print("Subtitle berhasil dibuat dan divalidasi.")
        print(f"Output File: {result}")
        print(f"Validasi   : {val_msg}")
        sys.exit(0)
    else:
        print(f"[ERROR] {result}", file=sys.stderr)
        sys.exit(1)


# ==============================================================================
# ENTRY POINT UTAMA
# ==============================================================================
def main():
    if len(sys.argv) > 1:
        first_arg = sys.argv[1].strip()
        if not first_arg.startswith("-") and not first_arg.startswith("/"):
            video_input = first_arg
            lang = "id"
            if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
                lang = sys.argv[2]
            run_cli_mode(video_input, language=lang)
            return

    root = tk.Tk()
    app = NugiSubtitleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
