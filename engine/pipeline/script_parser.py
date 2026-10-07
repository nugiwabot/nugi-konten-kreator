"""
engine/pipeline/script_parser.py
================================
Parses structured video script files into strongly-typed NarasiScript and ScriptSection objects.

Supports multiple production script standards in the repository:
1. Shorts Scripts (Shorts 01-20):
   - Header: '## SHORT XX — Title'
   - Teleprompter: '### 🪝 HOOK', '### 🔓 OPEN LOOP', '### 💡 ISI', '### 🔄 PERUBAHAN',
                   '### 🎁 PAYOFF', '### 📣 CTA'
2. Long-Form Scripts (Scripts 01-13):
   - Header: '# NASKAH KONTEN NUGI — LONG FORM #XX'
   - Chapters / Teleprompter: '### [COLD OPEN]', '### [BAB X: ...]', '### [PENUTUP / REFLEKSI]'
3. Legacy Scripts:
   - Header: '## 📽️ NARASI X' or '## NARASI X'
   - Explicit timecodes: '[MM:SS - MM:SS] SECTION_NAME'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


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


def format_seconds_to_timecode(seconds: float) -> str:
    """Format seconds into MM:SS string."""
    total_sec = int(round(seconds))
    minutes = total_sec // 60
    secs = total_sec % 60
    return f"{minutes:02d}:{secs:02d}"


def normalize_section_type(raw_name: str) -> str:
    """Normalize raw section name into a clean category key."""
    name_upper = raw_name.upper()
    if "HOOK" in name_upper or "COLD OPEN" in name_upper:
        return "hook"
    elif "OPEN LOOP" in name_upper:
        return "open_loop"
    elif "TENSION" in name_upper or "PARADOX" in name_upper:
        return "tension"
    elif "ISI" in name_upper or "REVELATION" in name_upper or "REVELASI" in name_upper or "WHY" in name_upper:
        return "revelation"
    elif "PAYOFF" in name_upper:
        return "payoff"
    elif "PERUBAHAN" in name_upper or "CONTEXT" in name_upper or "DATA" in name_upper or "BAB" in name_upper:
        return "context"
    elif "CTA" in name_upper or "CALL TO ACTION" in name_upper or "QUESTION" in name_upper or "PENUTUP" in name_upper or "REFLEKSI" in name_upper or "KESIMPULAN" in name_upper:
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
    id: str  # e.g., "narasi-01" or "short-06"
    title: str
    pillar: str
    dna: str
    total_duration_seconds: float
    sections: List[ScriptSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def project_name(self) -> str:
        return f"Nugi_Narasi_{self.index:02d}"


class ScriptParser:
    """Parses markdown narrative scripts into NarasiScript objects."""

    WORDS_PER_SECOND = 2.2  # Approximate Indonesian narration rate (~132 wpm)

    def parse_file(self, filepath: Path | str) -> List[NarasiScript]:
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Script file not found: {filepath}")
        content = p.read_text(encoding="utf-8")
        return self.parse_text(content)

    def parse_text(self, content: str) -> List[NarasiScript]:
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # 1. Try Shorts Script pattern (## SHORT XX ...)
        shorts = self._try_parse_shorts(content)
        if shorts:
            return shorts

        # 2. Try Long-form Script pattern (# NASKAH KONTEN NUGI — LONG FORM #XX)
        longform = self._try_parse_longform(content)
        if longform:
            return longform

        # 3. Try Legacy Narasi Script pattern (## 📽️ NARASI X or ## NARASI X)
        legacy = self._try_parse_legacy(content)
        if legacy:
            return legacy

        # 4. Fallback: single narrative
        dna_match = re.search(r"\*\*Content DNA:\*\*\s*`?([^`\n]+)`?", content)
        global_dna = dna_match.group(1).strip() if dna_match else "AI × PROPERTY × HUMAN × WHY"
        return self._parse_single_block(content, global_dna)

    # --------------------------------------------------------------------------
    # 1. Shorts Parser (SHORT 01 - SHORT 20)
    # --------------------------------------------------------------------------
    def _try_parse_shorts(self, content: str) -> Optional[List[NarasiScript]]:
        short_match = re.search(r"##\s+SHORT\s+(\d+)\s*(?:[—–\-:]\s*([^\n]+))?", content, re.IGNORECASE)
        if not short_match:
            return None

        short_idx = int(short_match.group(1))
        title = short_match.group(2).strip() if short_match.group(2) else f"Short {short_idx}"

        # Extract metadata
        story_type_match = re.search(r"\*\*Story Type:\*\*\s*([^\n|]+)", content)
        story_type = story_type_match.group(1).strip() if story_type_match else "PLACE"

        device_match = re.search(r"\*\*Narrative Device:\*\*\s*([^\n|]+)", content)
        narrative_device = device_match.group(1).strip() if device_match else ""

        anchor_match = re.search(r"\*\*Human[–\-]Place Anchor:\*\*\s*([^\n]+)", content)
        human_anchor = anchor_match.group(1).strip() if anchor_match else ""

        headline_match = re.search(r"\*\*Headline:\*\*\s*\n?\s*\*\*?([^\*\n]+)\*\*?", content)
        if headline_match:
            title = headline_match.group(1).strip()

        # Extract Teleprompter sections
        # Look for section header: ## 🎙️ NASKAH TELEPROMPTER or just ### 🪝 HOOK
        teleprompter_start = content.find("NASKAH TELEPROMPTER")
        body_text = content[teleprompter_start:] if teleprompter_start != -1 else content

        section_pattern = r"(###\s*(?:[🪝🔓💡🔄🎁📣🎯🎙️])?\s*([^\n]+))\n(.*?)(?=(?:\n###|\Z))"
        matches = list(re.finditer(section_pattern, body_text, re.DOTALL))

        sections: List[ScriptSection] = []
        cumulative_time = 0.0

        for idx, m in enumerate(matches, 1):
            raw_header, sec_name, raw_body = m.groups()
            clean_name = re.sub(r"^[🪝🔓💡🔄🎁📣🎯🎙️\s]+", "", sec_name).strip()
            # Clean body lines (skip markdown subheadings or metadata)
            lines = [ln.strip() for ln in raw_body.splitlines() if ln.strip() and not ln.strip().startswith("---")]
            clean_text = " ".join(lines)
            if not clean_text:
                continue

            sec_type = normalize_section_type(clean_name)
            words = clean_text.split()
            # Calculate duration: min 3.0s, speaking rate 2.2 words/sec
            duration = max(3.0, round(len(words) / self.WORDS_PER_SECOND, 1))
            start_sec = round(cumulative_time, 1)
            end_sec = round(cumulative_time + duration, 1)
            cumulative_time = end_sec

            tc_raw = f"[{format_seconds_to_timecode(start_sec)} - {format_seconds_to_timecode(end_sec)}] {clean_name}"

            sections.append(
                ScriptSection(
                    index=len(sections) + 1,
                    name=clean_name,
                    section_type=sec_type,
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    duration_seconds=duration,
                    text=clean_text,
                    timecode_raw=tc_raw,
                )
            )

        if not sections:
            return None

        total_dur = sections[-1].end_seconds if sections else 0.0
        script_id = f"short-{short_idx:02d}"

        return [
            NarasiScript(
                index=short_idx,
                id=script_id,
                title=title,
                pillar="HUMAN x PLACE",
                dna=f"{story_type} | {narrative_device}".strip(" |"),
                total_duration_seconds=total_dur,
                sections=sections,
                metadata={
                    "format": "Shorts",
                    "story_type": story_type,
                    "narrative_device": narrative_device,
                    "human_place_anchor": human_anchor,
                },
            )
        ]

    # --------------------------------------------------------------------------
    # 2. Long-form Parser (SCRIPT 01 - SCRIPT 13)
    # --------------------------------------------------------------------------
    def _try_parse_longform(self, content: str) -> Optional[List[NarasiScript]]:
        long_match = re.search(r"#\s+NASKAH KONTEN NUGI\s*[—–\-]\s*LONG\s*FORM\s*#(\d+)", content, re.IGNORECASE)
        if not long_match:
            return None

        script_idx = int(long_match.group(1))

        # Title: ## *"..."* or ## Title
        title_match = re.search(r"##\s+\*?\"?([^\*\n\"]+)\"?\*?", content)
        title = title_match.group(1).strip() if title_match else f"Long Form {script_idx}"

        # Extract Teleprompter sections
        tele_start = content.find("NASKAH TELEPROMPTER")
        body_text = content[tele_start:] if tele_start != -1 else content

        # Look for ### [COLD OPEN] or ### [BAB X: ...] or ### Section
        section_pattern = r"(###\s*\[?([^\n\]]+)\]?)\n(.*?)(?=(?:\n###|\Z))"
        matches = list(re.finditer(section_pattern, body_text, re.DOTALL))

        sections: List[ScriptSection] = []
        cumulative_time = 0.0

        for idx, m in enumerate(matches, 1):
            raw_header, sec_name, raw_body = m.groups()
            clean_name = sec_name.strip()
            # Clean body: strip italic cues like *(Durasi target: ...)*
            clean_lines = []
            for ln in raw_body.splitlines():
                ln_s = ln.strip()
                if not ln_s or ln_s.startswith("---") or (ln_s.startswith("*(") and ln_s.endswith(")*")):
                    continue
                clean_lines.append(ln_s)
            clean_text = " ".join(clean_lines)
            if not clean_text:
                continue

            sec_type = normalize_section_type(clean_name)
            words = clean_text.split()
            duration = max(5.0, round(len(words) / self.WORDS_PER_SECOND, 1))
            start_sec = round(cumulative_time, 1)
            end_sec = round(cumulative_time + duration, 1)
            cumulative_time = end_sec

            tc_raw = f"[{format_seconds_to_timecode(start_sec)} - {format_seconds_to_timecode(end_sec)}] {clean_name}"

            sections.append(
                ScriptSection(
                    index=len(sections) + 1,
                    name=clean_name,
                    section_type=sec_type,
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    duration_seconds=duration,
                    text=clean_text,
                    timecode_raw=tc_raw,
                )
            )

        if not sections:
            return None

        total_dur = sections[-1].end_seconds if sections else 0.0
        script_id = f"longform-{script_idx:02d}"

        return [
            NarasiScript(
                index=script_idx,
                id=script_id,
                title=title,
                pillar="DOCUMENTARY ESSAY",
                dna="ORIGIN x SYSTEM x WHY",
                total_duration_seconds=total_dur,
                sections=sections,
                metadata={"format": "Long-Form"},
            )
        ]

    # --------------------------------------------------------------------------
    # 3. Legacy Narasi Script Parser
    # --------------------------------------------------------------------------
    def _try_parse_legacy(self, content: str) -> Optional[List[NarasiScript]]:
        dna_match = re.search(r"\*\*Content DNA:\*\*\s*`?([^`\n]+)`?", content)
        global_dna = dna_match.group(1).strip() if dna_match else "AI × PROPERTY × HUMAN × WHY"

        pattern = r"##\s+(?:📽️\s*)?NARASI\s+(\d+)(?::\s*([^\n]+))?"
        splits = list(re.finditer(pattern, content, re.IGNORECASE))
        if not splits:
            return None

        narratives: List[NarasiScript] = []
        for i, match in enumerate(splits):
            narasi_idx = int(match.group(1))
            pillar = match.group(2).strip() if match.group(2) else ""

            start_pos = match.end()
            end_pos = splits[i + 1].start() if i + 1 < len(splits) else len(content)
            block_text = content[start_pos:end_pos]

            title_match = re.search(r"###\s+\*?([^\*\n]+)\*?", block_text)
            title = title_match.group(1).strip() if title_match else f"Narasi {narasi_idx}"

            pilar_dna_match = re.search(r"-\s+\*\*Pilar DNA:\*\*\s*`?([^`\n]+)`?", block_text)
            block_dna = pilar_dna_match.group(1).strip() if pilar_dna_match else (pillar or global_dna)

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
        code_match = re.search(r"```(?:text)?\n(.*?)\n```", block_text, re.DOTALL)
        source_text = code_match.group(1) if code_match else block_text

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
