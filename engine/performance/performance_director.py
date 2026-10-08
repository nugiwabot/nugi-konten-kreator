"""
Dependency-free vocal performance coaching for finished scripts.

The learning output is intentionally inline and visual:
- arrows for pitch movement
- bold words for emphasis
- slash for thought boundaries
- ellipsis for deliberate pauses

The generator preserves script wording and only overlays delivery cues.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


STOPWORDS = {
    "yang", "dan", "atau", "di", "ke", "dari", "untuk", "dengan", "ini",
    "itu", "kita", "mereka", "ada", "akan", "jadi", "karena", "pada",
    "dalam", "sebuah", "lebih", "sudah", "masih", "bisa", "bukan",
    "hanya", "juga", "seperti", "bahwa", "adalah", "sebagai", "ketika",
    "para", "agar", "oleh", "tersebut",
}

REVEAL = ("ternyata", "sebenarnya", "masalahnya", "kuncinya", "yang menarik")
CONTRAST = ("tapi", "namun", "padahal", "justru", "sedangkan", "bukan")
REFLECT = ("jadi", "artinya", "berarti", "pada akhirnya", "mungkin")
EMOTION = ("aneh", "takut", "khawatir", "marah", "sedih", "mengejutkan")
QUESTION_START = ("kenapa", "mengapa", "bagaimana", "apa", "kok", "gimana")
LAND_MARKERS = ("pada akhirnya", "kesimpulannya", "yang sebenarnya", "bukanlah", "adalah")


@dataclass(frozen=True)
class PerformanceCue:
    index: int
    text: str
    role: str
    pitch: str
    pace: str
    emphasis: Optional[str]
    pause_before: float
    pause_after: float
    delivery: str
    why: str


@dataclass(frozen=True)
class PerformanceDocument:
    source_name: str
    cues: List[PerformanceCue]

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "schema_version": "2.0",
            "cues": [asdict(c) for c in self.cues],
        }


def _words(text: str) -> List[str]:
    return re.findall(r"[A-Za-zÀ-ÿ0-9%'-]+", text.lower())


def _meaningful_word(text: str) -> Optional[str]:
    for word in _words(text):
        word = re.sub(r"[^a-z0-9à-ÿ'-]", "", word)
        if len(word) >= 4 and word not in STOPWORDS:
            return word
    return None


def _marker(text: str, markers: Sequence[str]) -> bool:
    lower = text.lower()
    return any(item in lower for item in markers)


def split_thought_units(script: str) -> List[str]:
    """Split long paragraphs into teachable units without rewriting wording."""
    units: List[str] = []

    for raw_line in script.replace("\r\n", "\n").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue

        if line.startswith("#"):
            units.append(line)
            continue

        sentences = re.split(r"(?<=[.!?])\s+", line)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(_words(sentence)) > 34:
                chunks = re.split(
                    r"(?<=,)\s+(?=(?:tapi|namun|jadi|padahal|justru|ketika)\b)",
                    sentence,
                    flags=re.IGNORECASE,
                )
                units.extend(c.strip() for c in chunks if c.strip())
            else:
                units.append(sentence)

    return units


def classify_unit(text: str, index: int, total: int) -> Tuple[str, str, str, str, str]:
    lower = text.lower().strip()

    if text.startswith("#"):
        return "STRUCTURAL", "flat", "normal", "none", "Bagian struktur, bukan dialog."

    question = text.endswith("?") or re.match(
        r"^(kenapa|mengapa|bagaimana|apa|kok|gimana)\b", lower
    )
    reveal = _marker(text, REVEAL)
    contrast = _marker(text, CONTRAST)
    reflection = _marker(text, REFLECT)
    emotion = _marker(text, EMOTION)
    list_like = len(re.findall(r",|;", text)) >= 2

    if question:
        return "CURIOUS", "rising", "mixed", "0.6", (
            "Mulai seperti benar-benar bertanya; naik sedikit di pertanyaan."
        )
    if reveal:
        return "REVEAL", "contrast", "slow", "0.8", (
            "Bangun rasa ingin tahu lalu turunkan nada saat insight mendarat."
        )
    if contrast:
        return "CONTRAST", "contrast", "slow", "0.7", (
            "Beri perubahan arah yang terasa jelas tanpa berteriak."
        )
    if list_like:
        return "BUILD", "flat", "fast", "0.25", (
            "Sedikit percepat rangkaian informasi agar terasa bergerak."
        )
    if emotion:
        return "EMOTIVE", "contrast", "slow", "0.6", (
            "Gunakan warna suara, bukan volume berlebihan."
        )
    if reflection or index == total - 1:
        return "REFLECTIVE", "falling", "slow", "1.0", (
            "Perlambat dan land agar gagasan terasa personal."
        )
    if re.search(r"\d|%|tahun|juta|miliar|data|studi|penelitian", lower):
        return "MATTER-OF-FACT", "flat", "normal", "0.3", (
            "Utamakan artikulasi dan kredibilitas."
        )
    return "CONVERSATIONAL", "flat", "normal", "0.3", (
        "Bayangkan menjelaskan ini kepada satu orang."
    )


def _why(role: str) -> str:
    return {
        "CURIOUS": "Pertanyaan membuka attention loop.",
        "REVEAL": "Titik ini mengubah cara pandang.",
        "CONTRAST": "Kontras membantu otak menangkap perbedaan.",
        "BUILD": "Sedikit percepatan membangun momentum.",
        "EMOTIVE": "Warna suara membawa emosi tanpa teatrikal.",
        "REFLECTIVE": "Pelambatan membantu insight terasa personal.",
        "MATTER-OF-FACT": "Data perlu terdengar jelas dan kredibel.",
        "CONVERSATIONAL": "Baseline natural menjaga suara tetap manusiawi.",
    }.get(role, "Delivery natural.")


def _clean_heading(line: str) -> str:
    return re.sub(r"^#+\s*", "", line).strip()


def _split_clauses(text: str) -> List[str]:
    """Create readable speech phrases while preserving every original word."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    parts = re.split(r"(?<=[,;:])\s+", text)
    result: List[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if len(_words(part)) > 14:
            subparts = re.split(
                r"\s+(?=(?:namun|tapi|padahal|justru|sedangkan|ketika|dan|atau)\b)",
                part,
                flags=re.IGNORECASE,
            )
            result.extend(p.strip() for p in subparts if p.strip())
        else:
            result.append(part)

    return result


def _strip_terminal_punctuation(text: str) -> Tuple[str, str]:
    match = re.search(r"([.!?]+)$", text)
    if not match:
        return text, ""
    return text[: match.start()].rstrip(), match.group(1)


def _emphasis_word(
    text: str,
    role: str,
    clause_index: int,
    clause_count: int,
) -> Optional[str]:
    """Choose at most one visually emphasized word per clause."""
    words = _words(text)
    if not words:
        return None

    if role == "CURIOUS":
        candidates = [
            w for w in words
            if w not in QUESTION_START and w not in STOPWORDS and len(w) >= 4
        ]
        return candidates[-1] if candidates else None

    if role in {"REVEAL", "CONTRAST", "REFLECTIVE"}:
        candidates = [w for w in words if w not in STOPWORDS and len(w) >= 4]
        return candidates[-1] if candidates else None

    number = re.search(r"\b\d+(?:[.,]\d+)?%?\b", text)
    if number:
        return number.group(0)

    if role == "BUILD" and clause_index == 0:
        return _meaningful_word(text)

    if clause_index == clause_count - 1 and role in {"CONVERSATIONAL", "MATTER-OF-FACT"}:
        return _meaningful_word(text)

    return None


def _apply_emphasis(text: str, emphasis: Optional[str], pitch: str) -> str:
    if not emphasis:
        return text

    pattern = re.compile(
        rf"(?<![A-Za-zÀ-ÿ]){re.escape(emphasis)}(?![A-Za-zÀ-ÿ])",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return text

    word = match.group(0)
    arrow = {
        "rising": "↗",
        "falling": "↘",
        "contrast": "↗↘",
        "flat": "",
    }.get(pitch, "")
    replacement = f"**{word.upper()}{arrow}**"
    return text[:match.start()] + replacement + text[match.end():]


def _annotate_clause(
    clause: str,
    role: str,
    clause_index: int,
    clause_count: int,
) -> str:
    body, punctuation = _strip_terminal_punctuation(clause)

    is_question = role == "CURIOUS"
    is_reveal = _marker(body, REVEAL)
    is_contrast = _marker(body, CONTRAST)
    is_landing = (
        clause_index == clause_count - 1
        or _marker(body, LAND_MARKERS)
        or punctuation in {".", "?"}
    )

    if is_question:
        pitch = "rising"
    elif is_reveal or is_contrast:
        pitch = "contrast"
    elif is_landing:
        pitch = "falling"
    else:
        pitch = "flat"

    emphasis = _emphasis_word(body, role, clause_index, clause_count)
    body = _apply_emphasis(body, emphasis, pitch)

    if not emphasis:
        if pitch == "rising":
            body += "↗"
        elif pitch == "falling":
            body += "↘"
        elif pitch == "contrast":
            body += "↗↘"

    return body + punctuation


def render_inline_script(doc: PerformanceDocument) -> str:
    """Render the visual inline coaching format used by Nugi's examples."""
    out: List[str] = []

    for cue in doc.cues:
        if cue.role == "STRUCTURAL":
            out.append(f"# {_clean_heading(cue.text)}")
            out.append("")
            continue

        clauses = _split_clauses(cue.text)
        if not clauses:
            continue

        rendered = [
            _annotate_clause(clause, cue.role, i, len(clauses))
            for i, clause in enumerate(clauses)
        ]

        line = " / ".join(rendered)

        # A long pause belongs at a thought transition, not after every line.
        if cue.pause_after >= 0.8:
            line += " ..."

        out.append(line)
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def annotate_script(script: str, source_name: str = "script") -> PerformanceDocument:
    units = split_thought_units(script)
    cues: List[PerformanceCue] = []

    for index, unit in enumerate(units, start=1):
        role, pitch, pace, after, delivery = classify_unit(
            unit, index - 1, len(units)
        )

        if role == "STRUCTURAL":
            cues.append(
                PerformanceCue(
                    index, unit, role, pitch, pace, None, 0.0, 0.0,
                    delivery, "Struktur dokumen."
                )
            )
            continue

        cues.append(
            PerformanceCue(
                index=index,
                text=unit,
                role=role,
                pitch=pitch,
                pace=pace,
                emphasis=_emphasis_word(unit, role, 0, 1),
                pause_before=0.35 if role in {"REVEAL", "CONTRAST"} else 0.0,
                pause_after=float(after),
                delivery=delivery,
                why=_why(role),
            )
        )

    return PerformanceDocument(source_name, cues)


def render_annotated(doc: PerformanceDocument, include_legend: bool = True) -> str:
    """Backward-compatible detailed sheet for debugging/advanced users."""
    out = ["# NUGI PERFORMANCE SHEET", "", f"Source: {doc.source_name}", ""]

    if include_legend:
        out += [
            "## Cara membaca",
            "",
            "- ↗ = naik sedikit; ↘ = turun/land; ↗↘ = naik lalu turun.",
            "- BOLD = kata yang mendapat penekanan.",
            "- / = batas frasa; ... = jeda lebih panjang.",
            "- Jangan menaikkan volume secara berlebihan.",
            "",
        ]

    out.append(render_inline_script(doc))
    return "\n".join(out).rstrip() + "\n"


def render_clean(doc: PerformanceDocument) -> str:
    return "\n\n".join(cue.text for cue in doc.cues).strip() + "\n"


def write_outputs(
    script_text: str,
    output_dir: Path,
    source_name: str = "script",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = annotate_script(script_text, source_name)

    annotated = output_dir / "script_performance.md"
    teleprompter = output_dir / "script_teleprompter.txt"
    plan = output_dir / "performance_plan.json"

    annotated.write_text(render_inline_script(doc), encoding="utf-8")
    teleprompter.write_text(render_clean(doc), encoding="utf-8")
    plan.write_text(
        json.dumps(doc.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "annotated": str(annotated),
        "teleprompter": str(teleprompter),
        "plan": str(plan),
        "segments": len(doc.cues),
        "format": "inline-performance-v2",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a finished script into a visual inline vocal-performance learning sheet."
    )
    parser.add_argument("input", nargs="?")
    parser.add_argument("--text")
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--no-legend",
        action="store_true",
        help="Kept for compatibility; inline output has no legend by default.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.text:
        script_text, source = args.text, "inline-script"
    elif args.input:
        path = Path(args.input)
        script_text, source = path.read_text(encoding="utf-8"), path.name
    else:
        parser.error("Provide a script file or --text.")
        return 2

    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else (
            Path(args.input).with_name(Path(args.input).stem + "_performance")
            if args.input
            else Path("performance_output")
        )
    )

    doc = annotate_script(script_text, source)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "script_performance.md").write_text(
        render_inline_script(doc), encoding="utf-8"
    )
    (out_dir / "script_teleprompter.txt").write_text(
        render_clean(doc), encoding="utf-8"
    )
    (out_dir / "performance_plan.json").write_text(
        json.dumps(doc.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = {
        "status": "ok",
        "segments": len(doc.cues),
        "format": "inline-performance-v2",
        "annotated": str(out_dir / "script_performance.md"),
        "teleprompter": str(out_dir / "script_teleprompter.txt"),
        "plan": str(out_dir / "performance_plan.json"),
    }

    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else result
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
