"""
Deterministic natural-language request resolver for Nugi Content Creator.
It converts a sparse user instruction into a safe execution contract.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


DISCOVERY_PATTERNS = (
    r"\bcari(?:kan)?\b.*\b(?:topik|ide|gagasan)\b",
    r"\b(?:topik|ide)\b.*\b(?:minggu|bulan|terbaik|menarik|konten|video)\b",
    r"\b(?:content|video)\s+ideas?\b",
    r"\bide\s+konten\b",
    r"\btopik\s+(?:yang\s+)?menarik\b",
)
RESEARCH_PATTERNS = (
    r"\b(?:riset|research|teliti|telusuri|investigasi|mendalam)\b",
    r"\bdeep\s+research\b",
    r"\binvestigative\b",
)
FACT_CHECK_PATTERNS = (
    r"\bfact[- ]?check\b",
    r"\bcek\s+fakta\b",
    r"\bperiksa\s+fakta\b",
)
BROLL_PATTERNS = (
    r"\bb[- ]?roll\b",
    r"\bfootage\b",
    r"\bvisual\s+(?:research|riset|footage)\b",
)
REPURPOSE_PATTERNS = (
    r"\bubah\b.*\b(?:short|shorts|reels)\b",
    r"\bjadikan\b.*\b(?:short|shorts|reels)\b",
    r"\brepurpose\b",
)
LONGFORM_PATTERNS = (
    r"\blong[ -]?form\b",
    r"\bvideo\s+panjang\b",
    r"\byoutube\s+(?:long|panjang)\b",
    r"\bdurasi\s+(?:10|[1-9]\d+)\s*(?:menit|minutes?)\b",
)
SHORT_PATTERNS = (
    r"\bshorts?\b",
    r"\breels?\b",
    r"\btiktok\b",
    r"\bshort\s+video\b",
)
CURRENT_PATTERNS = (
    r"\bterkini\b",
    r"\bterbaru\b",
    r"\bterhangat\b",
    r"\bminggu\s+ini\b",
    r"\bbulan\s+ini\b",
    r"\blatest\b",
    r"\bcurrent\b",
    r"\brecent\b",
)
INVESTIGATIVE_PATTERNS = (
    r"\bsangat\s+mendalam\b",
    r"\bmendalam\b",
    r"\binvestigat(?:ive|if)\b",
    r"\bbedah\b.*\b(?:tuntas|mendalam)\b",
)


@dataclass(frozen=True)
class ResolvedRequest:
    original_request: str
    intent: str
    topic: str
    format: str
    duration_seconds: Optional[float]
    research_depth: str
    recency: Optional[str]
    requested_count: int
    needs_idea_discovery: bool
    needs_research: bool
    needs_fact_check: bool
    needs_visual_research: bool
    needs_broll: bool
    needs_capcut: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _extract_count(text: str) -> int:
    match = re.search(
        r"\b(\d{1,2})\s+(?:buah\s+)?(?:ide|topik|shorts?|reels?|video)\b",
        text,
        re.IGNORECASE,
    )
    return max(1, min(50, int(match.group(1)))) if match else 1


def _extract_duration(text: str) -> Optional[float]:
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*(?:detik|sec(?:ond)?s?|s)\b",
        text,
        re.IGNORECASE,
    )
    if range_match:
        return round((float(range_match.group(1)) + float(range_match.group(2))) / 2.0, 1)

    sec_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:detik|sec(?:ond)?s?)\b", text, re.IGNORECASE)
    if sec_match:
        return float(sec_match.group(1))

    minute_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:menit|minutes?)\b", text, re.IGNORECASE)
    if minute_match:
        return float(minute_match.group(1)) * 60.0
    return None


def _extract_topic(text: str) -> str:
    cleaned = text.strip()
    match = re.search(
        r"(?:tentang|mengenai|soal|about)\s+(.+?)(?:\s+(?:dengan|gaya|style)\s+.+)?$",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        topic = match.group(1).strip(" .,:;-")
        if topic:
            return topic

    topic = re.sub(
        r"^\s*(?:tolong\s+)?(?:buat(?:kan)?|bikin|ciptakan|generate|create|make)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\b(?:video\s+)?(?:shorts?|short\s+video|long[ -]?form)\b", " ", topic, flags=re.IGNORECASE)
    topic = re.sub(r"\b(?:youtube|reels?|tiktok)\b", " ", topic, flags=re.IGNORECASE)
    topic = re.sub(r"\b(?:minggu|bulan)\s+ini\b", " ", topic, flags=re.IGNORECASE)
    topic = re.sub(r"\s+", " ", topic).strip(" .,:;-")
    # Generic production commands are not content topics.
    if re.fullmatch(
        r"(?:\d{1,2}\s+)?(?:shorts?|reels?|videos?|script(?:s)?|konten|ide|topik)(?:\s+(?:video|konten|script|shorts?))?",
        topic,
        flags=re.IGNORECASE,
    ):
        return ""
    if re.fullmatch(r"\d{1,2}", topic):
        return ""
    return topic


def resolve_request(
    request: str,
    *,
    format_hint: Optional[str] = None,
    duration_hint: Optional[float] = None,
    depth_hint: Optional[str] = None,
    recency_hint: Optional[str] = None,
) -> ResolvedRequest:
    original = (request or "").strip()
    text = original.lower()

    requested_count = _extract_count(text)
    explicit_duration = _extract_duration(original)

    is_discovery = _matches(text, DISCOVERY_PATTERNS)
    is_research = _matches(text, RESEARCH_PATTERNS)
    is_fact_check = _matches(text, FACT_CHECK_PATTERNS)
    is_broll = _matches(text, BROLL_PATTERNS)
    is_repurpose = _matches(text, REPURPOSE_PATTERNS)

    if is_discovery and not is_repurpose:
        intent = "DISCOVER_CONTENT"
    elif is_fact_check:
        intent = "FACT_CHECK"
    elif is_broll and "buat video" not in text and "bikin video" not in text and "create video" not in text:
        intent = "BROLL_RESEARCH"
    elif is_repurpose:
        intent = "REPURPOSE_CONTENT"
    elif is_research and not any(x in text for x in ("buat video", "bikin video", "create video", "buatkan video")):
        intent = "RESEARCH_TOPIC"
    else:
        intent = "CREATE_CONTENT"

    if _matches(text, LONGFORM_PATTERNS):
        resolved_format = "longform"
    elif _matches(text, SHORT_PATTERNS):
        resolved_format = "short"
    elif format_hint and str(format_hint).lower() not in {"", "auto"}:
        resolved_format = str(format_hint).lower()
    else:
        resolved_format = "short"

    duration = duration_hint if duration_hint and duration_hint > 0 else explicit_duration
    if duration is None and resolved_format == "longform":
        duration = 600.0
    elif duration is None and resolved_format in {"short", "reel"}:
        duration = 75.0

    if depth_hint and depth_hint.lower() not in {"", "auto"}:
        research_depth = depth_hint.lower()
    elif _matches(text, INVESTIGATIVE_PATTERNS):
        research_depth = "investigative"
    else:
        research_depth = "deep"

    recency = recency_hint or ("m" if _matches(text, CURRENT_PATTERNS) else None)
    topic = _extract_topic(original)

    needs_production = intent in {"CREATE_CONTENT", "REPURPOSE_CONTENT"}
    needs_broll = intent in {"CREATE_CONTENT", "REPURPOSE_CONTENT", "BROLL_RESEARCH"}

    if intent == "DISCOVER_CONTENT":
        reason = "Content opportunity discovery requested."
    elif intent == "RESEARCH_TOPIC":
        reason = "Topic research requested without forcing production."
    elif intent == "BROLL_RESEARCH":
        reason = "Visual/media research requested."
    elif intent == "FACT_CHECK":
        reason = "Factual verification requested."
    elif intent == "REPURPOSE_CONTENT":
        reason = "Existing content should be transformed into derivatives."
    else:
        reason = "End-to-end production inferred from the natural-language request."

    return ResolvedRequest(
        original_request=original,
        intent=intent,
        topic="" if intent == "DISCOVER_CONTENT" else topic,
        format=resolved_format,
        duration_seconds=duration,
        research_depth=research_depth,
        recency=recency,
        requested_count=requested_count,
        needs_idea_discovery=is_discovery or (intent == "CREATE_CONTENT" and not topic),
        needs_research=intent in {"CREATE_CONTENT", "REPURPOSE_CONTENT", "RESEARCH_TOPIC"},
        needs_fact_check=needs_production,
        needs_visual_research=needs_broll or intent == "CREATE_CONTENT",
        needs_broll=needs_broll,
        needs_capcut=intent == "CREATE_CONTENT",
        reason=reason,
    )
