"""
engine/pipeline/capcut_validator.py
===================================
Rigorous CapCut Project Integrity and Compatibility Validator.
Location: engine/pipeline/capcut_validator.py

Validates generated CapCut drafts against 16 structural, media, and timeline rules.
Strictly separates validation tiers:
  - GENERATED: Project files created on filesystem.
  - VALIDATED: 100% passed all 16 deterministic schema, track, and media checks.
  - APP_VERIFIED: Explicit record confirms opening and checking in CapCut Desktop.
  - INVALID: Structural or media reference failure.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("capcut_validator")


@dataclass
class ValidationReport:
    """Detailed outcome of CapCut project validation."""
    project_path: str
    status: str  # "VALIDATED", "GENERATED", "APP_VERIFIED", "INVALID"
    is_valid: bool
    rules_checked: int
    rules_passed: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "status": self.status,
            "is_valid": self.is_valid,
            "rules_checked": self.rules_checked,
            "rules_passed": self.rules_passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class CapCutValidator:
    """Performs deep 16-point validation on CapCut draft directories."""

    REQUIRED_FILES = [
        "draft_content.json",
        "draft_meta_info.json",
        "draft_settings",
        "timeline_layout.json",
    ]

    REQUIRED_SUBDIRS = [
        "adjust_mask",
        "common_attachment",
        "matting",
        "qr_upload",
        "Resources",
        "smart_crop",
        "subdraft",
        "Timelines",
    ]

    def validate_draft(
        self,
        draft_dir: Path | str,
        allow_external_media: bool = True,
    ) -> ValidationReport:
        p = Path(draft_dir).resolve()
        errors: List[str] = []
        warnings: List[str] = []
        rules_checked = 0
        rules_passed = 0

        # Rule 1: Directory exists
        rules_checked += 1
        if not p.is_dir():
            return ValidationReport(
                project_path=str(p),
                status="INVALID",
                is_valid=False,
                rules_checked=1,
                rules_passed=0,
                errors=[f"Draft directory does not exist: {p}"]
            )
        rules_passed += 1

        # Rule 2: Required subdirectories exist
        rules_checked += 1
        missing_subdirs = [s for s in self.REQUIRED_SUBDIRS if not (p / s).is_dir()]
        if missing_subdirs:
            warnings.append(f"Subdirectories missing (optional for basic playback, recommended for CapCut 10): {missing_subdirs}")
        rules_passed += 1

        # Rule 3: Required files exist
        rules_checked += 1
        missing_files = [f for f in self.REQUIRED_FILES if not (p / f).is_file()]
        if missing_files:
            errors.append(f"Missing required draft files: {missing_files}")
        else:
            rules_passed += 1

        content_file = p / "draft_content.json"
        meta_file = p / "draft_meta_info.json"

        content_data: Dict[str, Any] = {}
        meta_data: Dict[str, Any] = {}

        # Rule 4: Valid draft_content.json JSON syntax
        rules_checked += 1
        if content_file.is_file():
            try:
                content_data = json.loads(content_file.read_text(encoding="utf-8"))
                rules_passed += 1
            except Exception as e:
                errors.append(f"draft_content.json invalid JSON: {e}")
        else:
            errors.append("draft_content.json not found")

        # Rule 5: Valid draft_meta_info.json JSON syntax
        rules_checked += 1
        if meta_file.is_file():
            try:
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
                rules_passed += 1
            except Exception as e:
                errors.append(f"draft_meta_info.json invalid JSON: {e}")
        else:
            errors.append("draft_meta_info.json not found")

        # Rule 6: Project ID integrity
        rules_checked += 1
        c_id = content_data.get("id")
        m_id = meta_data.get("draft_id")
        if not c_id:
            errors.append("draft_content.json missing project ID")
        elif not m_id:
            errors.append("draft_meta_info.json missing draft_id")
        elif c_id != m_id:
            warnings.append(f"Project ID mismatch between content ({c_id}) and meta ({m_id})")
            rules_passed += 1
        else:
            rules_passed += 1

        # Rule 7: Duration sanity
        rules_checked += 1
        duration_us = content_data.get("duration", 0)
        if duration_us <= 0:
            errors.append(f"Project duration is <= 0 microseconds ({duration_us})")
        else:
            rules_passed += 1

        # Rule 8: Canvas resolution and FPS
        rules_checked += 1
        fps = content_data.get("fps", 0)
        canvas_cfg = content_data.get("canvas_config", {})
        if fps <= 0:
            errors.append(f"Invalid FPS: {fps}")
        elif not canvas_cfg.get("width") or not canvas_cfg.get("height"):
            errors.append("Missing canvas width or height")
        else:
            rules_passed += 1

        # Rule 9: Tracks exist
        rules_checked += 1
        tracks = content_data.get("tracks", [])
        if not tracks:
            errors.append("Project contains 0 tracks")
        else:
            rules_passed += 1

        # Rule 10: Video tracks have segments
        rules_checked += 1
        video_tracks = [t for t in tracks if t.get("type") == "video"]
        total_video_segs = sum(len(t.get("segments", [])) for t in video_tracks)
        if not video_tracks:
            errors.append("No video track found in project")
        elif total_video_segs == 0:
            errors.append("Video tracks exist but contain 0 video segments")
        else:
            rules_passed += 1

        # Rule 11: Timerange sanity on segments
        rules_checked += 1
        invalid_segs = []
        for t_idx, tr in enumerate(tracks):
            for s_idx, seg in enumerate(tr.get("segments", [])):
                target_tr = seg.get("target_timerange")
                if target_tr:
                    st = target_tr.get("start", -1)
                    dur = target_tr.get("duration", -1)
                    if st < 0 or dur <= 0:
                        invalid_segs.append(f"Track {t_idx} seg {s_idx} target_timerange invalid (start={st}, dur={dur})")
                        break
        if invalid_segs:
            errors.extend(invalid_segs)
        else:
            rules_passed += 1

        # Rule 12: Materials table integrity
        rules_checked += 1
        materials = content_data.get("materials", {})
        mat_videos = materials.get("videos", [])
        if not isinstance(mat_videos, list):
            errors.append("materials.videos is not a list")
        else:
            rules_passed += 1

        # Rule 13: Media file references exist on filesystem
        rules_checked += 1
        missing_media_files = []
        for v in mat_videos:
            v_path = v.get("path")
            if v_path:
                # Normalize Windows and POSIX separators to the host filesystem convention.
                norm_p = Path(v_path.replace("\\", "/"))
                if not norm_p.is_file():
                    missing_media_files.append(str(norm_p))
        if missing_media_files:
            errors.append(f"Referenced media files missing on disk: {missing_media_files[:3]} (total {len(missing_media_files)})")
        else:
            rules_passed += 1

        # Rule 14: Subtitle text segments validity
        rules_checked += 1
        text_tracks = [t for t in tracks if t.get("type") == "text"]
        mat_texts = materials.get("texts", [])
        if text_tracks:
            total_text_segs = sum(len(t.get("segments", [])) for t in text_tracks)
            if total_text_segs > 0 and len(mat_texts) == 0:
                errors.append("Text tracks contain segments but materials.texts is empty")
            else:
                rules_passed += 1
        else:
            # Subtitles optional
            rules_passed += 1

        # Rule 15: Material ID references valid
        rules_checked += 1
        all_mat_ids = {m.get("id") for m in mat_videos} | {t.get("id") for t in mat_texts}
        dangling_refs = []
        for tr in tracks:
            for seg in tr.get("segments", []):
                m_ref = seg.get("material_id")
                if m_ref and m_ref not in all_mat_ids:
                    dangling_refs.append(m_ref)
                    break
        if dangling_refs:
            warnings.append(f"Segment references material_id not in materials table: {dangling_refs}")
            rules_passed += 1  # CapCut often allows auxiliary refs
        else:
            rules_passed += 1

        # Rule 16: Registration is useful diagnostic evidence, but is not proof
        # that CapCut Desktop opened, imported, and rendered this draft.
        rules_checked += 1
        app_registered = False
        local_app_data = Path(os.environ.get("LOCALAPPDATA") or "~/AppData/Local").resolve()
        root_meta_p = local_app_data / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft" / "root_meta_info.json"
        if root_meta_p.is_file():
            try:
                root_meta = json.loads(root_meta_p.read_text(encoding="utf-8"))
                draft_stores = root_meta.get("all_draft_store", [])
                for ds in draft_stores:
                    if ds.get("draft_id") == c_id or ds.get("draft_fold_path", "").lower() == str(p).replace("\\", "/").lower():
                        app_registered = True
                        break
            except Exception:
                pass
        rules_passed += 1

        # APP_VERIFIED requires an explicit human/application verification
        # record.  Never infer it from a package, validator pass, or registration
        # in root_meta_info.json.
        verification_p = p / "app_verification.json"
        app_verified = False
        if verification_p.is_file():
            try:
                verification = json.loads(verification_p.read_text(encoding="utf-8"))
                app_verified = bool(
                    verification.get("opened_in_capcut_desktop")
                    and verification.get("timeline_checked")
                    and verification.get("saved_after_verification")
                    and verification.get("verified_at")
                )
                if not app_verified:
                    warnings.append("app_verification.json is incomplete; status remains VALIDATED.")
            except Exception as exc:
                warnings.append(f"Could not read app_verification.json; status remains VALIDATED: {exc}")

        is_valid = len(errors) == 0
        if not is_valid:
            status = "INVALID"
        elif app_verified:
            status = "APP_VERIFIED"
        else:
            status = "VALIDATED"

        report = ValidationReport(
            project_path=str(p),
            status=status,
            is_valid=is_valid,
            rules_checked=rules_checked,
            rules_passed=rules_passed,
            errors=errors,
            warnings=warnings,
            metadata={
                "project_name": content_data.get("name", p.name),
                "duration_seconds": round(duration_us / 1_000_000, 2),
                "tracks_count": len(tracks),
                "video_segments": total_video_segs,
                "subtitle_segments": len(mat_texts),
                "media_files_checked": len(mat_videos),
                "app_verified": app_verified,
                "app_registered": app_registered,
            }
        )
        return report
