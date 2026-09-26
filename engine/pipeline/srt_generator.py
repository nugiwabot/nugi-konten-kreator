"""
engine/pipeline/srt_generator.py
================================
Generates standard SubRip (.srt) subtitle files from parsed NarasiScript objects
or timeline events.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from engine.pipeline.script_parser import NarasiScript, ScriptSection, format_seconds_to_srt_time


class SRTGenerator:
    """Generates standard .srt files with precise millisecond timestamps."""

    def generate_srt_content(
        self,
        sections: List[ScriptSection],
        split_long_lines: bool = True,
        max_words_per_cue: int = 14,
    ) -> str:
        """
        Generate SRT formatted string from a list of ScriptSection objects.
        
        Args:
            sections: List of ScriptSection objects with timecodes and text.
            split_long_lines: If True, subdivides sections longer than 8s into
                              smaller subtitle cues proportionally for readability.
            max_words_per_cue: Maximum words before wrapping or splitting a cue.

        Returns:
            Properly formatted SRT text content with trailing newline.
        """
        entries = []
        cue_index = 1

        for sec in sections:
            words = sec.text.split()
            if not words:
                continue

            if not split_long_lines or sec.duration_seconds <= 8.0 or len(words) <= max_words_per_cue:
                # Single cue for this section
                start_str = format_seconds_to_srt_time(sec.start_seconds)
                end_str = format_seconds_to_srt_time(sec.end_seconds)
                text_wrapped = self._wrap_text(sec.text, max_chars_per_line=42)
                entries.append(f"{cue_index}\n{start_str} --> {end_str}\n{text_wrapped}\n")
                cue_index += 1
            else:
                # Subdivide longer sections into evenly-timed chunks based on word count
                num_chunks = max(2, (len(words) + max_words_per_cue - 1) // max_words_per_cue)
                words_per_chunk = (len(words) + num_chunks - 1) // num_chunks
                time_per_word = sec.duration_seconds / len(words)

                word_offset = 0
                for chunk_i in range(num_chunks):
                    chunk_words = words[word_offset : word_offset + words_per_chunk]
                    if not chunk_words:
                        break

                    chunk_start_sec = sec.start_seconds + word_offset * time_per_word
                    chunk_end_sec = min(
                        sec.end_seconds,
                        sec.start_seconds + (word_offset + len(chunk_words)) * time_per_word,
                    )
                    if chunk_i == num_chunks - 1:
                        chunk_end_sec = sec.end_seconds

                    chunk_text = " ".join(chunk_words)
                    text_wrapped = self._wrap_text(chunk_text, max_chars_per_line=42)

                    start_str = format_seconds_to_srt_time(chunk_start_sec)
                    end_str = format_seconds_to_srt_time(chunk_end_sec)
                    entries.append(f"{cue_index}\n{start_str} --> {end_str}\n{text_wrapped}\n")
                    cue_index += 1
                    word_offset += len(chunk_words)

        return "\n".join(entries).strip() + "\n"

    def write_srt_file(
        self,
        output_path: Path | str,
        sections: List[ScriptSection],
        split_long_lines: bool = True,
    ) -> Path:
        """Write SRT file to disk."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate_srt_content(sections, split_long_lines=split_long_lines)
        target.write_text(content, encoding="utf-8")
        return target

    def _wrap_text(self, text: str, max_chars_per_line: int = 42) -> str:
        words = text.split()
        lines = []
        current_line: List[str] = []
        current_len = 0

        for w in words:
            if current_len + len(w) + (1 if current_line else 0) > max_chars_per_line:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [w]
                    current_len = len(w)
                else:
                    lines.append(w)
                    current_len = 0
            else:
                current_line.append(w)
                current_len += len(w) + (1 if len(current_line) > 1 else 0)

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines[:2])  # Standard max 2 lines for video subtitles
