"""
engine/production/production_manifest.py
========================================
Single source of truth for Autonomous Content Production State.
Location: engine/production/production_manifest.py

Maintains manifest.json across execution cycles to support:
  - Fully resumable workflows (skips completed, verified stages)
  - Idempotent execution (prevents duplicated downloads & mutations)
  - Transparent error recording & lineage tracking
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("production_manifest")


class ProductionStage(str, Enum):
    PLAN = "plan"
    QUALIFY = "qualify"
    RESEARCH = "research"
    STORY = "story"
    SCRIPT = "script"
    FACT_CHECK = "fact_check"
    VISUAL_PLAN = "visual_plan"
    MEDIA = "media"
    SUBTITLE = "subtitle"
    CAPCUT = "capcut"
    FINAL_QA = "final_qa"
    COMPLETE = "complete"


@dataclass
class ProductionManifest:
    """Production state manifest persisted as manifest.json in the workspace."""
    topic: str
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    format: str = "short"
    target_duration_seconds: float = 75.0
    status: str = "running"  # "running", "completed", "needs_review", "failed"
    current_stage: str = ProductionStage.PLAN.value
    completed_stages: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def mark_stage_completed(self, stage: str | ProductionStage, artifact_updates: Optional[Dict[str, str]] = None) -> None:
        st_val = stage.value if isinstance(stage, ProductionStage) else str(stage)
        if st_val not in self.completed_stages:
            self.completed_stages.append(st_val)
        if artifact_updates:
            self.artifacts.update(artifact_updates)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, stage: str | ProductionStage, error_message: str) -> None:
        st_val = stage.value if isinstance(stage, ProductionStage) else str(stage)
        self.status = "failed"
        self.current_stage = st_val
        self.errors.append(f"[{st_val}] {error_message}")
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def is_stage_done(self, stage: str | ProductionStage) -> bool:
        st_val = stage.value if isinstance(stage, ProductionStage) else str(stage)
        return st_val in self.completed_stages

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "run_id": self.run_id,
            "topic": self.topic,
            "format": self.format,
            "target_duration_seconds": self.target_duration_seconds,
            "status": self.status,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "artifacts": self.artifacts,
            "quality": self.quality,
            "content_quality": self.extra_fields.get("content_quality", self.quality),
            "errors": self.errors,
            "warnings": self.warnings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        d.update(self.extra_fields)
        return d

    def save(self, workspace_dir: Path | str) -> Path:
        ws = Path(workspace_dir).resolve()
        ws.mkdir(parents=True, exist_ok=True)
        manifest_p = ws / "manifest.json"
        manifest_p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest_p

    @classmethod
    def load(cls, manifest_file: Path | str) -> ProductionManifest:
        p = Path(manifest_file).resolve()
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            topic=data.get("topic", ""),
            run_id=data.get("run_id", f"run_{uuid.uuid4().hex[:12]}"),
            format=data.get("format", "short"),
            target_duration_seconds=float(data.get("target_duration_seconds", 75.0)),
            status=data.get("status", "running"),
            current_stage=data.get("current_stage", ProductionStage.PLAN.value),
            completed_stages=data.get("completed_stages", []),
            artifacts=data.get("artifacts", {}),
            quality=data.get("quality", {}),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )
