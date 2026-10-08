"""
engine/production/executive_producer.py
=======================================
Executive Producer Orchestration Contract.
Location: engine/production/executive_producer.py

Acts as the strategic decision maker for autonomous content production:
  - Parses user intent, format, style, and duration constraints
  - Formulates production_plan.json
  - Evaluates reuse of existing workspace artifacts
  - Controls gatekeeping decisions between stages
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("executive_producer")


@dataclass
class ProductionPlan:
    """The formal production plan emitted by the Executive Producer."""
    topic: str
    objective: str
    format: str = "short"  # "short", "reel", "longform"
    duration_seconds: float = 75.0
    style: str = "documentary"
    target_audience: str = "general_curious"
    # Explicit production contract for spoken narration pacing.  QA must read
    # this value from the plan, never apply a global short-video range.
    spoken_words_per_minute: float = 138.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Stage flags & configurations
    research_needed: bool = True
    research_depth: str = "deep"
    story_needed: bool = True
    script_needed: bool = True
    fact_check_needed: bool = True
    visual_needed: bool = True
    broll_needed: bool = True
    max_broll_shots: Optional[int] = None
    subtitle_needed: bool = True
    capcut_needed: bool = True
    final_qa_needed: bool = True

    # Artifact reuse guidance
    reuse_existing_dossier: bool = True
    reuse_existing_media: bool = True
    reuse_existing_script: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "objective": self.objective,
            "format": self.format,
            "duration_seconds": self.duration_seconds,
            "style": self.style,
            "target_audience": self.target_audience,
            "spoken_words_per_minute": self.spoken_words_per_minute,
            "target_spoken_words": round(self.duration_seconds * self.spoken_words_per_minute / 60),
            "created_at": self.created_at,
            "research": {
                "needed": self.research_needed,
                "depth": self.research_depth,
                "reuse_existing": self.reuse_existing_dossier,
            },
            "story": {
                "needed": self.story_needed,
            },
            "script": {
                "needed": self.script_needed,
                "reuse_existing": self.reuse_existing_script,
            },
            "fact_check": {
                "needed": self.fact_check_needed,
            },
            "visual": {
                "needed": self.visual_needed,
            },
            "broll": {
                "needed": self.broll_needed,
                "max_shots": self.max_broll_shots,
                "reuse_existing": self.reuse_existing_media,
            },
            "subtitle": {
                "needed": self.subtitle_needed,
            },
            "capcut": {
                "needed": self.capcut_needed,
            },
            "final_qa": {
                "needed": self.final_qa_needed,
            },
        }

    def save(self, workspace_dir: Path | str) -> Path:
        ws = Path(workspace_dir).resolve()
        ws.mkdir(parents=True, exist_ok=True)
        plan_p = ws / "production_plan.json"
        plan_p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return plan_p

    @classmethod
    def load(cls, file_path: Path | str) -> ProductionPlan:
        p = Path(file_path).resolve()
        data = json.loads(p.read_text(encoding="utf-8"))
        res_cfg = data.get("research", {})
        scr_cfg = data.get("script", {})
        bro_cfg = data.get("broll", {})
        return cls(
            topic=data.get("topic", ""),
            objective=data.get("objective", ""),
            format=data.get("format", "short"),
            duration_seconds=float(data.get("duration_seconds", 75.0)),
            style=data.get("style", "documentary"),
            target_audience=data.get("target_audience", "general_curious"),
            spoken_words_per_minute=float(data.get("spoken_words_per_minute", 138.0)),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            research_needed=res_cfg.get("needed", True),
            research_depth=res_cfg.get("depth", "deep"),
            story_needed=data.get("story", {}).get("needed", True),
            script_needed=scr_cfg.get("needed", True),
            fact_check_needed=data.get("fact_check", {}).get("needed", True),
            visual_needed=data.get("visual", {}).get("needed", True),
            broll_needed=bro_cfg.get("needed", True),
            max_broll_shots=bro_cfg.get("max_shots"),
            subtitle_needed=data.get("subtitle", {}).get("needed", True),
            capcut_needed=data.get("capcut", {}).get("needed", True),
            final_qa_needed=data.get("final_qa", {}).get("needed", True),
            reuse_existing_dossier=res_cfg.get("reuse_existing", True),
            reuse_existing_media=bro_cfg.get("reuse_existing", True),
            reuse_existing_script=scr_cfg.get("reuse_existing", False),
        )


class ExecutiveProducer:
    """Deterministic contract parser creating production_plan.json."""

    @staticmethod
    def parse_user_request(
        topic_or_prompt: str,
        format_hint: Optional[str] = None,
        duration_hint: Optional[float] = None,
        depth_hint: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
    ) -> ProductionPlan:
        """
        Interprets user prompt to formulate a complete production plan.
        Extracts duration constraints (e.g. '60-90 detik', '75 detik', 'short').
        """
        clean_text = topic_or_prompt.strip()

        # 1. Duration extraction heuristics
        duration = 75.0  # Default sweet spot for Nugi Shorts
        if duration_hint is not None and duration_hint > 0:
            duration = float(duration_hint)
        else:
            # Check for range: e.g. "60–90 detik" or "60-90 detik" -> average to 75s
            range_match = re.search(r"(\d+)\s*[-–—]\s*(\d+)\s*(?:detik|sec|s)", clean_text, re.IGNORECASE)
            if range_match:
                d1 = float(range_match.group(1))
                d2 = float(range_match.group(2))
                duration = round((d1 + d2) / 2.0, 1)
            else:
                single_match = re.search(r"(\d+)\s*(?:detik|sec|s)", clean_text, re.IGNORECASE)
                if single_match:
                    duration = float(single_match.group(1))

        # 2. Topic extraction
        # If text begins with "Buat video short ... tentang [TOPIC]", extract pure topic
        topic = clean_text
        match_topic = re.search(r"(?:tentang|mengenai|soal)\s+(.+?)(?:,\s*gaya|$)", clean_text, re.IGNORECASE)
        if match_topic:
            topic = match_topic.group(1).strip()
        else:
            # Remove command prefixes like "Buat video short 60-90 detik"
            topic = re.sub(r"^(?:buat|ciptakan|generate|bikin)\s+(?:video\s+)?(?:short\s+)?(?:durasi\s+)?(?:\d+[-–]\d+\s*detik\s+)?", "", topic, flags=re.IGNORECASE).strip()

        # Remove trailing style hints
        topic = re.sub(r",?\s*gaya\s+dokumenter.*$", "", topic, flags=re.IGNORECASE).strip()

        # 3. Format & Objective
        fmt = format_hint or ("short" if duration <= 120 else "longform")
        objective = f"Produce a {duration:.0f}s documentary {fmt} video on '{topic}' in authentic Nugi narrative DNA."

        # 4. Check for artifact reuse in workspace
        reuse_dossier = False
        reuse_media = False
        if workspace_dir and Path(workspace_dir).is_dir():
            ws_p = Path(workspace_dir)
            if (ws_p / "research_dossier.json").is_file():
                reuse_dossier = True
            footage_dir = ws_p / "footage"
            if footage_dir.is_dir() and any(footage_dir.iterdir()):
                reuse_media = True

        return ProductionPlan(
            topic=topic,
            objective=objective,
            format=fmt,
            duration_seconds=duration,
            style="documentary",
            target_audience="general_curious",
            research_needed=True,
            research_depth=depth_hint or "deep",
            story_needed=True,
            script_needed=True,
            fact_check_needed=True,
            visual_needed=True,
            broll_needed=True,
            subtitle_needed=True,
            capcut_needed=True,
            final_qa_needed=True,
            reuse_existing_dossier=reuse_dossier,
            reuse_existing_media=reuse_media,
        )
