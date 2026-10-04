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
from typing import Any, Dict, List, Optional

from engine.pipeline.visual_requirements import (
    REAL_REQUIRED,
    REAL_PREFERRED,
    GENERIC_ALLOWED,
    NO_BROLL,
    REMOTION_REQUIRED,
    PRIMARY_EVIDENCE,
    DIRECT_CONTEXT,
    GENERIC_ATMOSPHERE,
    ARCHIVAL_REFERENCE,
    DOCUMENT,
    MOTION_GRAPHICS,
    NO_VISUAL,
    classify_visual_requirement,
    extract_entities,
)

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
    "pasukan sekutu": "allied forces",
    "sekutu": "allied",
    "pendaratan normandia": "normandy landings",
    "normandia": "normandy",
    "memperkenalkan": "introduction keynote",
    "abad ke-20": "20th century",
    "awal abad": "early century",
    "zaman prasejarah": "prehistoric era",
    "prasejarah": "prehistoric",
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

    # Evidence-Based Visual Retrieval fields (Sections 4, 12, 17)
    visual_requirement: str = GENERIC_ALLOWED
    visual_type: str = "METAPHOR"
    entities: List[Dict[str, str]] = field(default_factory=list)
    motion_spec: Optional[Dict[str, Any]] = None
    source_role: str = GENERIC_ATMOSPHERE

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
        media_type_override: Optional[str] = None,
        visual_requirement_override: Optional[str] = None,
        visual_requirement: Optional[str] = None,
    ) -> ExpandedQuery:
        """
        Main entry point.

        Args:
            user_request: Raw natural-language string from user.
            media_type_override: Force media_type if already known externally.
            visual_requirement_override: Force visual_requirement if given.
            visual_requirement: Alias for visual_requirement_override.

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

        # 1. Classify visual requirement (Section 4)
        effective_vr = visual_requirement or visual_requirement_override
        v_req, v_type, entities, motion_spec, s_role = classify_visual_requirement(text)
        if effective_vr and effective_vr != "auto":
            v_req = effective_vr
            if v_req == REAL_REQUIRED and s_role == GENERIC_ATMOSPHERE:
                s_role = PRIMARY_EVIDENCE
            elif v_req == REAL_PREFERRED and s_role == GENERIC_ATMOSPHERE:
                s_role = DIRECT_CONTEXT

        # If NO_BROLL or REMOTION_REQUIRED, do NOT generate media search queries (Sections 16, 18, 19)
        if v_req in (NO_BROLL, REMOTION_REQUIRED):
            return ExpandedQuery(
                original_request=user_request,
                detected_media_type="any",
                primary_queries=[],
                expanded_queries=[],
                is_historical=False,
                year_hint=None,
                visual_requirement=v_req,
                visual_type=v_type,
                entities=entities,
                motion_spec=motion_spec,
                source_role=s_role,
            )

        # 2. Detect and normalize media type
        if media_type_override:
            m_override = media_type_override.lower().strip()
            if m_override in ("video", "footage", "film", "rekaman"):
                media_type = "video"
            elif m_override in ("image", "photo", "foto", "gambar"):
                media_type = "image"
            elif m_override in ("any", "all", "semua"):
                media_type = "any"
            else:
                media_type = m_override
        else:
            media_type = self._detect_media_type(text)

        # 3. Detect historical context
        is_historical, year_hint = self._detect_historical(text)
        if v_req == REAL_REQUIRED:
            # If historical entities or dates are present, ensure is_historical is True
            if any(e["type"] in ("HISTORICAL_PERIOD", "DATE") for e in entities):
                is_historical = True

        # 4. Extract core concept (strip action words and media type words)
        core_concept = self._extract_core_concept(text)

        # 5. Build queries with Entity Preservation Rule (Sections 6, 7, 14, 15)
        if v_req == REAL_REQUIRED and entities:
            primary_queries, expanded_queries = self._build_entity_queries(
                entities=entities,
                raw_text=text,
                media_type=media_type,
                is_historical=is_historical,
                visual_requirement=v_req,
            )
        elif v_req == REAL_PREFERRED and entities:
            primary_queries, expanded_queries = self._build_entity_queries(
                entities=entities,
                raw_text=text,
                media_type=media_type,
                is_historical=is_historical,
                visual_requirement=v_req,
            )
        else:
            primary_queries = self._build_primary_queries(
                core_concept, year_hint, is_historical, media_type=media_type
            )
            expanded_queries = self._build_expanded_queries(
                core_concept, year_hint, is_historical, media_type
            )

        # For relatable present-day scenes, explicitly prefer real people and real places.
        # This supplements semantic search and prevents drift into abstract concept art.
        if v_req == REAL_PREFERRED and v_type in ("HUMAN_LIFE", "HUMAN_LIFE_IN_PLACE"):
            human_query = f"{core_concept} real people real place documentary"
            place_query = f"{core_concept} everyday life home neighborhood documentary"
            primary_queries = self._dedup([human_query] + primary_queries)
            expanded_queries = self._dedup([place_query] + expanded_queries)

        return ExpandedQuery(
            original_request=user_request,
            detected_media_type=media_type,
            primary_queries=primary_queries,
            expanded_queries=expanded_queries,
            is_historical=is_historical,
            year_hint=year_hint,
            visual_requirement=v_req,
            visual_type=v_type,
            entities=entities,
            motion_spec=motion_spec,
            source_role=s_role,
        )

    def _build_entity_queries(
        self,
        entities: List[Dict[str, str]],
        raw_text: str,
        media_type: str,
        is_historical: bool,
        visual_requirement: str,
    ) -> Tuple[List[str], List[str]]:
        """
        Build entity-preserved queries adhering to Sections 6, 7, 14, 15:
        [EXACT ENTITY] + [EVENT / OBJECT / ACTION] + [DATE / ERA] + [LOCATION] + [ARCHIVAL qualifier]
        Never drop proper nouns or aggressively broaden.
        Completely content-agnostic without hardcoded subjects.
        """
        lower = raw_text.lower()
        ent_names = [e["name"] for e in entities]
        ent_by_type: Dict[str, List[str]] = {}
        for e in entities:
            ent_by_type.setdefault(e["type"], []).append(e["name"])

        primary: List[str] = []
        expanded: List[str] = []

        # General entity composition (Content-Agnostic)
        core_ents = " ".join(ent_names)
        if not core_ents:
            core_ents = self._extract_core_concept(raw_text)

        date_hint = " ".join(ent_by_type.get("DATE", []))
        loc_hint = " ".join(ent_by_type.get("PLACE", []) + ent_by_type.get("CITY", []) + ent_by_type.get("COUNTRY", []))
        event_hint = " ".join(ent_by_type.get("EVENT", []))
        person_hint = " ".join(ent_by_type.get("PERSON", []))
        prod_hint = " ".join(ent_by_type.get("PRODUCT", []))

        # Detect action keywords in text (e.g. keynote, introduction, landing, proklamasi, dll)
        actions = []
        for kw in ["keynote", "introduction", "memperkenalkan", "landing", "pendaratan", "meeting", "speech", "interview", "announcement"]:
            if kw in lower:
                action_word = "keynote" if kw in ("keynote", "memperkenalkan") else ("landing" if kw in ("landing", "pendaratan") else kw)
                if action_word not in actions:
                    actions.append(action_word)
        action_hint = " ".join(actions)

        # Primary queries combining entity with context
        if media_type == "video":
            if is_historical:
                primary.append(f"{core_ents} archival footage".strip())
                if action_hint:
                    primary.append(f"{core_ents} {action_hint}".strip())
                primary.append(f"{core_ents} historical footage".strip())
                primary.append(f"{core_ents} original recording".strip())
                primary.append(f"{core_ents} original footage".strip())
            else:
                primary.append(f"{core_ents} footage".strip())
                if action_hint:
                    primary.append(f"{core_ents} {action_hint}".strip())
                primary.append(f"{core_ents} documentary footage".strip())
        elif media_type in ("image", "photo"):
            if is_historical:
                primary.append(f"{core_ents} historical photograph".strip())
                primary.append(f"{core_ents} archival photo".strip())
                if action_hint:
                    primary.append(f"{core_ents} {action_hint}".strip())
                primary.append(f"{core_ents} archive".strip())
            else:
                primary.append(f"{core_ents} photograph".strip())
                primary.append(f"{core_ents} photo".strip())
        else:
            if is_historical:
                primary.append(f"{core_ents} archival".strip())
                if action_hint:
                    primary.append(f"{core_ents} {action_hint}".strip())
                primary.append(f"{core_ents} historical document".strip())
            else:
                primary.append(core_ents.strip())

        # If person and product, also add targeted entity pair query
        if person_hint and prod_hint:
            if date_hint:
                primary.insert(0, f"{person_hint} {prod_hint} {date_hint} {action_hint or 'keynote'}".strip())
                primary.insert(1, f"{person_hint} {prod_hint} {date_hint}".strip())
            else:
                primary.insert(0, f"{person_hint} {prod_hint} {action_hint}".strip())

        # If event and location, add targeted event-location query
        if event_hint and loc_hint:
            if date_hint:
                primary.insert(0, f"{event_hint} {loc_hint} {date_hint}".strip())
            else:
                primary.insert(0, f"{event_hint} {loc_hint}".strip())

        # Expanded queries strictly retaining main entity
        main_entity = ent_names[0] if ent_names else core_ents
        if is_historical:
            expanded.append(f"{main_entity} archival")
            expanded.append(f"{main_entity} historical")
            if loc_hint and loc_hint not in main_entity:
                expanded.append(f"{main_entity} {loc_hint}".strip())
            if date_hint and date_hint not in main_entity:
                expanded.append(f"{main_entity} {date_hint}".strip())
            if action_hint:
                expanded.append(f"{main_entity} {action_hint}".strip())
            if media_type == "video":
                expanded.append(f"{main_entity} newsreel")
                expanded.append(f"{main_entity} documentary film")
            else:
                expanded.append(f"{main_entity} vintage photograph")
        else:
            expanded.append(f"{main_entity} documentary")
            if loc_hint and loc_hint not in main_entity:
                expanded.append(f"{main_entity} {loc_hint}".strip())
            if action_hint:
                expanded.append(f"{main_entity} {action_hint}".strip())

        return self._dedup(primary), self._dedup(expanded)

        # General entity composition
        core_ents = " ".join(ent_names)
        if not core_ents:
            core_ents = self._extract_core_concept(raw_text)

        date_hint = " ".join(ent_by_type.get("DATE", []))
        loc_hint = " ".join(ent_by_type.get("PLACE", []) + ent_by_type.get("CITY", []) + ent_by_type.get("COUNTRY", []))

        # Primary queries combining entity with context
        if media_type == "video":
            if is_historical:
                primary.append(f"{core_ents} archival footage")
                primary.append(f"{core_ents} historical footage")
                primary.append(f"{core_ents} original recording")
            else:
                primary.append(f"{core_ents} footage")
                primary.append(f"{core_ents} documentary footage")
        elif media_type in ("image", "photo"):
            if is_historical:
                primary.append(f"{core_ents} historical photograph")
                primary.append(f"{core_ents} archival photo")
                primary.append(f"{core_ents} archive")
            else:
                primary.append(f"{core_ents} photograph")
                primary.append(f"{core_ents} photo")
        else:
            if is_historical:
                primary.append(f"{core_ents} archival")
                primary.append(f"{core_ents} historical document")
            else:
                primary.append(core_ents)

        # Expanded queries strictly retaining main entity
        main_entity = ent_names[0] if ent_names else core_ents
        if is_historical:
            expanded.append(f"{main_entity} archival")
            expanded.append(f"{main_entity} historical")
            if loc_hint and loc_hint not in main_entity:
                expanded.append(f"{main_entity} {loc_hint}")
            if date_hint and date_hint not in main_entity:
                expanded.append(f"{main_entity} {date_hint}")
            if media_type == "video":
                expanded.append(f"{main_entity} newsreel")
                expanded.append(f"{main_entity} documentary film")
            else:
                expanded.append(f"{main_entity} vintage photograph")
        else:
            expanded.append(f"{main_entity} documentary")
            if loc_hint and loc_hint not in main_entity:
                expanded.append(f"{main_entity} {loc_hint}")

        return self._dedup(primary), self._dedup(expanded)

    def expand_script(
        self,
        script_text: str,
        folder_hint: Optional[str] = None
    ) -> List[ExpandedQuery]:
        """
        Script-to-visual mode: extract visual scenes from a long script
        and generate an ExpandedQuery per scene.

        Sections 4 & 16:
        Only scenes classified as REAL_REQUIRED, REAL_PREFERRED, or GENERIC_ALLOWED
        are retained for media provider search. NO_BROLL and REMOTION_REQUIRED are skipped.
        """
        scenes = self._extract_script_scenes(script_text)
        results: List[ExpandedQuery] = []
        for scene_text in scenes:
            eq = self.expand(scene_text)
            eq.is_script_mode = True
            if eq.visual_requirement in (NO_BROLL, REMOTION_REQUIRED):
                continue
            if eq.all_queries:
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
        media_type: str = "any",
    ) -> List[str]:
        """Build 1–3 most specific queries."""
        queries: List[str] = []

        # Most specific: concept + year if available
        if year_hint and year_hint not in core_concept:
            if media_type == "video":
                queries.append(f"{core_concept} {year_hint} footage")
            else:
                queries.append(f"{core_concept} {year_hint}")

        # Concept itself
        queries.append(core_concept)

        # Media and historical qualifier
        if media_type == "video":
            if is_historical:
                queries.append(f"{core_concept} archival footage")
                queries.append(f"{core_concept} historical footage")
            else:
                queries.append(f"{core_concept} footage")
                queries.append(f"{core_concept} film footage")
        else:
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

        # Media type qualifier & archival variants
        if media_type == "video":
            if is_historical:
                queries.append(f"{core_concept} historical footage")
                queries.append(f"{core_concept} archival footage")
                queries.append(f"{core_concept} wartime footage")
                queries.append(f"{core_concept} newsreel")
                queries.append(f"{core_concept} film footage")
                queries.append(f"{core_concept} documentary footage")
                if year_hint:
                    queries.append(f"{core_concept} {year_hint} archival")
            else:
                queries.append(f"{core_concept} footage")
                queries.append(f"{core_concept} archival footage")
                queries.append(f"{core_concept} newsreel")
                queries.append(f"{core_concept} film footage")
        elif media_type in ("image", "photo"):
            queries.append(f"{core_concept} photograph")
            if is_historical:
                queries.append(f"{core_concept} archival photograph")
                queries.append(f"{core_concept} archive")
                queries.append(f"{core_concept} documentary")
                if year_hint:
                    queries.append(f"{core_concept} {year_hint} archival")
        else:
            # any
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
