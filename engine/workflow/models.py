"""
engine/workflow/models.py
=========================
Core data structures and enums for Nugi Konten Kreator Workflow Orchestration Layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStatus(str, Enum):
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WorkflowTier(str, Enum):
    TIER_1 = "TIER_1"  # Core Editorial & Research
    TIER_2 = "TIER_2"  # Production Units (B-roll, Subtitles, CapCut Draft)
    TIER_3 = "TIER_3"  # Master End-to-End Orchestrations (Shorts, Full Video)


@dataclass
class WorkflowStep:
    """Represents a single executable or verifiable step within a workflow."""
    step_id: str
    name: str
    description: str
    tool_name: str
    required_inputs: List[str] = field(default_factory=list)
    optional_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    validation_rule: Optional[str] = None
    is_critical: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowDefinition:
    """Blueprint definition for a standardized Nugi content workflow."""
    workflow_id: str
    name: str
    description: str
    tier: WorkflowTier
    required_inputs: List[str]
    steps: List[WorkflowStep]
    optional_inputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    validation_steps: List[str] = field(default_factory=list)
    side_effects: str = "none"
    risk_level: RiskLevel = RiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "tier": self.tier.value,
            "required_inputs": self.required_inputs,
            "optional_inputs": self.optional_inputs,
            "dependencies": self.dependencies,
            "tools_used": self.tools_used,
            "validation_steps": self.validation_steps,
            "side_effects": self.side_effects,
            "risk_level": self.risk_level.value,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class StepExecutionResult:
    """Result of running or checking a single workflow step."""
    step_id: str
    name: str
    status: StepStatus
    output: Any = None
    files_created: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "status": self.status.value,
            "output": self.output,
            "files_created": self.files_created,
            "warnings": self.warnings,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }


@dataclass
class PreflightReport:
    """Report evaluating readiness of a workflow before execution."""
    workflow_id: str
    status: str  # "READY", "BLOCKED", "WARNING"
    ready_items: List[str] = field(default_factory=list)
    missing_items: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    available_assets: List[str] = field(default_factory=list)
    recommended_next_step: Optional[str] = None
    recommended_tool: Optional[str] = None
    next_workflow: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowRunState:
    """Serializable execution state of a workflow instance."""
    run_id: str
    workflow_id: str
    status: WorkflowStatus
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    next_action: Optional[Dict[str, Any]] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "context": self.context,
            "step_results": self.step_results,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "files_created": self.files_created,
            "next_action": self.next_action,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
