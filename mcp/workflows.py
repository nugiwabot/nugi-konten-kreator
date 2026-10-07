"""
mcp/workflows.py
================
MCP Workflow Orchestration Interface for Nugi Konten Kreator.
Bridges MCP tool calls to engine.workflow execution, preflight, and planning services.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from security import resolve_safe_path, SecurityError
from engine.workflow import (
    WorkflowExecutor,
    WorkflowPlanner,
    WorkflowPreflight,
    WorkflowRegistry,
    WorkflowStateManager,
    registry,
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """Singleton service managing MCP workflow interactions."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.registry = registry
        self.planner = WorkflowPlanner(self.registry)
        self.preflight = WorkflowPreflight(self.repo_root, self.registry)
        self.state_mgr = WorkflowStateManager(self.repo_root)
        self.executor = WorkflowExecutor(self.repo_root, self.registry, self.state_mgr)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows in the registry."""
        return [
            {
                "workflow_id": wf.workflow_id,
                "name": wf.name,
                "description": wf.description,
                "tier": wf.tier.value,
                "required_inputs": wf.required_inputs,
                "optional_inputs": wf.optional_inputs,
                "side_effects": wf.side_effects,
                "risk_level": wf.risk_level.value,
                "total_steps": len(wf.steps),
                "tools_used": wf.tools_used,
            }
            for wf in self.registry.list_all()
        ]

    def explain_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Explain the rationale, dependencies, tools, and steps of a specific workflow."""
        wf = self.registry.get(workflow_id)
        if not wf:
            return {
                "error": f"Workflow '{workflow_id}' not found.",
                "available_workflows": [w.workflow_id for w in self.registry.list_all()],
            }

        return {
            "workflow_id": wf.workflow_id,
            "name": wf.name,
            "description": wf.description,
            "tier": wf.tier.value,
            "required_inputs": wf.required_inputs,
            "optional_inputs": wf.optional_inputs,
            "dependencies": wf.dependencies,
            "tools_used": wf.tools_used,
            "validation_steps": wf.validation_steps,
            "side_effects": wf.side_effects,
            "risk_level": wf.risk_level.value,
            "steps": [
                {
                    "step_number": idx + 1,
                    "step_id": s.step_id,
                    "name": s.name,
                    "description": s.description,
                    "tool": s.tool_name,
                    "required_inputs": s.required_inputs,
                    "is_critical": s.is_critical,
                }
                for idx, s in enumerate(wf.steps)
            ],
            "why_each_step_exists": self._get_step_rationales(wf.workflow_id),
        }

    def plan_workflow(self, request: str) -> Dict[str, Any]:
        """Generate workflow plan from natural language intent."""
        return self.planner.plan(request)

    def preflight_workflow(self, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Evaluate preconditions and missing assets before execution."""
        clean_ctx = self._sanitize_context(context or {})
        rep = self.preflight.check(workflow_id, clean_ctx)
        return rep.to_dict()

    def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute a workflow with state tracking and preflight verification."""
        clean_ctx = self._sanitize_context(context or {})
        return self.executor.execute(workflow_id=workflow_id, context=clean_ctx, run_id=run_id, dry_run=dry_run)

    def workflow_status(self, run_id: str) -> Dict[str, Any]:
        """Get the execution state and checkpoint history of a run."""
        state = self.state_mgr.get_run(run_id)
        if not state:
            return {"error": f"Workflow run '{run_id}' not found."}
        return state.to_dict()

    def resume_workflow(self, run_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Resume execution of a halted or blocked workflow run."""
        state = self.state_mgr.get_run(run_id)
        if not state:
            return {"error": f"Workflow run '{run_id}' not found."}

        clean_ctx = self._sanitize_context(context or {})
        return self.executor.execute(workflow_id=state.workflow_id, context=clean_ctx, run_id=run_id)

    def _sanitize_context(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure file paths inside context remain safely confined within the repository."""
        sanitized = dict(ctx)
        for key in ["script_path", "raw_video_path", "srt_path", "output_path"]:
            if key in sanitized and isinstance(sanitized[key], str) and sanitized[key]:
                try:
                    safe_p = resolve_safe_path(self.repo_root, sanitized[key])
                    sanitized[key] = str(safe_p.relative_to(self.repo_root))
                except (SecurityError, PermissionError):
                    # Retain original value for validator to handle or fail gracefully
                    pass
        return sanitized

    def _get_step_rationales(self, workflow_id: str) -> Dict[str, str]:
        rationales: Dict[str, Dict[str, str]] = {
            "content_idea": {
                "editorial_classify": "Maps topic to proven audience interest anchors and domain taxonomy.",
                "human_place": "Ensures topic connects with where and how living humans inhabit physical spaces.",
                "property_brand_fit": "Guarantees Nugi Properti identity: Property is the lens, not always the sales object.",
                "story_type": "Selects emotional narrative arc (Hidden System, Contradiction, Origin, Reframe).",
                "why_angle": "Extracts systemic causal chain to prevent superficial trivia storytelling.",
                "recommendation": "Synthesizes qualifications into definitive GO / PIVOT editorial verdict.",
            },
            "fact_check": {
                "audit_engine": "Extracts empirical claims, verifies against evidence base, identifies overclaims, and checks property brand fit.",
            },
            "capcut_draft": {
                "workspace_preflight": "Verifies all media, subtitle, and script assets exist before assembly.",
                "footage_analysis": "Checks resolution, FPS, and audio streams to ensure high-quality render output.",
                "capcut_generate": "Constructs multi-track CapCut timeline draft_content.json.",
                "capcut_inspect": "Inspects JSON schema and tracks continuity.",
                "capcut_validate": "Verifies file linkage and asset integrity.",
            },
            "short_video": {
                "1_content_idea": "Guarantees strong hook and property lens before incurring production cost.",
                "2_research": "Provides empirical facts and citations for Layer B Evidence Cards.",
                "3_script": "Drafts spoken script calibrated to 160-185 words for natural 65-80s delivery.",
                "4_fact_audit": "Ensures no unverified claims or false causality slip into published video.",
                "5_editorial_audit": "Enforces zero hard selling and no promotional anti-patterns.",
                "6_script_validation": "Verifies natural speaking pace and section boundaries.",
                "7_visual_plan": "Creates dynamic shot list matching emotional beats with human relatability.",
                "8_broll": "Discovers authentic archival and context footage across Wikimedia, IA, and Pexafy.",
                "9_subtitle": "Produces synchronized word-for-word .srt subtitle tracks.",
                "10_capcut_draft": "Assembles ready-to-edit CapCut timeline draft.",
                "11_final_validation": "Ensures all project assets are complete and ready for voice-over recording.",
            },
        }
        return rationales.get(workflow_id, {})
