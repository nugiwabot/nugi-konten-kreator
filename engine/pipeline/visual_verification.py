"""Injectable pixel-level verification seam for selected real-world B-roll.

No multimodal model endpoint is configured by this project today. The default
verifier therefore records VISUAL_UNKNOWN; metadata search/ranking is never
reported as visual inspection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass
class VisualVerification:
    status: str = "VISUAL_UNKNOWN"  # VISUALLY_CONSISTENT, VISUAL_MISMATCH, VISUAL_UNKNOWN
    method: str = "none"
    reason: str = "No image/video verification model is configured."


class VisualVerifier(Protocol):
    def verify(self, candidate: Any, request: str, context: Dict[str, Any]) -> VisualVerification:
        """Inspect one candidate against the shot's visible factual requirements."""


class UnknownVisualVerifier:
    """Deterministic safe default; does not claim a candidate was visually checked."""

    def verify(self, candidate: Any, request: str, context: Dict[str, Any]) -> VisualVerification:
        return VisualVerification()
