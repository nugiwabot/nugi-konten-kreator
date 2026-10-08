"""Machine-readable provider capability metadata and capability-based routing."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List


CAPABILITY_MATRIX_PATH = Path(__file__).resolve().parents[1] / "data" / "media_provider_capabilities.json"


@lru_cache(maxsize=1)
def _load_matrix() -> Dict[str, Any]:
    try:
        return json.loads(CAPABILITY_MATRIX_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "providers": {}}


def get_provider_capabilities(provider_name: str) -> Dict[str, Any]:
    """Return a defensive copy of a provider's capability record."""
    record = _load_matrix().get("providers", {}).get((provider_name or "").lower(), {})
    return json.loads(json.dumps(record))


def route_provider_names(
    provider_names: Iterable[str],
    *,
    era: str,
    media_type: str,
    visual_requirement: str,
) -> List[str]:
    """Order provider names using their declared media, era, and intent support."""
    era_key = "historical" if era in ("past", "historical") else era
    media_keys = ["video"] if media_type == "video" else ["photo"] if media_type in {"photo", "image"} else ["photo", "video"]
    vr = (visual_requirement or "GENERIC_ALLOWED").upper()
    if vr in {"REAL_REQUIRED", "REAL_PREFERRED"}:
        route_keys = [f"{era_key}_{key}" for key in media_keys]
    else:
        route_keys = [f"generic_{key}" for key in media_keys]

    raw_names = list(dict.fromkeys(str(name).lower() for name in provider_names))
    providers = _load_matrix().get("providers", {})
    names = []
    for name in raw_names:
        profile = providers.get(name)
        if profile:
            supported = profile.get("media_types", [])
            media_supported = any(
                ("video" if key == "video" else "image") in supported for key in media_keys
            )
            eras = profile.get("eras", [])
            if not media_supported or (era_key not in eras and "all" not in eras):
                continue
        names.append(name)

    def priority(name: str) -> tuple[int, int]:
        profile = providers.get(name, {})
        supported = profile.get("media_types", [])
        media_supported = any(
            ("video" if key == "video" else "image") in supported for key in media_keys
        )
        eras = profile.get("eras", [])
        era_supported = era_key in eras or "all" in eras
        # For any media type, use the best supported medium while preserving
        # image/video capability checks and stable input order for ties.
        priorities = [profile.get("route_priority", {}).get(key) for key in route_keys]
        priorities = [int(value) for value in priorities if value is not None]
        score = min(priorities) if priorities else None
        # Custom providers without a profile remain available as soft fallbacks.
        if score is None:
            score = 99 if media_supported and era_supported else 999
        elif not media_supported or not era_supported:
            score += 1000
        return int(score), names.index(name)

    return sorted(names, key=priority)
