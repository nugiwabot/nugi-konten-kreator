"""Structured research intelligence distilled from evidence and feed discovery."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from engine.intelligence.rss import FeedEventCluster, FeedItem, cluster_feed_items
from engine.pipeline.visual_requirements import extract_entities


_CURRENT_CUES = (
    "latest", "breaking", "today", "this week", "this month", "current", "recent",
    "terbaru", "hari ini", "minggu ini", "bulan ini", "saat ini", "berita", "ongoing",
)


@dataclass
class ResearchIntelligence:
    topic: str
    intent: str = "general_research"
    recency: str = "historical_or_general"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    entities: List[Dict[str, str]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    rss_discoveries: List[Dict[str, Any]] = field(default_factory=list)
    discovery_sources: List[Dict[str, str]] = field(default_factory=list)
    primary_source_queries: List[str] = field(default_factory=list)
    escalation_results: List[Dict[str, str]] = field(default_factory=list)
    visual_entities: List[str] = field(default_factory=list)
    visual_events: List[str] = field(default_factory=list)
    visual_locations: List[str] = field(default_factory=list)
    visual_time_periods: List[str] = field(default_factory=list)
    recommended_broll_queries: List[str] = field(default_factory=list)
    evidence_status: str = "DISCOVERY_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_research_recency(topic: str, requested_recency: Optional[str] = None) -> str:
    requested = (requested_recency or "").strip().lower()
    if requested in {"d", "day", "24h", "breaking"}:
        return "breaking"
    if requested in {"w", "week", "7d", "recent"}:
        return "recent"
    if requested in {"m", "month", "30d", "current"}:
        return "current"
    if requested in {"y", "year"}:
        return "current"
    lower = (topic or "").lower()
    if any(cue in lower for cue in _CURRENT_CUES):
        if any(cue in lower for cue in ("breaking", "hari ini", "today", "latest", "terbaru")):
            return "breaking"
        return "current"
    return "historical_or_general"


def _merge_entities(*texts: str) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    seen = set()
    for text in texts:
        for item in extract_entities(text):
            key = item["name"].strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(item)
    return result


def build_research_intelligence(
    topic: str,
    discoveries: Sequence[FeedItem] = (),
    *,
    recency: Optional[str] = None,
    evidence_entities: Sequence[str] = (),
) -> ResearchIntelligence:
    """Create a discovery-only event/entity bridge for research and B-roll."""
    mode = detect_research_recency(topic, recency)
    clusters = cluster_feed_items(list(discoveries))
    source_text = " ".join(item.title for item in discoveries[:40])
    entities = _merge_entities(topic, source_text)
    seen_entity_names = {item["name"].lower() for item in entities}
    for value in evidence_entities:
        if value and value.lower() not in seen_entity_names:
            entities.append({"type": "ENTITY", "name": value})
            seen_entity_names.add(value.lower())

    locations = [item["name"] for item in entities if item.get("type") in {"PLACE", "CITY", "COUNTRY", "LOCATION"}]
    dates = [item["name"] for item in entities if item.get("type") in {"DATE", "YEAR", "HISTORICAL_PERIOD"}]
    event_dicts = [cluster.to_dict() for cluster in clusters]
    event_titles = [cluster.canonical_event for cluster in clusters[:6]]
    entity_names = [item["name"] for item in entities if item.get("type") not in {"DATE", "HISTORICAL_PERIOD"}]

    escalation_queries = []
    for title in event_titles[:3]:
        query = f'"{title}" official report OR primary source'
        if query not in escalation_queries:
            escalation_queries.append(query)

    broll_queries = []
    base_parts = [topic.strip()]
    if entity_names:
        base_parts.extend(entity_names[:3])
    if locations:
        base_parts.extend(locations[:2])
    if dates:
        base_parts.extend(dates[:2])
    base = " ".join(dict.fromkeys(part for part in base_parts if part))
    if base:
        broll_queries.append(base)
    for title in event_titles[:4]:
        query = " ".join(part for part in (title, *locations[:1], *dates[:1], "documentary photo video") if part)
        if query and query not in broll_queries:
            broll_queries.append(query)
    for entity in entity_names[:2]:
        query = " ".join(part for part in (entity, *locations[:1], *dates[:1], "official archive") if part)
        if query and query not in broll_queries:
            broll_queries.append(query)

    source_rows = []
    seen_sources = set()
    for item in discoveries:
        url = item.canonical_url
        if not url or url in seen_sources:
            continue
        seen_sources.add(url)
        source_rows.append({
            "source_id": item.source_id,
            "source_name": item.source_name,
            "url": url,
            "feed_url": item.feed_url,
            "published_at": item.published_at,
            "trust_tier": item.trust_tier,
            "source_type": item.source_type,
            "evidence_status": "DISCOVERY_ONLY",
        })

    return ResearchIntelligence(
        topic=topic,
        intent="current_event_research" if mode in {"breaking", "recent", "current"} else "general_research",
        recency=mode,
        entities=entities,
        events=event_dicts,
        locations=locations,
        dates=dates,
        rss_discoveries=[item.to_dict() for item in discoveries],
        discovery_sources=source_rows,
        primary_source_queries=escalation_queries,
        visual_entities=entity_names[:8],
        visual_events=event_titles[:8],
        visual_locations=locations[:8],
        visual_time_periods=dates[:8],
        recommended_broll_queries=broll_queries[:8],
        evidence_status="DISCOVERY_ONLY" if discoveries else "NO_FEED_DISCOVERY",
    )
