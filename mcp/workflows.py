"""Compatibility MCP workflow surface backed only by ProductionOrchestrator.

The old workflow registry/executor had its own execution graph and persisted
state. This module keeps the public MCP names while delegating every production
action and resume lookup to the canonical manifest-based run.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from security import SecurityError, resolve_safe_path
from engine.production.production_manifest import ProductionManifest
from engine.production.production_orchestrator import ProductionOrchestrator


class WorkflowService:
    """Thin compatibility wrapper; it owns no production logic or state."""

    _COMPATIBILITY_WORKFLOWS = {
        "content_idea": "research",
        "research_only": "research",
        "script_only": "script",
        "fact_check": "script",
        "content_audit": "script",
        "short_video": None,
        "full_video": None,
        "broll": None,
        "subtitle": None,
        "capcut_draft": None,
    }

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def list_workflows(self) -> List[Dict[str, Any]]:
        return [
            {
                "workflow_id": workflow_id,
                "name": workflow_id.replace("_", " ").title(),
                "description": "Compatibility view of the canonical ProductionOrchestrator pipeline.",
                "canonical_entry_point": "nugi_content_create",
                "required_inputs": ["topic"],
                "state_source": "ProductionManifest",
            }
            for workflow_id in self._COMPATIBILITY_WORKFLOWS
        ]

    def explain_workflow(self, workflow_id: str) -> Dict[str, Any]:
        if workflow_id not in self._COMPATIBILITY_WORKFLOWS:
            return {"error": f"Workflow '{workflow_id}' not found.", "available_workflows": list(self._COMPATIBILITY_WORKFLOWS)}
        return {
            "workflow_id": workflow_id,
            "compatibility_wrapper": True,
            "canonical_entry_point": "nugi_content_create",
            "canonical_orchestrator": "ProductionOrchestrator",
            "state_source": "ProductionManifest",
            "stage_limit": self._COMPATIBILITY_WORKFLOWS[workflow_id],
        }

    def plan_workflow(self, request: str) -> Dict[str, Any]:
        topic = self._topic_from_request(request)
        return {
            "mode": "PLAN",
            "status": "planned" if topic else "needs_input",
            "canonical_entry_point": "nugi_content_create",
            "canonical_orchestrator": "ProductionOrchestrator",
            "topic": topic,
            "required_inputs": [] if topic else ["topic"],
            "recommended_next_action": "Run nugi_content_create with the topic." if topic else "Provide a production topic.",
        }

    def preflight_workflow(self, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if workflow_id not in self._COMPATIBILITY_WORKFLOWS:
            return {"workflow_id": workflow_id, "status": "BLOCKED", "missing_items": ["Unknown workflow_id"]}
        context = self._sanitize_context(context or {})
        topic, workspace = self._resolve_topic_and_workspace(context)
        if not topic:
            return {
                "workflow_id": workflow_id,
                "status": "BLOCKED",
                "missing_items": ["Missing required input: 'topic' (or a workspace with manifest.json)"],
                "canonical_entry_point": "nugi_content_create",
            }
        return {
            "workflow_id": workflow_id,
            "status": "READY",
            "canonical_entry_point": "nugi_content_create",
            "canonical_orchestrator": "ProductionOrchestrator",
            "state_source": "ProductionManifest",
            "workspace": workspace,
            "topic": topic,
        }

    def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        if workflow_id not in self._COMPATIBILITY_WORKFLOWS:
            return {"status": "failed", "error": f"Workflow '{workflow_id}' not found."}
        context = self._sanitize_context(context or {})
        resolved = self._find_manifest(run_id) if run_id else None
        if resolved:
            manifest, work_dir = resolved
            topic = manifest.topic
            output_folder = str(work_dir.relative_to(self.repo_root / "output"))
        else:
            topic, output_folder = self._resolve_topic_and_workspace(context)
        if not topic:
            return {"status": "blocked", "error": "A topic or canonical production workspace is required."}

        result = ProductionOrchestrator(repo_root=self.repo_root).run(
            topic_or_prompt=topic,
            output_folder=output_folder or context.get("output_folder"),
            format_hint=context.get("format", "short"),
            duration_hint=context.get("duration_seconds"),
            depth=context.get("depth", "deep"),
            dry_run=dry_run,
            stage_limit=self._COMPATIBILITY_WORKFLOWS[workflow_id],
            max_broll_shots=context.get("max_broll_shots"),
            install_to_capcut=bool(context.get("install_to_capcut", False)),
            recency=context.get("recency"),
        )
        payload = result.to_dict()
        payload.update({
            "workflow_id": workflow_id,
            "compatibility_wrapper": True,
            "canonical_entry_point": "nugi_content_create",
        })
        return payload

    def workflow_status(self, run_id: str) -> Dict[str, Any]:
        resolved = self._find_manifest(run_id)
        if not resolved:
            return {"error": f"Production run '{run_id}' not found."}
        manifest, work_dir = resolved
        return {"workspace": str(work_dir), "manifest": manifest.to_dict(), "state_source": "ProductionManifest"}

    def resume_workflow(self, run_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resolved = self._find_manifest(run_id)
        if not resolved:
            return {"status": "failed", "error": f"Production run '{run_id}' not found."}
        manifest, _ = resolved
        return self.execute_workflow("short_video", context=context, run_id=manifest.run_id)

    def _find_manifest(self, run_id: Optional[str]) -> Optional[tuple[ProductionManifest, Path]]:
        if not run_id:
            return None
        output_root = self.repo_root / "output"
        if not output_root.is_dir():
            return None
        for manifest_p in output_root.rglob("manifest.json"):
            try:
                manifest = ProductionManifest.load(manifest_p)
            except Exception:
                continue
            if manifest.run_id == run_id:
                return manifest, manifest_p.parent
        return None

    def _resolve_topic_and_workspace(self, context: Dict[str, Any]) -> tuple[str, Optional[str]]:
        topic = str(context.get("topic") or "").strip()
        workspace = context.get("output_folder") or context.get("workspace")
        if workspace:
            candidate = self.repo_root / "output" / str(workspace)
            manifest_p = candidate / "manifest.json"
            if manifest_p.is_file():
                manifest = ProductionManifest.load(manifest_p)
                return topic or manifest.topic, str(workspace)
        return topic, str(workspace) if workspace else None

    @staticmethod
    def _topic_from_request(request: str) -> str:
        quoted = re.search(r'["“\']([^"”\']+)["”\']', request)
        if quoted:
            return quoted.group(1).strip()
        match = re.search(r"(?:tentang|mengenai|about)\s+([^\n.,;?]+)", request, re.IGNORECASE)
        return match.group(1).strip() if match else request.strip()

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = dict(context)
        for key in ("output_folder", "workspace"):
            value = sanitized.get(key)
            if isinstance(value, str) and value:
                try:
                    safe = resolve_safe_path(self.repo_root / "output", value)
                    sanitized[key] = str(safe.relative_to(self.repo_root / "output"))
                except (SecurityError, ValueError, PermissionError):
                    pass
        return sanitized
