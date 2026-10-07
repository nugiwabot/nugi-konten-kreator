"""
engine/workflow/planner.py
==========================
Workflow Planner for Nugi Konten Kreator.
Translates natural language user intents into structured workflow blueprints.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from engine.workflow.models import WorkflowDefinition
from engine.workflow.registry import registry, WorkflowRegistry


class WorkflowPlanner:
    """Intelligent intent resolver and step planner."""

    def __init__(self, workflow_reg: Optional[WorkflowRegistry] = None) -> None:
        self.registry = workflow_reg or registry

    def plan(self, request: str) -> Dict[str, Any]:
        """
        Analyze user intent, select the most appropriate workflow, and generate a step-by-step plan.
        Mode: PLAN (Read-only, no side effects).
        """
        req_lower = request.lower()

        # 1. Intent Detection Heuristics
        workflow_id = self._detect_workflow_id(req_lower)
        wf_def = self.registry.get(workflow_id)
        if not wf_def:
            wf_def = self.registry.get("short_video")  # default master workflow
            workflow_id = "short_video"

        # 2. Extract potential inputs from natural language
        extracted_inputs = self._extract_inputs(request)

        # 3. Compute missing inputs
        missing = [inp for inp in wf_def.required_inputs if inp not in extracted_inputs]

        # 4. Build planned step sequence
        steps_plan = [
            {
                "step_number": idx + 1,
                "step_id": step.step_id,
                "name": step.name,
                "description": step.description,
                "tool_to_use": step.tool_name,
                "is_critical": step.is_critical,
                "required_inputs": step.required_inputs,
            }
            for idx, step in enumerate(wf_def.steps)
        ]

        return {
            "mode": "PLAN",
            "status": "planned",
            "user_request": request,
            "detected_workflow_id": workflow_id,
            "workflow_name": wf_def.name,
            "description": wf_def.description,
            "tier": wf_def.tier.value,
            "side_effects": wf_def.side_effects,
            "risk_level": wf_def.risk_level.value,
            "extracted_inputs": extracted_inputs,
            "missing_inputs": missing,
            "ready_to_preflight": len(missing) == 0,
            "total_steps": len(steps_plan),
            "planned_steps": steps_plan,
            "recommended_next_action": (
                f"Run nugi_workflow_preflight(workflow_id='{workflow_id}', context={extracted_inputs}) to verify assets."
                if len(missing) == 0
                else f"Provide missing inputs: {missing} before executing."
            ),
        }

    def _detect_workflow_id(self, req: str) -> str:
        # Priority mapping from specific to broad
        if any(k in req for k in ["fact check", "cek fakta", "verifikasi klaim", "audit fakta", "overclaim", "script auditor"]):
            return "fact_check"
        elif any(k in req for k in ["content audit", "audit naskah", "audit script", "evaluasi naskah", "review konten", "audit lengkap"]):
            return "content_audit"
        elif any(k in req for k in ["capcut", "draft capcut", "timeline capcut", "edit capcut", "project capcut"]):
            return "capcut_draft"
        elif any(k in req for k in ["b-roll", "broll", "footage", "cari video", "cari gambar", "media retrieval"]):
            return "broll"
        elif any(k in req for k in ["subtitle", "srt", "teks suara", "generate srt"]):
            return "subtitle"
        elif any(k in req for k in ["longform", "documentary", "dokumenter", "video panjang", "full video"]):
            return "full_video"
        elif any(k in req for k in ["short", "shorts", "video pendek", "tiktok", "reels"]):
            return "short_video"
        elif any(k in req for k in ["bikin script", "buat script", "tulis script", "buat naskah", "tulis naskah", "script only"]):
            return "script_only"
        elif any(k in req for k in ["riset", "research", "cari bukti", "cari data", "studi topik"]):
            return "research_only"
        elif any(k in req for k in ["ide konten", "ide topik", "topik baru", "angle", "human place", "cek topik", "brainstorming"]):
            return "content_idea"
        elif any(k in req for k in ["script", "naskah"]):
            return "script_only"
        
        # Default for general video requests
        return "short_video"

    def _extract_inputs(self, text: str) -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}

        # Extract workspace: e.g. "01-script", "workspace 02", "short-01"
        ws_match = re.search(r"\b(\d{1,2}-script|short[-_]?\d{1,2})\b", text, re.IGNORECASE)
        if ws_match:
            inputs["workspace"] = ws_match.group(1)

        # Extract file paths: e.g. path ending with .md or .srt
        file_match = re.search(r"([\w/\\.-]+\.(?:md|srt|json|mp4))", text, re.IGNORECASE)
        if file_match:
            fpath = file_match.group(1)
            if fpath.endswith(".md"):
                inputs["script_path"] = fpath
            elif fpath.endswith(".srt"):
                inputs["srt_path"] = fpath
            elif fpath.endswith(".mp4"):
                inputs["raw_video_path"] = fpath

        # Extract topic: after "tentang", "about", "mengenai", or inside quotes
        quote_match = re.search(r'["“\']([^"”\']+)["”\']', text)
        if quote_match:
            inputs["topic"] = quote_match.group(1).strip()
        else:
            topic_match = re.search(r"(?:tentang|about|mengenai|topik)\s+([^\.\,\;\?\n]+)", text, re.IGNORECASE)
            if topic_match:
                inputs["topic"] = topic_match.group(1).strip()

        # If user explicitly provided raw script text
        if "###" in text or "naskah teleprompter" in text.lower():
            inputs["script_text"] = text

        return inputs
