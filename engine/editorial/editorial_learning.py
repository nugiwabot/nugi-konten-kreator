"""Post-production learning summaries from recorded QA artifacts."""
import json
from datetime import datetime, timezone
from pathlib import Path


def _read(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_editorial_learning_record(workspace_dir):
    ws = Path(workspace_dir).resolve()
    manifest = _read(ws / "manifest.json")
    qa = _read(ws / "final_qa.json")
    fact = _read(ws / "fact_check_report.json")
    dossier = _read(ws / "research_dossier.json")
    feedback = _read(ws / "editorial_feedback.json")
    feedback_valid = feedback.get("schema_version") == 1
    blockers = qa.get("hard_blockers", [])
    blockers = blockers if isinstance(blockers, list) else []
    rules = {
        "evidence": ("evidence", "fact check", "claim", "dossier"),
        "visual_media": ("b-roll", "media", "visual"),
        "script": ("script", "pacing", "duration"),
        "capcut": ("capcut", "timeline", "draft"),
        "manifest": ("manifest", "artifact", "subtitle"),
    }
    categories = []
    for category, terms in rules.items():
        if any(term in str(item).lower() for item in blockers for term in terms):
            categories.append(category)
    actions = {
        "evidence": "Tinjau sumber, klaim, dan hasil fact-check.",
        "visual_media": "Periksa relevansi media, sumber, dan hak penggunaannya.",
        "script": "Evaluasi naskah dan durasi melalui pembacaan nyata.",
        "capcut": "Periksa draft CapCut, path media, subtitle, dan timeline.",
        "manifest": "Periksa konsistensi manifest dan artefak produksi.",
    }
    recommendations = [{"category": key, "action": actions[key]} for key in categories]
    ratings = feedback.get("ratings", {}) if feedback_valid else {}
    if not isinstance(ratings, dict):
        ratings = {}
    ratings = {key: value for key, value in ratings.items()
               if key in ("hook", "clarity", "pacing", "evidence", "visuals", "brand_fit")
               and isinstance(value, (int, float)) and not isinstance(value, bool) and 1 <= value <= 5}
    for key, value in ratings.items():
        if value <= 2:
            recommendations.append({"category": key, "action": f"Perbaiki aspek {key.replace('_', ' ')} berdasarkan rating manusia {value}/5."})
    if not recommendations:
        recommendations.append({"category": "collect_feedback", "action": "Kumpulkan rating editor dan metrik audiens setelah publikasi."})
    audience_metrics = feedback.get("audience_metrics", {}) if feedback_valid else {}
    if not isinstance(audience_metrics, dict):
        audience_metrics = {}
    shots = _read(ws / "media_manifest.json").get("shots", [])
    media_counts = {}
    for shot in shots if isinstance(shots, list) else []:
        if isinstance(shot, dict):
            status = str(shot.get("status", "UNKNOWN")).upper()
            media_counts[status] = media_counts.get(status, 0) + 1
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": manifest.get("run_id", ""),
        "topic": manifest.get("topic", ""),
        "learning_status": "HUMAN_FEEDBACK_RECORDED" if feedback_valid else "WAITING_FOR_HUMAN_FEEDBACK",
        "qa_verdict": qa.get("verdict", "UNKNOWN"),
        "is_publishable": qa.get("is_publishable") is True,
        "quality_score": qa.get("overall_quality_score"),
        "media_coverage_pct": qa.get("media_coverage_pct"),
        "fact_check_verdict": fact.get("overall_verdict", "UNKNOWN"),
        "research_status": dossier.get("epistemic_status", "UNKNOWN"),
        "blocker_count": len(blockers),
        "blockers": [str(item) for item in blockers],
        "blocker_categories": categories,
        "media_status_counts": media_counts,
        "human_feedback_recorded": feedback_valid,
        "human_feedback": {
            "recorded": feedback_valid,
            "ratings": ratings,
            "audience_metrics": audience_metrics,
            "editor_notes": feedback.get("editor_notes", "") if feedback_valid else "",
            "audience_observations": feedback.get("audience_observations", "") if feedback_valid else "",
        },
        "recommended_next_actions": recommendations,
        "interpretation_limits": [
            "Automated QA measures artifact checks, not audience satisfaction or business impact.",
            "Audience performance is not inferred when explicit metrics are absent.",
            "This record does not automatically change editorial decisions or publication gates.",
        ],
    }


def update_editorial_learning_history(output_root, record):
    """Keep a local, run-keyed history for comparing future production runs."""
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "editorial_learning_history.json"
    old = _read(path)
    runs = old.get("runs", [])
    if not isinstance(runs, list):
        runs = []
    run_id = str(record.get("run_id", ""))
    runs = [item for item in runs if not isinstance(item, dict) or str(item.get("run_id", "")) != run_id]
    runs.append(record)
    runs.sort(key=lambda item: str(item.get("generated_at", "")) if isinstance(item, dict) else "")
    history = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "run_count": len(runs),
        "human_feedback_run_count": sum(1 for item in runs if isinstance(item, dict) and item.get("human_feedback_recorded") is True),
        "runs": runs,
        "interpretation": "Observational history only; does not automatically change editorial decisions.",
    }
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "run_count": len(runs)}
