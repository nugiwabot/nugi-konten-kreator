"""
engine/workflow/preflight.py
============================
Preflight Evaluator for Nugi Konten Kreator Workflows.
Evaluates asset readiness, dependencies, and prerequisites without side effects.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from engine.workflow.models import PreflightReport
from engine.workflow.registry import registry, WorkflowRegistry


class WorkflowPreflight:
    """Pre-execution validation engine for Nugi workflows."""

    def __init__(self, repo_root: Path, workflow_reg: Optional[WorkflowRegistry] = None) -> None:
        self.repo_root = repo_root.resolve()
        self.registry = workflow_reg or registry

    def check(self, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> PreflightReport:
        """
        Evaluate workflow readiness against context and repository assets.
        Mode: PREFLIGHT (Read-only, strictly non-destructive).
        """
        context = context or {}
        wf_def = self.registry.get(workflow_id)
        if not wf_def:
            return PreflightReport(
                workflow_id=workflow_id,
                status="BLOCKED",
                missing_items=[f"Unknown workflow_id: '{workflow_id}'"],
                recommended_next_step="Check available workflows using nugi_workflow_list()",
                recommended_tool="nugi_workflow_list",
            )

        ready_items: List[str] = []
        missing_items: List[str] = []
        warnings: List[str] = []
        available_assets: List[str] = []
        next_step: Optional[str] = None
        next_tool: Optional[str] = None
        next_workflow: Optional[str] = None

        # 1. Check required context inputs
        for req in wf_def.required_inputs:
            # Special aliases: script can be provided as script_text or script_path
            if req == "script" and ("script_text" in context or "script_path" in context):
                ready_items.append("Script content or path provided")
            elif req in context and context[req]:
                ready_items.append(f"Input '{req}' is provided")
            else:
                missing_items.append(f"Missing required input: '{req}'")

        # 2. Workspace asset checks (for production workflows)
        workspace = context.get("workspace")
        if workspace:
            ws_dir = self._resolve_workspace(workspace)
            if ws_dir and ws_dir.exists():
                ready_items.append(f"Workspace directory verified: {ws_dir.relative_to(self.repo_root)}")
                # Scan workspace assets
                footage_dir = ws_dir / "footage"
                broll_dir = ws_dir / "broll"
                subtitle_dir = ws_dir / "subtitle"
                project_dir = ws_dir / "project"

                # Check main footage
                if footage_dir.exists() and any(footage_dir.glob("*.mp4")):
                    vids = list(footage_dir.glob("*.mp4"))
                    available_assets.append(f"footage: {vids[0].name}")
                    ready_items.append("Main video footage available")
                else:
                    if workflow_id in ["capcut_draft"]:
                        missing_items.append("Main footage file (*.mp4) in footage/")
                        next_step = f"Place recorded voice-over or video into output/{workspace}/footage/"
                        next_tool = "nugi_output_create"

                # Check B-roll
                has_broll_files = broll_dir.exists() and any(broll_dir.glob("*.*"))
                has_broll_plan = (project_dir / "broll_plan.json").exists() or (project_dir / "broll_sources.json").exists()
                if has_broll_files or has_broll_plan:
                    ready_items.append("B-roll package or plan available")
                    available_assets.append("broll: assets/plan verified")
                else:
                    if workflow_id in ["capcut_draft"]:
                        warnings.append("No local B-roll files found; draft will assemble without overlay cut-ins.")
                        if not next_workflow:
                            next_workflow = "broll"

                # Check subtitles
                has_srt = subtitle_dir.exists() and any(subtitle_dir.glob("*.srt"))
                if has_srt:
                    ready_items.append("Synchronized SRT subtitles available")
                    available_assets.append("subtitle: .srt verified")
                else:
                    if workflow_id in ["capcut_draft"]:
                        warnings.append("No .srt subtitle found; CapCut draft will be generated without subtitle track.")
                        if not next_workflow:
                            next_workflow = "subtitle"

                # Check script file
                scripts = list(ws_dir.glob("*.md"))
                if scripts:
                    ready_items.append(f"Script file available: {scripts[0].name}")
                    available_assets.append(f"script: {scripts[0].name}")
            else:
                if workflow_id in ["capcut_draft"]:
                    missing_items.append(f"Workspace folder '{workspace}' not found in output/ or output/short video/")
                    next_step = f"Create workspace output/{workspace} with footage/ and subtitle/ subfolders."
                    next_tool = "nugi_output_mkdir"
                else:
                    ready_items.append(f"Workspace folder '{workspace}' will be created upon output.")

        # 3. Script path check
        script_path = context.get("script_path")
        if script_path:
            sp = (self.repo_root / script_path).resolve()
            if sp.is_file():
                ready_items.append(f"Script file exists: {script_path}")
                available_assets.append(f"script_path: {script_path}")
            else:
                missing_items.append(f"Script file not found at: '{script_path}'")
                next_step = f"Verify script file path '{script_path}'"

        # 4. Determine overall status and next recommendations
        if missing_items:
            status = "BLOCKED"
            if not next_step:
                next_step = f"Provide missing inputs: {', '.join(missing_items)}"
            if not next_tool:
                next_tool = wf_def.tools_used[0] if wf_def.tools_used else "nugi_workflow_execute"
        elif warnings:
            status = "WARNING"
            if not next_step:
                next_step = f"Prerequisites met with warnings. Ready to execute."
            if not next_tool:
                next_tool = "nugi_workflow_execute"
        else:
            status = "READY"
            next_step = f"All prerequisites verified. Ready to execute '{workflow_id}' workflow."
            next_tool = "nugi_workflow_execute"

        return PreflightReport(
            workflow_id=workflow_id,
            status=status,
            ready_items=ready_items,
            missing_items=missing_items,
            warnings=warnings,
            available_assets=available_assets,
            recommended_next_step=next_step,
            recommended_tool=next_tool,
            next_workflow=next_workflow,
        )

    def _resolve_workspace(self, workspace: str) -> Optional[Path]:
        from engine.pipeline.auto_edit_capcut import find_workspace
        return find_workspace(workspace)
