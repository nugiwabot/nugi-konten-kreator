import json

from engine.editorial.editorial_learning import (
    build_editorial_learning_record,
    update_editorial_learning_history,
)


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_learning_record_summarizes_observed_outcome_without_inventing_feedback(tmp_path):
    _write(tmp_path / "manifest.json", {"run_id": "run-1", "topic": "Housing costs", "format": "short"})
    _write(tmp_path / "final_qa.json", {
        "verdict": "BLOCKED",
        "is_publishable": False,
        "overall_quality_score": 54,
        "media_coverage_pct": 25,
        "hard_blockers": ["Missing real B-roll for required shot(s): shot_02", "Research dossier is UNVERIFIED"],
        "warnings": ["Low empirical evidence count"],
    })
    _write(tmp_path / "fact_check_report.json", {
        "overall_verdict": "UNVERIFIED",
        "narrative_integrity": {"gate_status": "BLOCKED"},
    })
    _write(tmp_path / "research_dossier.json", {"epistemic_status": "PARTIAL"})
    _write(tmp_path / "media_manifest.json", {
        "shots": [{"shot_id": "shot_01", "status": "REAL_DOWNLOADED"}, {"shot_id": "shot_02", "status": "MISSING"}],
    })

    record = build_editorial_learning_record(tmp_path, generated_at="2026-10-09T00:00:00+00:00")

    assert record["run_id"] == "run-1"
    assert record["learning_status"] == "WAITING_FOR_HUMAN_FEEDBACK"
    assert record["production_outcome"]["qa_verdict"] == "BLOCKED"
    assert record["production_outcome"]["blocker_categories"] == ["evidence", "visual_media"]
    assert record["production_outcome"]["media_status_counts"] == {"REAL_DOWNLOADED": 1, "MISSING": 1}
    assert record["human_feedback_recorded"] is False
    assert "audience_retention" not in record["production_outcome"]
    assert record["is_publishable"] if "is_publishable" in record else record["production_outcome"]["is_publishable"] is False


def test_explicit_editor_feedback_is_kept_separate_from_automated_qa(tmp_path):
    _write(tmp_path / "manifest.json", {"run_id": "run-2", "topic": "City transport"})
    _write(tmp_path / "final_qa.json", {"verdict": "NEEDS_REVIEW", "is_publishable": False, "hard_blockers": []})
    _write(tmp_path / "editorial_feedback.json", {
        "schema_version": 1,
        "ratings": {"hook": 2, "clarity": 4},
        "audience_metrics": {"average_view_duration_seconds": 31},
        "editor_notes": "Opening is too slow.",
    })

    record = build_editorial_learning_record(tmp_path)

    assert record["human_feedback_recorded"] is True
    assert record["human_feedback"]["ratings"] == {"hook": 2, "clarity": 4}
    assert record["human_feedback"]["audience_metrics"]["average_view_duration_seconds"] == 31
    assert any(item["category"] == "hook" for item in record["recommended_next_actions"])


def test_learning_history_upserts_by_run_id(tmp_path):
    record = {"run_id": "run-1", "generated_at": "2026-10-09T00:00:00+00:00", "human_feedback_recorded": False}
    first = update_editorial_learning_history(tmp_path, record)
    update_editorial_learning_history(tmp_path, {**record, "topic": "updated"})
    history = json.loads((tmp_path / "editorial_learning_history.json").read_text(encoding="utf-8"))

    assert first["run_count"] == 1
    assert history["run_count"] == 1
    assert history["runs"][0]["topic"] == "updated"
    assert history["human_feedback_run_count"] == 0
