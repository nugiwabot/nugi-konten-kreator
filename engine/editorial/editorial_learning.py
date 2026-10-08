"""Post-production learning summaries from recorded QA artifacts."""
import json
from datetime import datetime, timezone
from pathlib import Path


def build_editorial_learning_record(workspace_dir):
    ws = Path(workspace_dir).resolve()
    def read(name):
        try:
            value = json.loads((ws / name).read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
    manifest = read("manifest.json")
    qa = read("final_qa.json")
    fact = read("fact_check_report.json")
    dossier = read("research_dossier.json")
    blockers = qa.get("hard_blockers", [])
    blockers = blockers if isinstance(blockers, list) else []
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": manifest.get("run_id", ""),
        "topic": manifest.get("topic", ""),
        "learning_status": "HUMAN_FEEDBACK_RECORDED" if _read(ws / "editorial_feedback.json").get("schema_version") == 1 else "WAITING_FOR_HUMAN_FEEDBACK",
        "qa_verdict": qa.get("verdict", "UNKNOWN"),
        "is_publishable": qa.get("is_publishable") is True,
        "quality_score": qa.get("overall_quality_score"),
        "fact_check_verdict": fact.get("overall_verdict", "UNKNOWN"),
        "research_status": dossier.get("epistemic_status", "UNKNOWN"),
        "blocker_count": len(blockers),
        "blockers": [str(item) for item in blockers],
        "human_feedback_recorded": (ws / "editorial_feedback.json").is_file(),
        "note": "Automated QA is not audience performance or human publication approval.",
    }



def update_editorial_learning_history(output_root, record):
    """Keep a local, run-keyed history for comparing future production runs."""
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "editorial_learning_history.json"
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        old = {}
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
        "human_feedback_run_count": sum(
            1 for item in runs
            if isinstance(item, dict) and item.get("human_feedback_recorded") is True
        ),
        "runs": runs,
        "interpretation": "Observational history only; does not automatically change editorial decisions.",
    }
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path), "run_count": len(runs)}
