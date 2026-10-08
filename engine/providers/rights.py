"""Conservative, per-asset reuse classification for downloaded media."""

from __future__ import annotations

import re
from typing import Any, Iterable

from engine.config import MEDIA_REUSABLE_LICENSES


REUSABLE_RIGHTS_STATUSES = {
    "PUBLIC_DOMAIN",
    "CC0",
    "CC_BY",
    "CC_BY_SA",
    "COMMERCIAL_ALLOWED",
    "FREE_WITH_ATTRIBUTION",
}


def classify_rights(
    *,
    license_name: str = "",
    license_url: str = "",
    rights_statement: str = "",
    stated_status: str = "",
    provider: str = "",
) -> str:
    """Classify only explicit reuse signals; ambiguous "free" labels stay unknown."""
    status = (stated_status or "").strip().upper().replace("-", "_").replace(" ", "_")
    allowed_states = REUSABLE_RIGHTS_STATUSES | {
        "EDITORIAL_ONLY", "LICENSE_REQUIRED", "UNKNOWN", "RESTRICTED",
    }
    if status in allowed_states and status != "UNKNOWN":
        return status

    text = " ".join((license_name, license_url, rights_statement)).lower()
    compact = re.sub(r"\s+", " ", text)

    if any(token in compact for token in ("all rights reserved", "no reuse", "not for reuse", "restricted")):
        return "RESTRICTED"
    if any(token in compact for token in ("editorial use only", "editorial-only", "news use only")):
        return "EDITORIAL_ONLY"
    if any(token in compact for token in ("license required", "permission required", "contact the rights holder")):
        return "LICENSE_REQUIRED"
    # Non-commercial, no-derivatives, and otherwise incompatible terms are not
    # considered reusable for a video production workflow by the default policy.
    if any(token in compact for token in ("by-nc", "by/4.0/nc", "noncommercial", "non-commercial", "by-nd", "no derivatives", "no-derivatives")):
        return "RESTRICTED"
    if any(token in compact for token in ("creativecommons.org/publicdomain/zero", "cc0", "cc zero", "public domain", "public-domain", "u.s. government work")):
        return "CC0" if "cc0" in compact or "publicdomain/zero" in compact or "cc zero" in compact else "PUBLIC_DOMAIN"
    if any(token in compact for token in ("by-sa", "by/4.0/sa", "cc by-sa", "cc-by-sa")):
        return "CC_BY_SA"
    if any(token in compact for token in ("creativecommons.org/licenses/by/", "cc by 4", "cc-by-4", "cc by 3", "cc-by-3")):
        return "CC_BY"
    if "commercial use permitted" in compact or "commercial-use allowed" in compact:
        return "COMMERCIAL_ALLOWED"
    if "attribution required" in compact or "free with attribution" in compact:
        return "FREE_WITH_ATTRIBUTION"
    # "free", "no known restrictions", and provider-level terms do not establish
    # that this specific asset may be reused commercially or edited.
    return "UNKNOWN"


def is_reusable_rights_status(status: str, allowed: Iterable[str] = MEDIA_REUSABLE_LICENSES) -> bool:
    return (status or "UNKNOWN").upper() in {str(item).upper() for item in allowed}


def item_rights_status(item: Any) -> str:
    metadata = getattr(item, "metadata", {}) or {}
    return classify_rights(
        license_name=getattr(item, "license", ""),
        license_url=getattr(item, "license_url", "") or metadata.get("license_url", ""),
        rights_statement=metadata.get("rights_statement", "") or metadata.get("rights_advisory", ""),
        stated_status=getattr(item, "rights_status", ""),
        provider=getattr(item, "provider", ""),
    )
