
"""Dependency-free vocal performance coaching for finished scripts."""

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
}

REVEAL = ("ternyata", "sebenarnya", "masalahnya", "kuncinya", "yang menarik")
CONTRAST = ("tapi", "namun", "padahal", "justru", "sedangkan", "bukan")
REFLECT = ("jadi", "artinya", "berarti", "pada akhirnya", "mungkin")
EMOTION = ("aneh", "takut", "khawatir", "marah", "sedih", "mengejutkan")

PITCH_LABEL = {
    "rising": "↗ naik tipis",
    "falling": "↘ turun / land",
    "flat": "→ conversational",
    "contrast": "↗↘ naik lalu turun",
}

PACE_LABEL = {
    "slow": "🐢 lambat",
    "normal": "▶ normal",
    "fast": "⚡ sedikit cepat",
    "mixed": "↔ normal lalu melambat",
}


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
            "schema_version": "1.0",
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
    """Keep wording intact while splitting the script into coachable units."""
    units: List[str] = []
    for raw_line in script.replace("\r\n", "\n").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if line.startswith("#"):
            units.append(line)
            continue
        if len(_words(line)) > 34:
            chunks = re.split(
                r"(?<=[.!?])\s+|(?<=,)\s+(?=(?:tapi|namun|jadi|padahal|ternyata)\b)",
                line,
                flags=re.IGNORECASE,
            )
            units.extend(c.strip() for c in chunks if c.strip())
        else:
            units.append(line)
    return units


def _emphasis(text: str, role: str) -> Optional[str]:
    if role == "CONVERSATIONAL":
        return None
    match = re.search(r"\b\d+(?:[.,]\d+)?%?\b", text)
    if match:
        return match.group(0)
    meaningful = _meaningful_word(text)
    return meaningful.upper() if meaningful else None


def classify_unit(text: str, index: int, total: int) -> Tuple[str, str, str, str, str]:
    lower = text.lower()
    if text.startswith("#"):
        return "STRUCTURAL", "flat", "normal", "none", "Bagian struktur, bukan dialog."

    question = text.endswith("?") or re.match(
        r"^(kenapa|mengapa|bagaimana|apa|kok|gimana)\b", lower
    )
    reveal = _marker(text, REVEAL)
    contrast = _marker(text, CONTRAST)
    reflection = _marker(text, REFLECT)
    emotion = _marker(text, EMOTION)
    pieces = [p for p in re.split(r"[.!?]+", text) if p.strip()]
    list_like = len(pieces) >= 3 and all(len(_words(p)) <= 7 for p in pieces)

    if question:
        return "CURIOUS", "rising", "mixed", "0.6", (
            "Tanya seperti benar-benar sedang mencari jawaban; jangan seperti membaca slogan."
        )
    if reveal:
        return "REVEAL", "contrast", "slow", "0.8", (
            "Tahan sedikit sebelum kata kunci, lalu turunkan nada saat insight mendarat."
        )
    if contrast:
        return "CONTRAST", "contrast", "slow", "0.7", (
            "Buat perbedaan terasa jelas tanpa menaikkan volume berlebihan."
        )
    if list_like:
        return "BUILD", "flat", "fast", "0.25", (
            "Naikkan energi sedikit dan biarkan tiap potongan terasa seperti langkah berikutnya."
        )
    if emotion:
        return "EMOTIVE", "contrast", "slow", "0.6", (
            "Biarkan emosi muncul lewat warna suara, bukan dengan berteriak."
        )
    if reflection or index == total - 1:
        return "REFLECTIVE", "falling", "slow", "1.0", (
            "Perlambat dan beri ruang agar penonton memproses gagasan."
        )
    if re.search(r"\d|%|tahun|juta|miliar|data|studi|penelitian", lower):
        return "MATTER-OF-FACT", "flat", "normal", "0.3", (
            "Utamakan artikulasi dan kredibilitas, bukan dramatisasi."
        )
    return "CONVERSATIONAL", "flat", "normal", "0.3", (
        "Bayangkan sedang menjelaskan ini ke satu orang, bukan membaca kepada ruangan."
    )


