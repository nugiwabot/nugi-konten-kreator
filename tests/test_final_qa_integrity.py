"""Final QA integration tests for narrative integrity and human review."""

import json

from engine.production.final_qa import FinalQAEngine


def _write_minimal_fact_check(workspace, integrity_status, *, editorial_status=None, schema=1):
    manifest = {
        "run_id": "run_stage10",
        "topic": "How cities change",
        "completed_stages": [
            "plan", "qualify", "research", "script", "fact_check",
            "visual_plan", "media", "subtitle", "capcut",
        ],
        "artifacts": {},
        "run_mode": "REAL_RUN",
    }
    (workspace / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    integrity = {
        "schema_version": schema,
        "gate_status": integrity_status,
        "publication_approval": False,
        "findings": [],
    }
    fact_report = {
        "production_run_id": "run_stage10",
        "topic": "How cities change",
        "overall_verdict": "VERIFIED",
        "pass_gate": True,
        "claims": [],
        "narrative_integrity": integrity,
        "editorial_gate": {
            "status": editorial_status or integrity_status,
            "publication_approval": False,
        },
    }
    (workspace / "fact_check_report.json").write_text(json.dumps(fact_report), encoding="utf-8")


def test_clean_automated_integrity_still_requires_human_editorial_review(tmp_path):
    _write_minimal_fact_check(tmp_path, "ELIGIBLE_FOR_EDITORIAL_REVIEW")

    report = FinalQAEngine().evaluate_production(tmp_path)
    payload = report.to_dict()

    assert report.editorial_review_required is True
    assert report.narrative_integrity_status == "ELIGIBLE_FOR_EDITORIAL_REVIEW"
    assert report.is_publishable is False
    assert report.verdict == "BLOCKED" or report.verdict == "NEEDS_REVIEW"
    assert any("human editorial review" in warning.lower() for warning in report.warnings)
    assert payload["editorial_review_required"] is True


def test_critical_narrative_integrity_block_is_enforced_by_final_qa(tmp_path):
    _write_minimal_fact_check(tmp_path, "BLOCKED")

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert report.narrative_integrity_status == "BLOCKED"
    assert any("Narrative integrity gate is BLOCKED" in item for item in report.hard_blockers)
    assert report.is_publishable is False


def test_fact_check_and_editorial_gate_must_agree(tmp_path):
    _write_minimal_fact_check(
        tmp_path,
        "ELIGIBLE_FOR_EDITORIAL_REVIEW",
        editorial_status="BLOCKED",
    )

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert any("does not match narrative_integrity gate_status" in item for item in report.hard_blockers)
    assert report.is_publishable is False


def test_unsupported_narrative_integrity_schema_blocks_final_qa(tmp_path):
    _write_minimal_fact_check(tmp_path, "ELIGIBLE_FOR_EDITORIAL_REVIEW", schema=99)

    report = FinalQAEngine().evaluate_production(tmp_path)

    assert any("schema_version=1" in item for item in report.hard_blockers)
    assert report.is_publishable is False
