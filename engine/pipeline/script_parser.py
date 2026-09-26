"""
engine/pipeline/script_parser.py
================================
Parses structured video script files (such as 5_Narasi_Konten_TikTok_Shorts_Nugi.md)
into strongly-typed NarasiScript and ScriptSection objects.

Extracts:
  - Narrative index, ID (e.g., 'narasi-01'), title, and DNA pillar
  - Sections: Hook, Tension/Paradox, Context/Data, Revelation, Open Question
  - Exact timecodes (seconds and formatted string)
  - Spoken text per section
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def parse_timecode_to_seconds(tc: str) -> float:
    """
    Parse a timecode string into total seconds.
    Supports formats:
      - '00:05' -> 5.0
      - '00:62' -> 62.0 (seconds >= 60 in MM:SS)
      - '01:15' -> 75.0
      - '00:01:15' -> 75.0
      - '75' -> 75.0
    """
    tc = tc.strip()
    parts = tc.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    elif len(parts) == 1:
        return float(parts[0])
    raise ValueError(f"Invalid timecode format: '{tc}'")


def format_seconds_to_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    secs = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def normalize_section_type(raw_name: str) -> str:
    """Normalize raw section name into a clean category key."""
    name_upper = raw_name.upper()
    if "HOOK" in name_upper:
        return "hook"
    elif "TENSION" in name_upper or "PARADOX" in name_upper:
        return "tension"
    elif "CONTEXT" in name_upper or "DATA" in name_upper:
        return "context"
    elif "REVELATION" in name_upper or "WHY" in name_upper:
        return "revelation"
    elif "QUESTION" in name_upper or "PENUTUP" in name_upper:
        return "open_question"
    return "general"


@dataclass
class ScriptSection:
    """A distinct scene/section in the narrative."""
    index: int
    name: str
    section_type: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    text: str
    timecode_raw: str

    @property
    def srt_start(self) -> str:
        return format_seconds_to_srt_time(self.start_seconds)

    @property
    def srt_end(self) -> str:
        return format_seconds_to_srt_time(self.end_seconds)


@dataclass
class NarasiScript:
    """A complete structured narrative ready for production."""
    index: int
    id: str  # e.g., "narasi-01"
    title: str
    pillar: str
    dna: str
    total_duration_seconds: float
    sections: List[ScriptSection] = field(default_factory=list)

    @property
    def project_name(self) -> str:
        return f"Nugi_Narasi_{self.index:02d}"


class ScriptParser:
    """Parses markdown narrative scripts into NarasiScript objects."""

    def parse_file(self, filepath: Path | str) -> List[NarasiScript]:
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Script file not found: {filepath}")
        content = p.read_text(encoding="utf-8")
        return self.parse_text(content)

    def parse_text(self, content: str) -> List[NarasiScript]:
        # Normalize newlines
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Extract global DNA if present
        dna_match = re.search(r"\*\*Content DNA:\*\*\s*`?([^`\n]+)`?", content)
        global_dna = dna_match.group(1).strip() if dna_match else "AI × PROPERTY × HUMAN × WHY"

        # Split content into Narasi blocks using ## 📽️ NARASI X or ## NARASI X
        pattern = r"##\s+(?:📽️\s*)?NARASI\s+(\d+)(?::\s*([^\n]+))?"
        splits = list(re.finditer(pattern, content, re.IGNORECASE))

        if not splits:
            # Fallback: maybe just code block or single narrative
            return self._parse_single_block(content, global_dna)

        narratives: List[NarasiScript] = []

        for i, match in enumerate(splits):
            narasi_idx = int(match.group(1))
            pillar = match.group(2).strip() if match.group(2) else ""

            start_pos = match.end()
            end_pos = splits[i + 1].start() if i + 1 < len(splits) else len(content)
            block_text = content[start_pos:end_pos]

            # Title
            title_match = re.search(r"###\s+\*?([^\*\n]+)\*?", block_text)
            title = title_match.group(1).strip() if title_match else f"Narasi {narasi_idx}"

            # Pillar DNA within block if available
            pilar_dna_match = re.search(r"-\s+\*\*Pilar DNA:\*\*\s*`?([^`\n]+)`?", block_text)
            block_dna = pilar_dna_match.group(1).strip() if pilar_dna_match else (pillar or global_dna)

            # Extract script text inside ```text ... ``` or just text
            sections = self._extract_sections_from_block(block_text)

            total_dur = sections[-1].end_seconds if sections else 0.0

            narasi_id = f"narasi-{narasi_idx:02d}"
            narratives.append(
                NarasiScript(
                    index=narasi_idx,
                    id=narasi_id,
                    title=title,
                    pillar=pillar or block_dna,
                    dna=block_dna,
                    total_duration_seconds=total_dur,
                    sections=sections,
                )
            )

        return narratives

    def _extract_sections_from_block(self, block_text: str) -> List[ScriptSection]:
        # Search for code block ```text ... ``` or ``` ... ```
        code_match = re.search(r"```(?:text)?\n(.*?)\n```", block_text, re.DOTALL)
        source_text = code_match.group(1) if code_match else block_text

        # Regex for [MM:SS - MM:SS] SECTION_NAME
        tc_pattern = (
            r"\[(\d+(?::\d+)?)\s*[-–—]\s*(\d+(?::\d+)?)\]\s*([^\n]+)\n"
            r"(.*?)(?=(?:\n\[\d+(?::\d+)?\s*[-–—]|\Z))"
        )

        matches = list(re.finditer(tc_pattern, source_text, re.DOTALL))
        sections: List[ScriptSection] = []

        for idx, m in enumerate(matches, 1):
            start_tc, end_tc, sec_name, raw_body = m.groups()
            start_sec = parse_timecode_to_seconds(start_tc)
            end_sec = parse_timecode_to_seconds(end_tc)
            duration = max(0.0, end_sec - start_sec)
            clean_text = " ".join(raw_body.strip().split())

            clean_name = sec_name.strip()
            sec_type = normalize_section_type(clean_name)

            sections.append(
                ScriptSection(
                    index=idx,
                    name=clean_name,
                    section_type=sec_type,
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    duration_seconds=duration,
                    text=clean_text,
                    timecode_raw=f"[{start_tc} - {end_tc}] {clean_name}",
                )
            )

        return sections

    def _parse_single_block(self, content: str, global_dna: str) -> List[NarasiScript]:
        sections = self._extract_sections_from_block(content)
        total_dur = sections[-1].end_seconds if sections else 0.0
        return [
            NarasiScript(
                index=1,
                id="narasi-01",
                title="Narasi 1",
                pillar="GENERAL",
                dna=global_dna,
                total_duration_seconds=total_dur,
                sections=sections,
            )
        ]
