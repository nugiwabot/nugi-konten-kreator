"""
engine/pipeline/remotion_engine.py
==================================
Remotion Motion Design and Title Card Rendering Engine.
Location: engine/pipeline/remotion_engine.py

Integrates Nugi's motion graphics design system into video production:
  - 15 production templates (statistic, fact-card, quote-card, headline, etc.)
  - Template catalog and design token inspection
  - Direct rendering to PNG/MP4 assets via Remotion CLI or deterministic fallback
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("remotion_engine")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REMOTION_DIR = REPO_ROOT / "remotion-app"
CATALOG_PATH = REMOTION_DIR / "template-catalog.json"
DESIGN_TOKENS_PATH = REMOTION_DIR / "design-tokens.json"


class RemotionEngine:
    """Manages Remotion motion graphic templates and rendering."""

    def __init__(self, remotion_dir: Optional[Path] = None):
        self.remotion_dir = remotion_dir or REMOTION_DIR
        self.catalog_path = self.remotion_dir / "template-catalog.json"
        self.design_tokens_path = self.remotion_dir / "design-tokens.json"

    def is_available(self) -> bool:
        """Checks if Node.js and Remotion CLI entry point exist."""
        node_bin = shutil.which("node")
        entry_exists = (self.remotion_dir / "src" / "index.tsx").is_file()
        return bool(node_bin and entry_exists)

    def list_templates(self) -> List[Dict[str, Any]]:
        """Returns catalog of all registered Remotion motion templates."""
        if not self.catalog_path.is_file():
            return []
        try:
            data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            return data.get("templates", [])
        except Exception as e:
            logger.warning(f"Error reading Remotion template catalog: {e}")
            return []

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves specification for a specific template."""
        templates = self.list_templates()
        for t in templates:
            if t.get("id") == template_id or t.get("compositionId") == template_id:
                return t
        return None

    def render_title_card(
        self,
        title: str,
        subtitle: str = "",
        output_path: Optional[Path | str] = None,
        duration_seconds: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Renders a documentary title card asset (MP4 or still).
        If Remotion CLI is available, executes remotion render.
        Otherwise, records the title card specification for CapCut text track rendering.
        """
        out_p = Path(output_path).resolve() if output_path else REPO_ROOT / "output" / "title_card.mp4"
        out_p.parent.mkdir(parents=True, exist_ok=True)

        spec = {
            "template": "documentary-text",
            "title": title,
            "subtitle": subtitle,
            "duration_seconds": duration_seconds,
            "output_path": str(out_p),
            "status": "SPECIFIED",
        }

        if self.is_available():
            try:
                cmd = [
                    "npx", "remotion", "still",
                    "Nugi-DocumentaryText",
                    str(out_p.with_suffix(".png")),
                    f"--props={json.dumps({'title': title, 'subtitle': subtitle})}"
                ]
                proc = subprocess.run(cmd, cwd=str(self.remotion_dir), capture_output=True, text=True, timeout=60)
                if proc.returncode == 0:
                    spec["status"] = "RENDERED"
                    spec["rendered_file"] = str(out_p.with_suffix(".png"))
            except Exception as e:
                logger.warning(f"Remotion render skipped/failed: {e}")

        return spec
