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
