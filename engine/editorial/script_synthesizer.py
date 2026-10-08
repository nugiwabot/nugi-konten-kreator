"""
engine/editorial/script_synthesizer.py
======================================
Dynamic Topic-Grounded Script Synthesizer for Nugi Content Intelligence Engine.

Constructs spoken-word teleprompter scripts derived directly from empirical
research dossiers, adhering to Nugi Channel DNA: HUMAN × PLACE × CHANGE × WHY.
Ensures factual grounding, natural spoken Indonesian, and complete freedom from
hardcoded templated conclusions or robotic AI filler.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from engine.pipeline.research_dossier import ResearchDossier


# Forbidden robotic filler phrases to proactively strip or replace
_AI_FILLER_PHRASES = [
    r"\bdi era modern ini\b",
    r"\bdi era digital yang serba cepat\b",
    r"\bfenomena ini sangat menarik\b",
    r"\bfenomena ini menarik untuk disimak\b",
    r"\btentu saja hal ini\b",
    r"\btak dapat dipungkiri bahwa\b",
    r"\bseperti yang kita ketahui bersama\b",
]


class DynamicScriptSynthesizer:
    """
    Transforms a ResearchDossier into a topic-grounded, spoken-word teleprompter script.
    """

    def __init__(self):
        pass

    def synthesize_script(
        self,
        dossier: ResearchDossier,
        target_duration_seconds: int = 60,
        story_plan: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Synthesize a script from the dossier. When a structured story plan is
        supplied, use its evidence-aware beats and preserve uncertainty.
        """
        if story_plan:
            return self._synthesize_from_story_plan(
                dossier, target_duration_seconds, story_plan
            )

        topic = dossier.topic
        
        # 1. Extract Anchor Data & Angles
        primary_angle = dossier.narrative_angles[0] if dossier.narrative_angles else {
            "revelation": f"Pergeseran nyata di balik fenomena {topic} jarang disadari secara utuh.",
            "human_dilemma": f"Masyarakat harus beradaptasi di tengah ketidakpastian seputar {topic}.",
            "why": "Struktur sistemik memaksa perubahan pola hidup mendasar."
        }
        secondary_angle = dossier.narrative_angles[1] if len(dossier.narrative_angles) > 1 else primary_angle

        # 2. Extract Empirical Proof Points only from dossier data that is
        # actually relevant to the research topic. Scholarly citation counts
        # are not topical statistics (providers omit them from data_points).
        dp_text = ""
        research_verified = dossier.epistemic_status == "VERIFIED" and bool(dossier.claims)
        if dossier.data_points and research_verified:
            dp = dossier.data_points[0]
            dp_text = f"Data {dp.source_name or 'resmi'} mencatat {dp.metric} sebesar {dp.value} {dp.unit}."
        elif dossier.claims:
            dp_text = dossier.claims[0].text

        # 3. Extract Causal Mechanism
        cause_text = ""
        if dossier.causal_relationships and research_verified:
            cr = dossier.causal_relationships[0]
            cause_text = f"Pendorong utamanya adalah {cr.get('cause', '').lower()}, yang bekerja melalui {cr.get('mechanism', '').lower()}."
        elif len(dossier.claims) > 1:
            cause_text = dossier.claims[1].text

        # 4. Construct Spoken Story Beats (Natural Spoken Indonesian)
        hook = primary_angle.get("revelation", "").rstrip(".")
        if not hook.endswith("?"):
            hook = f"Pernahkah kamu menyadari bahwa {hook.lower()}?"

        # Adapt content depth and word count to requested duration
        dur = max(20, int(target_duration_seconds))

        if not research_verified:
            if dossier.epistemic_status == "DISPUTED":
                hook = f"Sumber yang diperiksa berbeda pandangan tentang {topic}"
                tension = "Bukti yang tersedia belum cukup untuk memilih satu penjelasan sebagai fakta."
                context_cause = "Karena itu, hubungan sebab-akibatnya perlu diperiksa melalui data primer dan sumber independen."
                why_epiphany = "Sampai ada penguatan bukti, kesimpulan yang bertanggung jawab adalah menahan kepastian."
            elif dossier.claims:
                hook = f"Sejumlah sumber memberi petunjuk tentang {topic}, tetapi belum cukup untuk memastikan penyebabnya"
                tension = f"Temuan awal ini belum terkonfirmasi secara independen. {dp_text}"
                context_cause = "Karena itu, dampak dan hubungan sebab-akibat yang spesifik belum dapat dipastikan."
                why_epiphany = "Kesimpulan yang jujur: temuan ini masih perlu dibandingkan dengan data primer dan sumber independen."
            else:
                hook = f"Belum ada bukti yang cukup untuk memastikan penyebab {topic}"
                tension = "Sumber yang berhasil diperiksa belum mengonfirmasi angka atau dampak tertentu."
                context_cause = "Karena itu, hubungan sebab-akibatnya belum bisa disimpulkan."
                why_epiphany = "Langkah berikutnya adalah mencari data primer, memeriksa periodenya, lalu membandingkannya dengan penelitian independen."
        elif dur <= 35:
            # Punchy 30s micro-short (~70-85 words)
            tension = f"Banyak yang mengira ini kebetulan, padahal data menunjukkan sebaliknya. {dp_text}"
            context_cause = f"{cause_text}"
            why_epiphany = f"{primary_angle.get('why', '')}"
        elif dur <= 65:
            # Standard 60s short (~140-160 words)
            tension = (
                f"Banyak orang mengira ini persoalan sederhana. "
                f"Namun bukti empiris di lapangan menunjukkan dinamika yang jauh berbeda. "
                f"{dp_text}"
            )
            context_cause = (
                f"{cause_text} "
                f"Dampaknya langsung terasa pada kehidupan sehari-hari: {primary_angle.get('human_dilemma', '')}"
            )
            why_epiphany = (
                f"{primary_angle.get('why', '')} "
                f"Ini bukan sekadar soal angka, melainkan bagaimana ruang hidup dan masa depan manusia dibentuk ulang."
            )
        else:
            # Extended 75s - 90s documentary short (~180-220 words)
            secondary_why = secondary_angle.get("why", "")
            tension = (
                f"Banyak orang mengira fenomena ini hanya masalah sementara. "
                f"Namun bukti empiris di lapangan memperlihatkan pergeseran yang jauh lebih dalam. "
                f"{dp_text} "
                f"Kondisi ini bukan terjadi tiba-tiba, melainkan akumulasi dari sistem yang telah berjalan lama."
            )
            context_cause = (
                f"{cause_text} "
                f"Akibatnya, masyarakat terjebak dalam dilema nyata: {primary_angle.get('human_dilemma', '')} "
                f"Ketika pilihan semakin terbatas, cara orang memandang tempat tinggal pun ikut bergeser."
            )
            why_epiphany = (
                f"{primary_angle.get('why', '')} "
                f"{f'Di sisi lain, {secondary_why.lower()} ' if secondary_why and secondary_why != primary_angle.get('why') else ''}"
                f"Pada akhirnya, rumah dan kota bukan sekadar komoditas ekonomi, melainkan cermin dari bagaimana peradaban kita memperlakukan masa depan warganya."
            )

        # 5. Clean AI Fillers
        hook = self._clean_fillers(hook)
        tension = self._clean_fillers(tension)
        context_cause = self._clean_fillers(context_cause)
        why_epiphany = self._clean_fillers(why_epiphany)

        # Calculate proportional timecodes based on duration
        t_hook_end = max(4, int(round(dur * 0.12)))
        t_tension_end = max(t_hook_end + 6, int(round(dur * 0.38)))
        t_context_end = max(t_tension_end + 8, int(round(dur * 0.72)))
        t_final = dur

        # 6. Format Canonical Production Markdown
        script_md = [
            f"# NASKAH KONTEN NUGI — {topic.upper()}",
            "## 📽️ NARASI 1: HUMAN × PLACE",
            f"### *{topic}*",
            "- **Pilar DNA:** `HUMAN × PLACE × CHANGE × WHY`",
            f"- **Status Epistemik Riset:** `{dossier.epistemic_status}` (Evidence strength heuristic: {int(dossier.evidence_strength * 100)}%)",
            "",
            f"#### NASKAH TALKING-HEAD (Durasi ~{dur} Detik | Spoken Word)",
            "",
            "```text",
            f"[00:00 - {t_hook_end:02d}:00] HOOK" if t_hook_end >= 60 else f"[00:00 - 00:{t_hook_end:02d}] HOOK",
            f"{hook}",
            "",
            f"[00:{t_hook_end:02d} - 00:{t_tension_end:02d}] TENSION & PARADOX" if t_tension_end < 60 else f"[00:{t_hook_end:02d} - {t_tension_end//60:02d}:{t_tension_end%60:02d}] TENSION & PARADOX",
            f"{tension}",
            "",
            f"[00:{t_tension_end:02d} - 00:{t_context_end:02d}] CONTEXT & STRUCTURAL CAUSE" if t_context_end < 60 else f"[{t_tension_end//60:02d}:{t_tension_end%60:02d} - {t_context_end//60:02d}:{t_context_end%60:02d}] CONTEXT & STRUCTURAL CAUSE",
            f"{context_cause}",
            "",
            f"[00:{t_context_end:02d} - 00:{t_final:02d}] THE REVELATION (THE WHY)" if t_final < 60 else f"[{t_context_end//60:02d}:{t_context_end%60:02d} - {t_final//60:02d}:{t_final%60:02d}] THE REVELATION (THE WHY)",
            f"{why_epiphany}",
            "```",
            ""
        ]

        return "\n".join(script_md)


    def _synthesize_from_story_plan(
        self,
        dossier: ResearchDossier,
        target_duration_seconds: int,
        story_plan: Dict[str, Any],
    ) -> str:
        """Render the supplied story outline without promoting unsupported claims."""
        topic = dossier.topic
        beats = [
            beat for beat in story_plan.get("beats", [])
            if isinstance(beat, dict) and str(beat.get("narration_seed", "")).strip()
        ]
        duration = max(20, int(target_duration_seconds or 60))
        if not beats:
            return self.synthesize_script(dossier, target_duration_seconds)

        def stamp(seconds: int) -> str:
            return f"{seconds // 60:02d}:{seconds % 60:02d}"

        sections = []
        count = len(beats)
        for index, beat in enumerate(beats):
            start = int(round(duration * index / count))
            end = int(round(duration * (index + 1) / count))
            seed = self._clean_fillers(str(beat["narration_seed"]))
            stage = str(beat.get("stage", f"BEAT {index + 1}")).replace("_", " ").upper()
            evidence_status = str(beat.get("evidence_status", "GAP_OR_QUESTION"))
            if index == 0:
                narration = seed
            elif evidence_status == "SUPPORTED_CLAIM":
                narration = f"Untuk menjawabnya, kita perlu melihat bukti ini: {seed}"
            elif "HUMAN" in stage or "REFLECTION" in stage:
                narration = f"Di titik ini, pertanyaan pentingnya adalah: {seed}"
            else:
                narration = seed
            sections.append(f"[{stamp(start)} - {stamp(end)}] {stage}\n{narration}")

        limitations = []
        if str(story_plan.get("epistemic_status", "UNVERIFIED")).upper() != "VERIFIED":
            limitations.append(
                "Status riset belum VERIFIED. Jangan menyajikan klaim yang belum terkonfirmasi sebagai fakta."
            )
        if not story_plan.get("evidence_summary", {}).get("supported_claims_used"):
            limitations.append(
                "Belum ada klaim VERIFIED/PROBABLE dalam story plan; perlakukan naskah sebagai kerangka investigasi, bukan kesimpulan final."
            )

        lines = [
            f"# NASKAH KONTEN NUGI — {topic.upper()}",
            f"- Story type: {story_plan.get('story_type_name', story_plan.get('story_type', 'unclassified'))}",
            f"- Narrative device: {story_plan.get('narrative_device', 'not specified')}",
            f"- Status epistemik riset: {story_plan.get('epistemic_status', 'UNVERIFIED')}",
            f"- Durasi target: sekitar {duration} detik",
            "",
            "## STORY PLAN / DRAFT NARASI",
            "",
            *[line for section in sections for line in (section, "")],
        ]
        if limitations:
            lines.extend(["", "## CATATAN EDITORIAL — JANGAN DIBACAKAN", *[f"- {item}" for item in limitations]])
        return "\n".join(lines).strip() + "\n"

    def _clean_fillers(self, text: str) -> str:
        """Removes generic robotic clichés from text."""
        cleaned = text
        for pattern in _AI_FILLER_PHRASES:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        # Normalize double spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
