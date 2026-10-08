"""
engine/pipeline/media_ranker.py
================================
Semantic media ranking pipeline using existing EmbeddingProvider and
RerankerProvider from engine/providers/.

Ranking is multi-stage:
  1. Deduplicate candidates by download_url
  2. Compute embedding similarity (query emb vs metadata text emb)
  3. Reranker precision pass (original request vs metadata text)
  4. Combine scores → final_rank

If local embedding / reranker services are offline:
  - Gracefully fall back to keyword overlap scoring
  - Report which services were unavailable (fallback_reason)

IMPORTANT:
  - Semantic representation is TEXT-ONLY from metadata fields.
  - We do NOT claim to do visual (pixel-level) embedding.
  - Embedding cache prevents re-computing the same metadata string.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from engine.pipeline.visual_requirements import (
    analyze_human_relatability,
    REAL_REQUIRED,
    REAL_PREFERRED,
    GENERIC_ALLOWED,
    PRIMARY_EVIDENCE,
    DIRECT_CONTEXT,
    GENERIC_ATMOSPHERE,
    ARCHIVAL_REFERENCE,
    DOCUMENT,
    classify_visual_requirement,
    extract_entities,
)
from engine.providers.embedding import (
    EmbeddingProvider,
    FallbackEmbeddingProvider,
    LocalEmbeddingProvider,
    cosine_similarity,
)
from engine.providers.media import MediaItem
from engine.providers.capabilities import get_provider_capabilities
from engine.providers.reranker import (
    FallbackRerankerProvider,
    LocalRerankerProvider,
    RerankerProvider,
)

logger = logging.getLogger(__name__)


class MediaRanker:
    """
    Multi-stage semantic ranker for MediaItem candidates with Evidence-Based
    authenticity scoring and hard gating.

    Reuses existing EmbeddingProvider + RerankerProvider without modification.
    Maintains a simple in-memory embedding cache to avoid re-embedding the
    same metadata representation.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        reranker_provider: Optional[RerankerProvider] = None,
    ):
        self.embedder: EmbeddingProvider = embedding_provider or LocalEmbeddingProvider()
        self.reranker: RerankerProvider = reranker_provider or LocalRerankerProvider()
        self._embedding_cache: Dict[str, List[float]] = {}
        self._embedding_ok: Optional[bool] = None   # None = not yet checked
        self._reranker_ok: Optional[bool] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def rank(
        self,
        original_request: str,
        candidates: List[MediaItem],
        top_n: int = 10,
        entities: Optional[List[Dict[str, str]]] = None,
        visual_requirement: str = "auto",
        era: str = "auto",
        human_context: Optional[Dict[str, object]] = None,
    ) -> Tuple[List[MediaItem], str]:
        """
        Rank candidates against the original user request with evidence and authenticity scoring.

        Returns:
            (ranked_items, fallback_reason)
            - ranked_items: sorted by final_rank, highest relevance first
            - fallback_reason: empty string if full pipeline ran;
                               description of what was skipped otherwise.
        """
        if not candidates:
            return [], ""

        # Auto-infer visual requirement & entities if not provided
        if not visual_requirement or visual_requirement == "auto":
            inferred_vr, _, inferred_ents, _, _ = classify_visual_requirement(original_request)
            effective_vr = inferred_vr
            effective_entities = entities if entities is not None else inferred_ents
        else:
            effective_vr = visual_requirement
            effective_entities = entities if entities is not None else extract_entities(original_request)

        # Stage 1: Deduplicate
        candidates = self._deduplicate(candidates)
        logger.info(f"MediaRanker: {len(candidates)} candidates after dedup")

        # Stage 2: Embedding similarity
        candidates, emb_ok, emb_reason = self._apply_embedding(
            original_request, candidates
        )

        # Stage 3: Reranker
        candidates, rer_ok, rer_reason = self._apply_reranker(
            original_request, candidates
        )

        # Stage 4: Evidence & Authenticity Scoring (Sections 9, 10, 11)
        candidates = self._apply_authenticity_scoring(
            original_request=original_request,
            candidates=candidates,
            entities=effective_entities,
            visual_requirement=effective_vr,
            era=era,
            human_context=human_context,
        )

        # Stage 5: Combine scores into final_rank (Section 20)
        candidates = self._compute_final_rank(
            candidates, emb_ok, rer_ok, visual_requirement=effective_vr
        )

        # Stage 6: Hard Gate for REAL_REQUIRED (Section 10)
        if effective_vr == REAL_REQUIRED:
            valid_candidates = [c for c in candidates if not c.rejection_reason]
            if not valid_candidates:
                logger.warning(
                    f"MediaRanker: All {len(candidates)} candidates failed authenticity hard gate for REAL_REQUIRED"
                )
                return [], f"No authentic evidence found matching required entities for: {original_request}"
            candidates = valid_candidates
            for idx, c in enumerate(candidates, 1):
                c.final_rank = idx

        fallback_reason = ""
        if not emb_ok and not rer_ok:
            fallback_reason = (
                "Semantic ranking unavailable: local embedding and reranker services "
                "were not reachable. Keyword/metadata fallback ranking was used."
            )
        elif not emb_ok:
            fallback_reason = f"Embedding service unavailable ({emb_reason}). Reranker was used alone."
        elif not rer_ok:
            fallback_reason = f"Reranker service unavailable ({rer_reason}). Embedding similarity was used alone."

        return candidates[:top_n], fallback_reason

    def get_status(self) -> Dict[str, str]:
        """
        Quick health check — probe embedding + reranker services.
        Returns status dict compatible with `media doctor` command.
        """
        emb_status = self._probe_embedding()
        rer_status = self._probe_reranker()
        return {
            "embedding": "OK" if emb_status else "OFFLINE",
            "reranker": "OK" if rer_status else "OFFLINE",
        }

    # ------------------------------------------------------------------
    # Stage 1: Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(candidates: List[MediaItem]) -> List[MediaItem]:
        """Remove duplicate items by dedup_key (download_url or provider:id)."""
        seen: set = set()
        result: List[MediaItem] = []
        for item in candidates:
            key = item.dedup_key()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    # ------------------------------------------------------------------
    # Stage 2: Embedding similarity
    # ------------------------------------------------------------------

    def _apply_embedding(
        self,
        query: str,
        candidates: List[MediaItem],
    ) -> Tuple[List[MediaItem], bool, str]:
        """
        Compute cosine similarity between query embedding and each
        candidate's metadata text embedding.

        Returns: (updated_candidates, success_bool, error_reason_str)
        """
        try:
            # Embed the query
            query_emb = self._cached_embed(query)
            if not query_emb:
                return candidates, False, "empty embedding response"

            # Embed each candidate's text representation
            texts = [item.build_text_representation() for item in candidates]
            candidate_embs = self._get_embeddings_cached(texts)

            if not candidate_embs or len(candidate_embs) != len(candidates):
                return candidates, False, "candidate embedding count mismatch"

            for item, emb in zip(candidates, candidate_embs):
                sim = cosine_similarity(query_emb, emb)
                item.embedding_similarity = round(sim, 4)

            return candidates, True, ""

        except Exception as e:
            logger.warning(f"MediaRanker embedding stage failed: {e}")
            # Apply keyword-based fallback score to embedding field
            candidates = self._keyword_score_fallback(query, candidates)
            return candidates, False, str(e)

    def _cached_embed(self, text: str) -> List[float]:
        """Embed text with in-memory cache."""
        clean_text = text[:300]
        cache_key = clean_text
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        embeddings = self.embedder.get_embeddings([clean_text])
        emb = embeddings[0] if embeddings else []
        if emb:
            self._embedding_cache[cache_key] = emb
        return emb

    def _get_embeddings_cached(self, texts: List[str]) -> List[List[float]]:
        """Batch embed with cache."""
        to_embed_indices: List[int] = []
        to_embed_texts: List[str] = []
        results: List[List[float]] = [[] for _ in texts]

        for i, text in enumerate(texts):
            clean_text = text[:300]
            key = clean_text
            if key in self._embedding_cache:
                results[i] = self._embedding_cache[key]
            else:
                to_embed_indices.append(i)
                to_embed_texts.append(clean_text)

        if to_embed_texts:
            new_embs = self.embedder.get_embeddings(to_embed_texts)
            for idx, emb in zip(to_embed_indices, new_embs):
                key = texts[idx][:300]
                self._embedding_cache[key] = emb
                results[idx] = emb

        return results

    # ------------------------------------------------------------------
    # Stage 3: Reranker
    # ------------------------------------------------------------------

    def _apply_reranker(
        self,
        original_request: str,
        candidates: List[MediaItem],
    ) -> Tuple[List[MediaItem], bool, str]:
        """
        Run reranker with the ORIGINAL user request (not expanded keywords)
        against each candidate's text representation.

        Returns: (updated_candidates, success_bool, error_reason_str)
        """
        if not candidates:
            return candidates, True, ""

        try:
            texts = [item.build_text_representation()[:400] for item in candidates]
            rerank_results = self.reranker.rerank(
                query=original_request,
                documents=texts,
            )
            # Map reranker scores back to items
            score_map: Dict[int, float] = {
                r["index"]: float(r.get("relevance_score", 0.0))
                for r in rerank_results
            }
            for i, item in enumerate(candidates):
                item.reranker_score = round(score_map.get(i, 0.0), 4)

            return candidates, True, ""

        except Exception as e:
            logger.warning(f"MediaRanker reranker stage failed: {e}")
            # Reranker failed — reranker_score stays 0.0, handled in final rank
            return candidates, False, str(e)

    # ------------------------------------------------------------------
    # Stage 4: Evidence & Authenticity Scoring (Sections 9, 10, 11)
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_authenticity_scoring(
        original_request: str,
        candidates: List[MediaItem],
        entities: List[Dict[str, str]],
        visual_requirement: str,
        era: str = "auto",
        human_context: Optional[Dict[str, object]] = None,
    ) -> List[MediaItem]:
        """
        Evaluate authenticity, entity matching, and source specificity (Sections 9, 10, 11).
        """
        req_lower = original_request.lower()
        years_req = re.findall(r"\b(1[0-9]{3}|200[0-9]|201[0-9]|202[0-9])\b", original_request)

        normalized_entities: List[Dict[str, str]] = []
        if entities:
            for e in entities:
                if isinstance(e, dict):
                    normalized_entities.append(e)
                elif isinstance(e, str) and e.strip():
                    name_str = e.strip()
                    if re.match(r"^(1[0-9]{3}|200[0-9]|201[0-9]|202[0-9])$", name_str):
                        etype = "DATE"
                    elif any(ev in name_str.lower() for ev in ["d-day", "landing", "keynote", "war", "apollo"]):
                        etype = "EVENT"
                    else:
                        etype = "ENTITY"
                    normalized_entities.append({"name": name_str, "type": etype})

        entities = normalized_entities

        key_entities = [e for e in entities if e.get("type") in (
            "PERSON", "EVENT", "LANDMARK", "BUILDING", "PRODUCT", "DOCUMENT",
            "ORGANIZATION", "CITY", "PLACE", "COUNTRY", "ENTITY"
        )]

        generic_title_patterns = [
            "soldiers on beach", "soldier on beach", "businessman", "office worker",
            "city traffic", "people walking", "technology presentation", "military soldiers",
            "beach war", "busy corporate office", "young person apartment", "tired worker"
        ]

        relatability = human_context or analyze_human_relatability(original_request)

        for item in candidates:
            item.visual_requirement = visual_requirement
            text_pool = f"{item.title} {item.description} {item.creator} {item.date} {' '.join(str(v) for v in item.metadata.values())}".lower()
            title_lower = (item.title or "").lower()

            # 1. Entity Match Score
            matched_names: List[str] = []
            if key_entities:
                match_weights = []
                for ke in key_entities:
                    name_l = ke["name"].lower()
                    tokens = [t for t in re.findall(r"\b\w+\b", name_l) if len(t) > 2]
                    name_matched = False
                    if name_l in text_pool:
                        name_matched = True
                        weight = 1.0 if name_l in title_lower else 0.8
                    elif len(tokens) >= 2 and all(t in text_pool for t in tokens):
                        name_matched = True
                        weight = 0.9 if all(t in title_lower for t in tokens) else 0.7
                    elif len(tokens) == 1 and tokens[0] in text_pool:
                        name_matched = True
                        weight = 0.8 if tokens[0] in title_lower else 0.5
                    else:
                        weight = 0.0

                    if name_matched:
                        matched_names.append(ke["name"])
                    match_weights.append(weight)

                entity_match_score = sum(match_weights) / max(1, len(key_entities))
                if len(matched_names) == len(key_entities) and all(ke["name"].lower() in title_lower for ke in key_entities):
                    entity_match_score = max(entity_match_score, 0.95)
            else:
                entity_match_score = 0.5 if visual_requirement == REAL_REQUIRED else 1.0

            # 2. Temporal Match Score
            if years_req:
                target_year = years_req[0]
                if target_year in text_pool or target_year in (item.date or ""):
                    temporal_match_score = 1.0
                elif any(dec in text_pool for dec in [f"{target_year[:3]}0s", f"{target_year[:3]}0-an"]):
                    temporal_match_score = 0.85
                elif any(h in text_pool for h in ["historical", "archival", "vintage", "history", "sejarah"]):
                    temporal_match_score = 0.7
                else:
                    temporal_match_score = 0.2
            elif era in ("historical", "past"):
                if any(h in text_pool for h in ["historical", "archival", "vintage", "kuno", "sejarah", "19", "18"]):
                    temporal_match_score = 0.9
                else:
                    temporal_match_score = 0.4
            else:
                temporal_match_score = 0.85

            # 3. Location Match Score
            loc_entities = [e for e in entities if e.get("type") in ("PLACE", "CITY", "COUNTRY")]
            if loc_entities:
                loc_matched = sum(1 for le in loc_entities if le["name"].lower() in text_pool)
                location_match_score = loc_matched / max(1, len(loc_entities))
                if loc_matched > 0:
                    location_match_score = max(location_match_score, 0.9)
                else:
                    location_match_score = 0.2
            else:
                location_match_score = 1.0

            # 4. Event Match Score
            event_entities = [e for e in entities if e.get("type") == "EVENT"]
            if event_entities:
                event_matched = sum(1 for ee in event_entities if ee["name"].lower() in text_pool)
                if event_matched > 0:
                    event_match_score = 1.0
                else:
                    event_tokens = set()
                    for ee in event_entities:
                        event_tokens.update(ee["name"].lower().split())
                    matched_tokens = sum(1 for tok in event_tokens if len(tok) > 3 and tok in text_pool)
                    if matched_tokens > 0:
                        event_match_score = 0.85
                    else:
                        event_match_score = 0.2
            else:
                event_match_score = 1.0

            # 5. Source Specificity Score
            profile = get_provider_capabilities(item.provider)
            provider_role = str(profile.get("source_role", "")).lower()
            is_archive = any(cue in provider_role for cue in ("archive", "library"))
            is_official = any(cue in provider_role for cue in ("official", "government", "science"))
            is_stock = "stock" in provider_role
            is_open_catalog = "open_media" in provider_role
            is_generic = any(gp in title_lower for gp in generic_title_patterns)
            if is_generic and not matched_names:
                source_specificity_score = 0.15
                item.is_generic = True
            elif is_archive:
                source_specificity_score = 0.92 if matched_names else 0.78
                item.is_archival = True
            elif is_official:
                source_specificity_score = 0.82 if matched_names else 0.62
            elif is_open_catalog:
                source_specificity_score = 0.72 if matched_names else 0.45
            elif is_stock:
                source_specificity_score = 0.48 if matched_names else 0.30
            else:
                source_specificity_score = 0.62 if matched_names else 0.40

            # 6. Human Relatability Alignment
            # Scores whether the candidate metadata points toward the same human/lived-life
            # context as the shot. This is semantic metadata scoring, not pixel-level analysis.
            candidate_lower = text_pool
            need_terms = {
                "safety": ["safe", "safety", "security", "secure", "aman", "keamanan"],
                "shelter": ["home", "house", "shelter", "housing", "rumah", "hunian", "bedroom", "kamar"],
                "health": ["health", "sleep", "rest", "tired", "heat", "air quality", "noise", "wellbeing", "kesehatan", "tidur", "lelah", "istirahat", "panas", "bising"],
                "wealth": ["money", "salary", "cost", "price", "commute", "transport", "time", "rent", "mortgage", "uang", "gaji", "biaya", "harga", "transportasi", "waktu", "cicilan"],
                "belonging": ["family", "neighbor", "community", "together", "family", "keluarga", "tetangga", "komunitas", "bersama"],
                "status": ["luxury", "status", "prestige", "mewah", "gengsi", "prestise"],
                "autonomy": ["privacy", "control", "choice", "independent", "privasi", "kontrol", "pilihan"],
                "family": ["couple", "child", "parent", "family", "pasangan", "anak", "orang tua", "keluarga"],
                "meaning": ["identity", "memory", "homeplace", "identitas", "kenangan", "makna"],
                "curiosity": ["history", "origin", "why", "sejarah", "asal", "kenapa", "mengapa"]
            }
            requested_need = str(relatability.get("human_basic_need", "")).lower()
            requested_lens = str(relatability.get("life_lens", "")).lower()

            if requested_need in need_terms:
                human_basic_need_score = 1.0 if any(t in candidate_lower for t in need_terms[requested_need]) else 0.20
            else:
                human_basic_need_score = 0.30

            lens_terms = {
                "health": ["health", "sleep", "rest", "noise", "heat", "air", "kesehatan", "tidur", "istirahat", "bising", "panas", "udara"],
                "wealth": ["money", "salary", "cost", "price", "commute", "transport", "time", "rent", "mortgage", "uang", "gaji", "biaya", "harga", "transportasi", "waktu", "cicilan"],
                "relationship": ["family", "neighbor", "community", "couple", "child", "keluarga", "tetangga", "komunitas", "pasangan", "anak"]
            }
            if requested_lens in lens_terms:
                lens_score = 1.0 if any(t in candidate_lower for t in lens_terms[requested_lens]) else 0.25
            else:
                lens_score = 0.30

            human_scene_terms = ["person", "people", "family", "worker", "neighbor", "couple", "child", "man", "woman", "orang", "manusia", "keluarga", "pekerja", "tetangga", "pasangan", "anak"]
            place_scene_terms = ["home", "house", "apartment", "neighborhood", "street", "city", "room", "office", "park", "housing", "rumah", "apartemen", "lingkungan", "jalan", "kota", "kamar", "kantor", "taman", "hunian"]
            human_scene_score = 1.0 if any(t in candidate_lower for t in human_scene_terms) else 0.20
            place_scene_score = 1.0 if any(t in candidate_lower for t in place_scene_terms) else 0.20

            requested_everyday = bool(relatability.get("has_human_life_scene"))
            requested_place = bool(relatability.get("has_place_scene"))
            everyday_relevance_score = human_scene_score if requested_everyday else 0.40
            human_place_relevance_score = (0.5 * place_scene_score + 0.5 * human_scene_score) if requested_place and requested_everyday else (place_scene_score if requested_place else 0.40)

            human_alignment_score = round(
                0.35 * human_basic_need_score
                + 0.20 * lens_score
                + 0.25 * everyday_relevance_score
                + 0.20 * human_place_relevance_score,
                4,
            )

            item.human_basic_need_score = round(human_basic_need_score, 4)
            item.life_lens_score = round(lens_score, 4)
            item.everyday_relevance_score = round(everyday_relevance_score, 4)
            item.human_place_relevance_score = round(human_place_relevance_score, 4)
            item.human_alignment_score = human_alignment_score
            item.human_basic_need = requested_need
            item.life_lens = requested_lens

            # 7. Authenticity Score calculation (Section 9)
            if visual_requirement == REAL_REQUIRED:
                authenticity_score = (
                    0.40 * entity_match_score
                    + 0.20 * temporal_match_score
                    + 0.20 * event_match_score
                    + 0.10 * location_match_score
                    + 0.10 * source_specificity_score
                )
            elif visual_requirement == REAL_PREFERRED:
                authenticity_score = (
                    0.35 * entity_match_score
                    + 0.25 * location_match_score
                    + 0.20 * temporal_match_score
                    + 0.20 * source_specificity_score
                )
            else:
                authenticity_score = 0.50 * entity_match_score + 0.50 * source_specificity_score

            # Hard gate criteria check (Section 10)
            if visual_requirement == REAL_REQUIRED:
                if key_entities and entity_match_score < 0.35:
                    item.rejection_reason = "Failed authenticity hard gate: missing required entity match"
                elif authenticity_score < 0.35:
                    item.rejection_reason = "Failed authenticity hard gate: low authenticity score"
                elif is_generic and not matched_names:
                    item.rejection_reason = "Failed authenticity hard gate: generic stock candidate not acceptable for REAL_REQUIRED"

            # Assign scores and roles (Sections 12, 13)
            item.authenticity_score = round(authenticity_score, 4)
            item.entity_match_score = round(entity_match_score, 4)
            item.temporal_match_score = round(temporal_match_score, 4)
            item.location_match_score = round(location_match_score, 4)
            item.event_match_score = round(event_match_score, 4)
            item.source_specificity_score = round(source_specificity_score, 4)
            item.matched_entities = matched_names
            matched_events = [e["name"] for e in event_entities if e["name"].lower() in text_pool]
            matched_locations = [e["name"] for e in loc_entities if e["name"].lower() in text_pool]
            requested_times = [e["name"] for e in entities if e.get("type") in ("DATE", "YEAR", "HISTORICAL_PERIOD")]
            matched_times = [value for value in requested_times if value.lower() in text_pool]
            if not matched_times and years_req and years_req[0] in text_pool:
                matched_times.append(years_req[0])
            item.metadata["matched_event"] = ", ".join(matched_events)
            item.metadata["matched_location"] = ", ".join(matched_locations)
            item.metadata["matched_time"] = ", ".join(matched_times)

            if visual_requirement == REAL_REQUIRED:
                if any(e.get("type") == "DOCUMENT" for e in entities):
                    item.source_role = DOCUMENT
                elif authenticity_score >= 0.70:
                    item.source_role = PRIMARY_EVIDENCE
                else:
                    item.source_role = ARCHIVAL_REFERENCE
            elif visual_requirement == REAL_PREFERRED:
                item.source_role = DIRECT_CONTEXT
            else:
                item.source_role = GENERIC_ATMOSPHERE

        return candidates

    # ------------------------------------------------------------------
    # Stage 5: Final rank computation (Section 20)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_final_rank(
        candidates: List[MediaItem],
        emb_ok: bool,
        rer_ok: bool,
        visual_requirement: str = GENERIC_ALLOWED,
    ) -> List[MediaItem]:
        """
        Combine available scores into a sortable composite adhering to Section 20.
        """
        for item in candidates:
            if emb_ok and rer_ok:
                semantic_score = 0.4 * item.embedding_similarity + 0.6 * item.reranker_score
            elif emb_ok:
                semantic_score = item.embedding_similarity
            elif rer_ok:
                semantic_score = item.reranker_score
            else:
                semantic_score = item.keyword_score
            item.semantic_score = round(semantic_score, 4)
            item.contextual_score = round(
                0.35 * item.entity_match_score + 0.25 * item.event_match_score
                + 0.20 * item.location_match_score + 0.20 * item.temporal_match_score, 4
            )
            item.generic_penalty = 0.28 if item.is_generic and item.contextual_score < 0.65 else 0.0

            if visual_requirement == REAL_REQUIRED:
                # Authenticity, entity match, and temporal/event match dominate heavily (Section 20)
                composite = (
                    0.45 * item.authenticity_score
                    + 0.25 * item.entity_match_score
                    + 0.15 * semantic_score
                    + 0.15 * item.embedding_similarity
                )
            elif visual_requirement == REAL_PREFERRED:
                composite = (
                    0.25 * item.authenticity_score
                    + 0.15 * item.entity_match_score
                    + 0.25 * semantic_score
                    + 0.15 * item.embedding_similarity
                    + 0.20 * item.human_alignment_score
                )
            else:
                composite = (
                    0.85 * semantic_score
                    + 0.15 * item.human_alignment_score
                )

            composite = max(0.0, composite - item.generic_penalty)

            # Penalize rejected candidates to 0 so they never outrank authentic candidates
            if item.rejection_reason:
                composite = 0.0

            item.reranker_score = round(composite, 4)

        # Sort descending by composite score
        candidates.sort(key=lambda x: x.reranker_score, reverse=True)

        # Assign final_rank (1-indexed)
        for rank_idx, item in enumerate(candidates, 1):
            item.final_rank = rank_idx

        return candidates

    # ------------------------------------------------------------------
    # Keyword fallback (when embedding offline)
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_score_fallback(
        query: str, candidates: List[MediaItem]
    ) -> List[MediaItem]:
        """
        Assign embedding_similarity based on keyword overlap as a fallback.
        Uses title + description text vs query words.
        """
        import re
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        if not query_words:
            return candidates

        for item in candidates:
            combined = f"{item.title} {item.description} {item.creator} {item.date}".lower()
            doc_words = set(re.findall(r"\b\w+\b", combined))
            overlap = len(query_words & doc_words)
            score = overlap / max(1, len(query_words))
            item.embedding_similarity = round(score, 4)
            item.keyword_score = item.embedding_similarity

        return candidates

    # ------------------------------------------------------------------
    # Health probes
    # ------------------------------------------------------------------

    def _probe_embedding(self) -> bool:
        """Return True if embedding service responds."""
        try:
            embs = self.embedder.get_embeddings(["test"])
            # A non-empty embedding from LocalEmbeddingProvider means service is up
            # FallbackEmbeddingProvider also returns non-empty — distinguish by type
            from engine.providers.embedding import LocalEmbeddingProvider as LEP
            if isinstance(self.embedder, LEP):
                # If we get a 128-dim vector, it's the fallback (service offline)
                # If service is up, vector should match model dimension (usually >128)
                return bool(embs and len(embs[0]) > 128)
            return bool(embs and embs[0])
        except Exception:
            return False

    def _probe_reranker(self) -> bool:
        """Return True if reranker service responds."""
        try:
            from engine.providers.reranker import LocalRerankerProvider as LRP, FallbackRerankerProvider as FRP
            if isinstance(self.reranker, (FRP,)):
                return False
            results = self.reranker.rerank("test query", ["test document"], top_n=1)
            # FallbackRerankerProvider always returns results — check if it's a fallback
            if isinstance(self.reranker, LRP):
                # If reranker is LocalRerankerProvider and it fell back silently,
                # we can't easily distinguish here; assume OK if no exception
                return True
            return bool(results)
        except Exception:
            return False
