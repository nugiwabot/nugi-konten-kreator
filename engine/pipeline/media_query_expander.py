"""
engine/pipeline/media_query_expander.py
========================================
Converts natural-language visual requests into structured search strategies.

Key responsibilities:
1. Detect requested media type (image / video / any) from natural language cues.
2. Detect if the request is historical (year hints, archival keywords).
3. Generate multiple expanded search queries from the core concept.
4. Support script-to-visual extraction (multi-scene scripts).

DESIGN PRINCIPLES:
- No keyword whitelist. Accepts any visual concept.
- No hardcoded topic categories.
- Works fully offline — no LLM dependency.
- Indonesian + English input supported.
- The same request, run twice, produces the same queries (deterministic).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Media type detection ──────────────────────────────────────────────────────

_VIDEO_CUES = {
    # Indonesian
    "footage", "video", "film", "rekaman", "klip", "cuplikan",
    "dokumenter", "tayangan", "siaran",
    # English
    "clip", "recording", "documentary", "motion picture", "film",
}
_IMAGE_CUES = {
    # Indonesian
    "foto", "gambar", "potret", "ilustrasi", "lukisan",
    "portrait", "gambar diam", "fotografi",
    # English
    "photo", "photograph", "picture", "image", "illustration",
    "painting", "drawing", "sketch", "portrait",
}

# ── Historical content detection ──────────────────────────────────────────────

_HISTORICAL_CUES = {
    "asli", "arsip", "lama", "kuno", "sejarah", "bersejarah",
    "archival", "archive", "historical", "vintage", "original",
    "antique", "era", "century", "abad", "tempo dulu", "zaman dulu",
    "wartime", "perang dunia",
}

# Year pattern: 4-digit year before 2010
_YEAR_RE = re.compile(r"\b(1[0-9]{3}|200[0-9])\b")

# ── Stop words (stripped before generating English variants) ──────────────────

_ID_STOP = {
    "cari", "carikan", "saya", "kami", "satu", "dua", "tiga", "empat",
    "lima", "untuk", "yang", "dan", "di", "ke", "dari", "dengan",
    "tentang", "mengenai", "adalah", "ini", "itu", "bisa",
    "tolong", "minta", "ingin", "mau",
}
_EN_STOP = {
    "find", "search", "get", "show", "me", "some", "a", "an", "the",
    "of", "in", "on", "at", "for", "with", "about", "related", "please",
    "look", "for",
}

# ── Simple Indonesian → English concept map (expandable) ─────────────────────
# This is NOT a whitelist — it is a translation helper for common phrases.
# Uncommon/unknown words are left as-is (they often work in Wikimedia/IA anyway).

_ID_EN_PHRASES = {
    "perang dunia": "world war",
    "perang dunia kedua": "world war II",
    "perang dunia pertama": "world war I",
    "tentara": "soldiers",
    "tentara sekutu": "allied soldiers",
    "pendaratan": "landing",
    "pantai": "beach",
    "manusia": "human",
    "orang": "person",
    "kota": "city",
    "gedung": "building",
    "kantor": "office",
    "pabrik": "factory",
    "revolusi industri": "industrial revolution",
    "keramaian": "crowd",
    "pemimpin": "leader",
    "berbicara": "speaking",
    "kesendirian": "loneliness",
    "sendirian": "alone",
    "kesepian": "lonely",
    "kemerdekaan": "independence",
    "proklamasi": "proclamation",
    "presiden": "president",
    "ketakutan": "fear",
    "harapan": "hope",
    "kehilangan": "loss",
    "kemenangan": "victory",
    "konflik": "conflict",
    "ambisi": "ambition",
    "masa depan": "future",
    "teknologi": "technology",
    "alam": "nature",
    "gunung": "mountain",
    "laut": "ocean",
    "sungai": "river",
    "hutan": "forest",
}


@dataclass
class ExpandedQuery:
    """Structured result of query expansion."""
    original_request: str
    detected_media_type: str              # "image" | "video" | "any"
    primary_queries: List[str]            # Most specific queries
    expanded_queries: List[str]           # Broader/alternative queries
    is_historical: bool
    year_hint: Optional[str]              # e.g. "1944"
    is_script_mode: bool = False
    scene_queries: List[List[str]] = field(default_factory=list)
    # Ordered deduplicated list of all queries to run
    all_queries: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.all_queries:
            seen: set = set()
            merged: List[str] = []
            for q in (self.primary_queries + self.expanded_queries):
                qn = q.strip()
                if qn and qn not in seen:
                    seen.add(qn)
                    merged.append(qn)
            self.all_queries = merged


class MediaQueryExpander:
    """
    Converts a natural-language visual request into an ExpandedQuery
    containing multiple search strategy variants.

    Works fully offline — no external API calls.
    Accepts any topic: historical, abstract, conceptual, emotional, modern.
    """

    def expand(
        self,
        user_request: str,
        media_type_override: Optional[str] = None
    ) -> ExpandedQuery:
        """
        Main entry point.

        Args:
            user_request: Raw natural-language string from user.
            media_type_override: Force media_type if already known externally.

        Returns:
            ExpandedQuery with primary + expanded queries ready for providers.
        """
        if not user_request.strip():
            return ExpandedQuery(
                original_request=user_request,
                detected_media_type="any",
                primary_queries=[],
                expanded_queries=[],
                is_historical=False,
                year_hint=None,
            )

        text = user_request.strip()

        # 1. Detect media type
        media_type = media_type_override or self._detect_media_type(text)

        # 2. Detect historical context
        is_historical, year_hint = self._detect_historical(text)

        # 3. Extract core concept (strip action words and media type words)
        core_concept = self._extract_core_concept(text)

        # 4. Build primary queries
        primary_queries = self._build_primary_queries(
            core_concept, year_hint, is_historical
        )

        # 5. Build expanded/alternative queries
        expanded_queries = self._build_expanded_queries(
            core_concept, year_hint, is_historical, media_type
        )

        return ExpandedQuery(
            original_request=user_request,
            detected_media_type=media_type,
            primary_queries=primary_queries,
            expanded_queries=expanded_queries,
            is_historical=is_historical,
            year_hint=year_hint,
        )

    def expand_script(
        self,
        script_text: str,
        folder_hint: Optional[str] = None
    ) -> List[ExpandedQuery]:
        """
        Script-to-visual mode: extract visual scenes from a long script
        and generate an ExpandedQuery per scene.

        The script is split into logical segments (paragraphs / sentences)
        and each segment is scored for visual richness.
        Only segments above a minimum richness threshold are retained.
        """
        scenes = self._extract_script_scenes(script_text)
        results: List[ExpandedQuery] = []
        for scene_text in scenes:
            eq = self.expand(scene_text)
            eq.is_script_mode = True
            if eq.all_queries:  # Only add if we got something useful
                results.append(eq)
        return results

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _detect_media_type(self, text: str) -> str:
        """Return 'image', 'video', or 'any' based on cue words in text."""
        lower = text.lower()
        words = set(re.findall(r"\b\w+\b", lower))

        has_video = bool(words & _VIDEO_CUES)
        has_image = bool(words & _IMAGE_CUES)

        if has_video and not has_image:
            return "video"
        if has_image and not has_video:
            return "image"
        return "any"

    def _detect_historical(self, text: str) -> tuple[bool, Optional[str]]:
        """Return (is_historical, year_hint)."""
        lower = text.lower()
        words = set(re.findall(r"\b\w+\b", lower))

        year_match = _YEAR_RE.search(text)
        year_hint = year_match.group(0) if year_match else None

        cue_match = bool(words & _HISTORICAL_CUES)
        has_year = year_hint is not None

        return (cue_match or has_year), year_hint

    # ------------------------------------------------------------------
    # Core concept extraction
    # ------------------------------------------------------------------

    def _extract_core_concept(self, text: str) -> str:
        """
        Strip action verbs and media-type nouns from the request,
        leaving the visual subject/concept.

        Examples:
          "Cari foto Albert Einstein" → "Albert Einstein"
          "Carikan footage D-Day 1944" → "D-Day 1944"
          "Cari visual orang kesepian di keramaian" → "orang kesepian di keramaian"
        """
        lower = text.lower()

        # Translate Indonesian phrases to English equivalents first
        translated = lower
        # Sort by length desc so longer phrases match first
        for id_phrase, en_phrase in sorted(
            _ID_EN_PHRASES.items(), key=lambda x: -len(x[0])
        ):
            translated = translated.replace(id_phrase, en_phrase)

        # Tokenize
        tokens = re.findall(r"\b[\w'-]+\b", translated)

        # Remove stop words
        kept = [
            t for t in tokens
            if t not in _ID_STOP and t not in _EN_STOP
            and t not in _VIDEO_CUES and t not in _IMAGE_CUES
        ]

        concept = " ".join(kept).strip()

        # If extraction left nothing meaningful, fall back to original (trimmed)
        if len(concept) < 3:
            concept = text.strip()

        return concept

    # ------------------------------------------------------------------
    # Query generation
    # ------------------------------------------------------------------

    def _build_primary_queries(
        self,
        core_concept: str,
        year_hint: Optional[str],
        is_historical: bool,
    ) -> List[str]:
        """Build 1–3 most specific queries."""
        queries: List[str] = []

        # Most specific: concept + year if available
        if year_hint and year_hint not in core_concept:
            queries.append(f"{core_concept} {year_hint}")

        # Concept itself
        queries.append(core_concept)

        # Historical qualifier
        if is_historical:
            queries.append(f"{core_concept} archival historical")

        return self._dedup(queries)

    def _build_expanded_queries(
        self,
        core_concept: str,
        year_hint: Optional[str],
        is_historical: bool,
        media_type: str,
    ) -> List[str]:
        """Build additional alternative queries for broader coverage."""
        queries: List[str] = []

        # Media type qualifier
        if media_type == "video":
            queries.append(f"{core_concept} footage film")
        elif media_type == "image":
            queries.append(f"{core_concept} photograph")

        # Archival variants for historical content
        if is_historical:
            queries.append(f"{core_concept} archive")
            queries.append(f"{core_concept} documentary")
            if year_hint:
                queries.append(f"{core_concept} {year_hint} archival")

        # Split multi-word concepts → broader individual term search
        concept_words = core_concept.split()
        if len(concept_words) > 2:
            # Try combinations of the most significant words
            significant = [w for w in concept_words if len(w) > 3]
            if len(significant) >= 2:
                queries.append(" ".join(significant[:3]))
                queries.append(" ".join(significant[-3:]))

        # Synonym/related expansions for a few common abstract concepts
        # These are NOT a whitelist — they augment; if no match, no expansion.
        abstract_expansions = {
            "lonely": ["solitude", "isolation", "alone crowd"],
            "loneliness": ["solitude urban", "isolated person city"],
            "crowd": ["crowded street", "mass of people", "urban crowd"],
            "fear": ["scared face", "terror anxiety"],
            "victory": ["celebration triumph", "winning moment"],
            "ambition": ["determined leader", "striving achievement"],
            "conflict": ["battle confrontation", "opposing groups"],
            "loss": ["grief mourning", "sadness despair"],
            "hope": ["inspiration aspiration", "optimism future"],
            "leader": ["speaker crowd", "public address leader"],
        }
        for keyword, variants in abstract_expansions.items():
            if keyword in core_concept.lower():
                queries.extend(variants)
                break  # Only expand on the first match

        return self._dedup(queries)

    @staticmethod
    def _dedup(queries: List[str]) -> List[str]:
        """Deduplicate while preserving order."""
        seen: set = set()
        result: List[str] = []
        for q in queries:
            qn = q.strip()
            if qn and qn not in seen:
                seen.add(qn)
                result.append(qn)
        return result

    # ------------------------------------------------------------------
    # Script scene extraction
    # ------------------------------------------------------------------

    def _extract_script_scenes(self, script_text: str) -> List[str]:
        """
        Split a script into candidate visual scene descriptions.

        Strategy:
        1. Split on double newlines (paragraph boundaries).
        2. For single long paragraphs, also split on sentence boundaries.
        3. Score each segment for visual richness (mentions of place, people,
           action, time period) and keep segments above threshold.
        """
        # Split on paragraph boundaries first
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", script_text)]
        segments: List[str] = []

        for para in paragraphs:
            if not para:
                continue
            # If paragraph is very long, split into sentences
            if len(para) > 200:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                segments.extend([s.strip() for s in sentences if s.strip()])
            else:
                segments.append(para)

        # Filter: keep only visually rich segments
        visual_segments: List[str] = []
        for seg in segments:
            if self._visual_richness_score(seg) >= 1:
                visual_segments.append(seg)

        # Deduplicate by content
        seen: set = set()
        result: List[str] = []
        for seg in visual_segments:
            key = seg[:80]
            if key not in seen:
                seen.add(key)
                result.append(seg)

        return result

    @staticmethod
    def _visual_richness_score(text: str) -> int:
        """
        Assign a score 0–5 based on how visually describable the text is.
        Higher = more likely to have findable visual assets.
        """
        score = 0
        lower = text.lower()

        # Year / era mention
        if _YEAR_RE.search(text):
            score += 2

        # People/character mentions
        if any(w in lower for w in ["tentara", "soldier", "orang", "person", "people", "manusia"]):
            score += 1

        # Location mentions
        if any(w in lower for w in ["pantai", "beach", "kota", "city", "gedung", "building",
                                     "jalan", "street", "kampung", "village"]):
            score += 1

        # Action / event
        if any(w in lower for w in ["mendarat", "landing", "perang", "war", "meledak",
                                     "berjalan", "berlari", "berbicara"]):
            score += 1

        # Named proper nouns (capitalized words likely proper nouns)
        proper_nouns = re.findall(r"\b[A-Z][a-z]+\b", text)
        if len(proper_nouns) >= 2:
            score += 1

        return score