def annotate_script(script: str, source_name: str = "script") -> PerformanceDocument:
    units = split_thought_units(script)
    cues: List[PerformanceCue] = []
    for index, unit in enumerate(units, start=1):
        role, pitch, pace, after, delivery = classify_unit(unit, index - 1, len(units))
        if role == "STRUCTURAL":
            cues.append(
                PerformanceCue(index, unit, role, pitch, pace, None, 0.0, 0.0, delivery, "Struktur dokumen.")
            )
            continue
        cues.append(
            PerformanceCue(
                index=index,
                text=unit,
                role=role,
                pitch=pitch,
                pace=pace,
                emphasis=_emphasis(unit, role),
                pause_before=0.35 if role in {"REVEAL", "CONTRAST"} else 0.0,
                pause_after=float(after),
                delivery=delivery,
                why=_why(role),
            )
        )
    return PerformanceDocument(source_name, cues)


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


def render_annotated(doc: PerformanceDocument, include_legend: bool = True) -> str:
    out = ["# NUGI PERFORMANCE SHEET", "", f"**Source:** {doc.source_name}", ""]
    if include_legend:
        out += [
            "## Cara membaca",
            "",
            "- **Pitch** = naik/turun tinggi nada sedikit, bukan berteriak.",
            "- **Pace** = atur cepat-lambat ritme bicara.",
            "- **Emphasis** = fokus pada kata penting lewat tempo, pitch, artikulasi, atau jeda.",
            "- **Pause** = diam dengan sengaja untuk memberi ruang pada pikiran.",
            "- **Delivery** = niat saat mengucapkan kalimat.",
            "- Cue adalah panduan latihan, bukan teks yang dibaca.",
            "",
        ]
    for cue in doc.cues:
        if cue.role == "STRUCTURAL":
            out += [f"## {cue.text}", ""]
            continue
        out += [
            f"## {cue.index:02d} — {cue.role}",
            "",
            f"**Pitch:** {PITCH_LABEL[cue.pitch]}",
            f"**Pace:** {PACE_LABEL[cue.pace]}",
            f"**Emphasis:** {cue.emphasis or 'tidak perlu — biarkan natural'}",
            f"**Pause:** {cue.pause_before:.2f}s sebelum · {cue.pause_after:.2f}s sesudah",
            f"**Delivery:** {cue.delivery}",
            f"**Kenapa:** {cue.why}",
            "",
            f"> {cue.text}",
            "",
        ]
    return "\n".join(out).rstrip() + "\n"


def render_clean(doc: PerformanceDocument) -> str:
    return "\n\n".join(cue.text for cue in doc.cues).strip() + "\n"


def write_outputs(script_text: str, output_dir: Path, source_name: str = "script") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = annotate_script(script_text, source_name)
    annotated = output_dir / "script_performance.md"
    teleprompter = output_dir / "script_teleprompter.txt"
    plan = output_dir / "performance_plan.json"
    annotated.write_text(render_annotated(doc), encoding="utf-8")
    teleprompter.write_text(render_clean(doc), encoding="utf-8")
    plan.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "ok",
        "annotated": str(annotated),
        "teleprompter": str(teleprompter),
        "plan": str(plan),
        "segments": len(doc.cues),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert a finished script into a vocal-performance learning sheet.")
    parser.add_argument("input", nargs="?")
    parser.add_argument("--text")
    parser.add_argument("--output-dir")
    parser.add_argument("--no-legend", action="store_true")
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
    out_dir = Path(args.output_dir) if args.output_dir else (
        Path(args.input).with_name(Path(args.input).stem + "_performance")
        if args.input else Path("performance_output")
    )
    if args.no_legend:
        doc = annotate_script(script_text, source)
        (out_dir / "script_performance.md").parent.mkdir(parents=True, exist_ok=True)
        (out_dir / "script_performance.md").write_text(render_annotated(doc, False), encoding="utf-8")
        (out_dir / "script_teleprompter.txt").write_text(render_clean(doc), encoding="utf-8")
        (out_dir / "performance_plan.json").write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        result = {"status": "ok", "segments": len(doc.cues)}
    else:
        result = write_outputs(script_text, out_dir, source)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
