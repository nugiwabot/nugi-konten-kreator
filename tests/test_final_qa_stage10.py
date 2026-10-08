"""Stage 10 regression tests for production integration and final editorial gates."""

import json

from engine.production.final_qa import FinalQAEngine


def _write_base_workspace(tmp_path, integrity_status="BLOCKED", include_integrity=True):
    story_plan_path = tmp_path / "story_plan.json"
    story_plan_path.write_text(
        json.dumps({
            "schema_version": 1,
            "topic": "Why cities change",
            "beats": [{"beat_id": "beat_01", "narration_seed": "A city changes over time."}],
        }),
        encoding="utf-8",
    )
    manifest = {
        "run_id": "run_stage10",
        "topic": "Why cities change",
        "completed_stages": ["plan", "qualify", "research", "script", "fact_check", "visual_plan", "media", "subtitle", "capcut"],
        "artifacts": {"story_plan": str(story_plan_path.resolve())},
        "run_mode": "DRY_RUN",
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    fact_report = {
        "production_run_id": "run_stage10",
        "topic": "Why cities change",
        "overall_verdict": "VERIFIED",
        "pass_gate": True,
        "claims": [],
    }
    if include_integrity:
        fact_report["narrative_integrity"] = {
            "schema_version": 1,
            "gate_status": integrity_status,
            "publication_approval": False,
            "findings": [],
        }
    (tmp_path / "fact_check_report.json").write_text(json.dumps(fact_report), encoding="utf-8")
    return story_plan_path


def test_final_qa_blocks_even_verified_fact_report_when_integrity_is_blocked(tmp_path):
    _write_base_workspace(tmp_path, integrity_status="BLOCKED")

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert report.verdict == "BLOCKED"
    assert "Narrative integrity gate is BLOCKED" in report.hard_blockers
    assert report.is_publishable is False


def test_final_qa_blocks_legacy_fact_report_without_integrity_schema(tmp_path):
    _write_base_workspace(tmp_path, include_integrity=False)

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert any("lacks a valid narrative-integrity report" in item for item in report.hard_blockers)
    assert report.is_publishable is False


def test_final_qa_requires_story_plan_manifest_path_and_matching_topic(tmp_path):
    story_plan_path = _write_base_workspace(tmp_path, integrity_status="ELIGIBLE_FOR_EDITORIAL_REVIEW")
    story_plan = json.loads(story_plan_path.read_text(encoding="utf-8"))
    story_plan["topic"] = "Different topic"
    story_plan_path.write_text(json.dumps(story_plan), encoding="utf-8")

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert "story_plan.json topic does not match manifest.json" in report.hard_blockers
    assert report.is_publishable is False


def test_final_qa_does_not_treat_false_publication_approval_as_a_gate_failure(tmp_path):
    _write_base_workspace(tmp_path, integrity_status="ELIGIBLE_FOR_EDITORIAL_REVIEW")

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert not any("Narrative integrity gate" in item for item in report.hard_blockers)
    assert report.is_publishable is False  # Other required production artifacts are intentionally absent.
