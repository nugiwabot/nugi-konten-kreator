"""Regression tests for the visual-plan and media-acquisition contract."""

from engine.pipeline.visual_requirements import (
    GENERIC_ALLOWED,
    VisualShotRequirement,
)
from engine.production.production_orchestrator import ProductionOrchestrator


def test_visual_shot_serializes_retrieval_constraints_and_truthful_unknown_status():
    shot = VisualShotRequirement(
        shot_id="shot_01",
        section_index=1,
        section_name="Bandung 2024",
        section_type="evidence",
        start_seconds=0,
        end_seconds=5,
        duration_seconds=5,
        visual_description="Street-level view of Bandung",
        search_query="Bandung housing street documentary",
        fallback_queries=["Bandung housing aerial", "Bandung housing street documentary"],
        preferred_media_type="video",
        visual_requirement=GENERIC_ALLOWED,
        visual_type="HUMAN_LIFE_IN_PLACE",
        entities=[{"type": "PLACE", "name": "Bandung"}],
        era="present",
        source_role="DIRECT_CONTEXT",
        search_required=True,
    )

    record = shot.to_dict()

    assert record["query"] == "Bandung housing street documentary"
    assert record["fallback_queries"] == ["Bandung housing aerial", "Bandung housing street documentary"]
    assert record["preferred_media_type"] == "video"
    assert record["visual_type"] == "HUMAN_LIFE_IN_PLACE"
    assert record["source_role"] == "DIRECT_CONTEXT"
    assert record["asset_availability"] == "NOT_CHECKED"
    assert record["rights_status"] == "NOT_CHECKED"
    assert record["visual_evidence_policy"] == "VISUALS_DO_NOT_SUBSTITUTE_FOR_CLAIM_EVIDENCE"
    assert record["start_frame"] == 0
    assert record["end_frame"] == 149


def test_visual_search_queries_use_topic_context_and_deduplicate_fallbacks():
    queries = ProductionOrchestrator._build_media_search_queries(
        {
            "query": "Bandung housing documentary",
            "fallback_queries": [
                "Bandung housing aerial",
                "Bandung housing documentary",
                "",
            ],
        },
        "Why housing prices change in Bandung",
    )

    assert len(queries) == 2
    assert all("Why housing prices change in Bandung" in query for query in queries)
    assert queries[0].startswith("Bandung housing documentary")
    assert queries[1].startswith("Bandung housing aerial")


def test_visual_search_queries_fall_back_to_topic_for_legacy_plan():
    queries = ProductionOrchestrator._build_media_search_queries({}, "How cities grow")

    assert queries == ["How cities grow"]


def test_no_broll_requirement_is_not_treated_as_missing_media():
    assert ProductionOrchestrator._shot_requires_media(
        {"search_required": False, "visual_requirement": "NO_BROLL"}
    ) is False
    assert ProductionOrchestrator._shot_requires_media(
        {"search_required": True, "visual_requirement": "REAL_REQUIRED"}
    ) is True
