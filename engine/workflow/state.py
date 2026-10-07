"""
engine/workflow/state.py
========================
Workflow State Persistence and Checkpoint Manager for Nugi Konten Kreator.
Persists run state into output/.workflow_runs/<run_id>.json.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from engine.workflow.models import WorkflowRunState, WorkflowStatus


class WorkflowStateManager:
    """Manages persistent workflow execution state and checkpoints."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.runs_dir = self.repo_root / "output" / ".workflow_runs"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> WorkflowRunState:
        """Create and persist a new workflow run state."""
        self._ensure_dir()
        now_iso = datetime.now(timezone.utc).isoformat()
        run_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        state = WorkflowRunState(
            run_id=run_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.PLANNED,
            current_step_index=0,
            context=context or {},
            step_results={},
            completed_steps=[],
            failed_steps=[],
            files_created=[],
            next_action=None,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self.save_run(state)
        return state

    def save_run(self, state: WorkflowRunState) -> None:
        """Atomically persist state to disk."""
        self._ensure_dir()
        state.updated_at = datetime.now(timezone.utc).isoformat()
        filepath = self.runs_dir / f"{state.run_id}.json"
        temp_filepath = self.runs_dir / f"{state.run_id}.tmp"
        temp_filepath.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        temp_filepath.replace(filepath)

    def get_run(self, run_id: str) -> Optional[WorkflowRunState]:
        """Load state of a run by run_id."""
        filepath = self.runs_dir / f"{run_id}.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return WorkflowRunState(
                run_id=data["run_id"],
                workflow_id=data["workflow_id"],
                status=WorkflowStatus(data.get("status", "planned")),
                current_step_index=data.get("current_step_index", 0),
                context=data.get("context", {}),
                step_results=data.get("step_results", {}),
                completed_steps=data.get("completed_steps", []),
                failed_steps=data.get("failed_steps", []),
                files_created=data.get("files_created", []),
                next_action=data.get("next_action"),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )
        except Exception:
            return None

    def list_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent workflow runs."""
        self._ensure_dir()
        runs: List[Dict[str, Any]] = []
        files = sorted(self.runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                runs.append({
                    "run_id": data.get("run_id"),
                    "workflow_id": data.get("workflow_id"),
                    "status": data.get("status"),
                    "completed_steps": len(data.get("completed_steps", [])),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                })
            except Exception:
                continue
        return runs
