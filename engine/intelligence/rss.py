"""RSS/Atom discovery with bounded parsing, caching, routing, and provenance.

Feed records are discovery leads. This module never promotes a feed item to
verified evidence or downloads media attached to a feed.
"""

from __future__ import annotations

import email.utils
import html
import ipaddress
import json
import logging
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from engine.config import (
    RSS_CACHE_TTL_SECONDS,
    RSS_DISCOVERY_ENABLED,
    RSS_FEED_REGISTRY_PATH,
    RSS_FETCH_TIMEOUT_SECONDS,
    RSSHUB_BASE_URL,
    RSSHUB_FALLBACK_URL,
    RSS_MAX_FEED_BYTES,
    RSS_MAX_SOURCES_PER_QUERY,
)

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "data" / "feed_registry.json"
MAX_FEED_BYTES = 2 * 1024 * 1024
MAX_FEED_ITEMS = 200
MAX_URLS_PER_ITEM = 20
_USER_AGENT = "NugiContentIntelligence/1.0 (+https://github.com/nugiwabot/nugi-konten-kreator)"


@dataclass
class FeedSource:
    id: str
    name: str
    feed_url: str = ""
    region: str = "international"
    country: str = ""
    language: str = ""
    category: str = "news"
    source_type: str = "publisher"
    base_url: str = ""
    route_type: str = "direct"
    rsshub_route: str = ""
    trust_tier: str = "S4"
    rights_policy: str = "editorial_discovery_only"
    evidence_role: str = "discovery_only"
    enabled: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class FeedItem:
    source_id: str
    source_name: str
    feed_url: str
    title: str
    description: str = ""
    content: str = ""
    published_at: str = ""
    updated_at: str = ""
    canonical_url: str = ""
    guid: str = ""
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    enclosure_urls: List[str] = field(default_factory=list)
    media_types: List[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trust_tier: str = "S4"
    source_type: str = "publisher"
    rights_policy: str = "editorial_discovery_only"
    evidence_status: str = "DISCOVERY_ONLY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FeedEventCluster:
    id: str
    canonical_event: str
    published_at: str
    related_entities: List[str]
    locations: List[str]
    items: List[FeedItem]
    source_count: int
    source_diversity: int
    lineage_roots: List[str] = field(default_factory=list)
    lineage_method: str = "conservative_headline_and_byline_heuristic"
    corroboration: str = "DISCOVERY_ONLY"
    conflicting_claims: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "items": [item.to_dict() for item in self.items],
        }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def _safe_link(value: str) -> str:
    value = html.unescape((value or "").strip())
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return value


def _clean_text(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    value = " ".join(part.strip() for part in element.itertext() if part and part.strip())
    value = html.unescape(value)
    value = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _children(element: ET.Element, name: str) -> List[ET.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _first_child(element: ET.Element, *names: str) -> Optional[ET.Element]:
    wanted = {name.lower() for name in names}
    for child in list(element):
        if _local_name(child.tag) in wanted:
            return child
    return None


def _first_text(element: ET.Element, *names: str) -> str:
    return _clean_text(_first_child(element, *names))


def _all_descendants(element: ET.Element, name: str) -> List[ET.Element]:
    return [node for node in element.iter() if node is not element and _local_name(node.tag) == name]


def _media_type(mime: str, url: str) -> str:
    mime = (mime or "").lower()
    if mime.startswith("image/") or re.search(r"\.(?:jpe?g|png|gif|webp|avif)(?:$|\?)", url, re.I):
        return "image"
    if mime.startswith("video/") or re.search(r"\.(?:mp4|mov|webm|m4v)(?:$|\?)", url, re.I):
        return "video"
    if mime.startswith("audio/") or re.search(r"\.(?:mp3|m4a|ogg|wav)(?:$|\?)", url, re.I):
        return "audio"
    return "unknown"


def parse_feed(
    payload: bytes,
    source: FeedSource,
    *,
    max_items: int = 50,
) -> List[FeedItem]:
    """Parse RSS 2.0, common RSS variants, RDF RSS, and Atom documents."""
    if not payload or len(payload) > MAX_FEED_BYTES:
        return []
    # ElementTree does not fetch external entities, but rejecting DTD/entity
    # declarations also avoids expansion payloads and ambiguous feed parsing.
    prefix = payload[: min(len(payload), 65536)].upper()
    if b"<!DOCTYPE" in prefix or b"<!ENTITY" in prefix:
        return []
    try:
        root = ET.fromstring(payload)
    except (ET.ParseError, ValueError):
        return []

    root_name = _local_name(root.tag)
    channel = _first_child(root, "channel") if root_name in {"rss", "rdf"} else None
    container = channel or root
    item_nodes = _children(container, "item")
    if not item_nodes:
        item_nodes = _children(root, "entry")
    if not item_nodes and root_name in {"item", "entry"}:
        item_nodes = [root]

    parsed: List[FeedItem] = []
    for node in item_nodes[: min(max_items, MAX_FEED_ITEMS)]:
        title = _first_text(node, "title")
        if not title:
            continue
        link = ""
        for link_node in _children(node, "link"):
            href = link_node.attrib.get("href", "")
            rel = link_node.attrib.get("rel", "alternate")
            candidate = href or _clean_text(link_node)
            if candidate and (rel == "alternate" or not link):
                link = _safe_link(candidate)
                if rel == "alternate" and link:
                    break

        guid = _first_text(node, "guid", "id") or link
        description = _first_text(node, "description", "summary", "subtitle")
        content = _first_text(node, "encoded", "content", "content:encoded") or description
        published_at = _first_text(node, "pubdate", "published", "date")
        updated_at = _first_text(node, "updated", "modified")

        authors = []
        for author_node in _children(node, "author") + _children(node, "creator"):
            author = _clean_text(author_node)
            if not author:
                author = _first_text(author_node, "name", "email")
            if author and author not in authors:
                authors.append(author)
        if not authors:
            for author_node in _all_descendants(node, "author"):
                author = _first_text(author_node, "name") or _clean_text(author_node)
                if author and author not in authors:
                    authors.append(author)

        categories = []
        for category_node in _children(node, "category"):
            value = category_node.attrib.get("term", "") or _clean_text(category_node)
            if value and value not in categories:
                categories.append(value)

        images: List[str] = []
        enclosures: List[str] = []
        media_types: List[str] = []
        for media_node in _all_descendants(node, "thumbnail") + _all_descendants(node, "content") + _children(node, "enclosure"):
            url = _safe_link(media_node.attrib.get("url", "") or media_node.attrib.get("href", ""))
            mime = media_node.attrib.get("type", "")
            medium = media_node.attrib.get("medium", "")
            kind = _media_type(mime, url)
            if not url:
                continue
            if kind == "image" or medium.lower() == "image":
                if url not in images:
                    images.append(url)
            elif kind in {"video", "audio"}:
                if url not in enclosures:
                    enclosures.append(url)
                if kind not in media_types:
                    media_types.append(kind)
            elif _local_name(media_node.tag) == "enclosure":
                if url not in enclosures:
                    enclosures.append(url)
            if kind in {"image", "video", "audio"} and kind not in media_types:
                media_types.append(kind)

        # Some feeds place images inside HTML content instead of media RSS.
        for raw_url in re.findall(r"<img\b[^>]*\bsrc=[\"']([^\"']+)", content, flags=re.I):
            url = _safe_link(raw_url)
            if url and url not in images:
                images.append(url)

        parsed.append(FeedItem(
            source_id=source.id,
            source_name=source.name,
            feed_url=source.feed_url,
            title=title[:500],
            description=description[:4000],
            content=content[:16000],
            published_at=published_at[:120],
            updated_at=updated_at[:120],
            canonical_url=link,
            guid=guid[:1000],
            authors=authors[:20],
            categories=categories[:40],
            image_urls=images[:MAX_URLS_PER_ITEM],
            enclosure_urls=enclosures[:MAX_URLS_PER_ITEM],
            media_types=media_types,
            trust_tier=source.trust_tier,
            source_type=source.source_type,
            rights_policy=source.rights_policy,
        ))
    return parsed


class FeedRegistry:
    """Small configurable catalog with JSON and optional OPML ingestion."""

    def __init__(self, sources: Optional[Sequence[FeedSource]] = None):
        self.sources = list(sources or [])

    @classmethod
    def from_file(cls, path: Optional[Path] = None) -> "FeedRegistry":
        path = path or DEFAULT_REGISTRY
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("sources", [])
            sources = [FeedSource(**row) for row in rows if isinstance(row, dict) and row.get("id")]
            return cls(sources)
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Feed registry could not be loaded from %s: %s", path, exc)
            return cls()

    def enabled_sources(self, query: str = "") -> List[FeedSource]:
        enabled = [source for source in self.sources if source.enabled]
        if not query:
            return enabled
        tokens = {word for word in re.findall(r"[a-z0-9]+", query.lower()) if len(word) >= 3}
        if not tokens:
            return enabled
        matched = [s for s in enabled if tokens.intersection({tag.lower() for tag in s.tags + [s.category, s.region, s.country]})]
        # Keep at least general-news sources for a current-event request.
        general = [s for s in enabled if s.category.lower() in {"news", "general_news", "science", "research"}]
        result: List[FeedSource] = []
        seen_ids = set()
        for source in matched + general:
            if source.id not in seen_ids:
                seen_ids.add(source.id)
                result.append(source)
        return result

    def import_opml(self, payload: bytes, *, default_trust_tier: str = "S4") -> List[FeedSource]:
        """Parse OPML outline feeds into disabled-by-default source definitions."""
        if not payload or len(payload) > MAX_FEED_BYTES or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
            return []
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []
        imported = []
        for outline in root.iter():
            url = _safe_link(outline.attrib.get("xmlUrl", "") or outline.attrib.get("xmlurl", ""))
            if not url:
                continue
            name = outline.attrib.get("title") or outline.attrib.get("text") or urllib.parse.urlsplit(url).hostname or "Imported feed"
            source_id = "opml_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:48]
            imported.append(FeedSource(
                id=source_id or "opml_feed",
                name=name[:120], feed_url=url, route_type="direct", trust_tier=default_trust_tier,
                rights_policy="editorial_discovery_only", evidence_role="discovery_only", enabled=False,
            ))
        return imported

    def save_file(self, path: Optional[Path] = None) -> Path:
        """Persist the current registry as UTF-8 JSON."""
        path = path or DEFAULT_REGISTRY
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "description": "Curated, extensible RSS/Atom source catalog. Feed content is discovery only.",
                   "sources": [asdict(source) for source in self.sources]}
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_path.replace(path)
        return path

    def import_opml_to_file(
        self,
        payload: bytes,
        *,
        path: Optional[Path] = None,
        default_trust_tier: str = "S4",
    ) -> List[FeedSource]:
        """Merge OPML feeds into a registry with imported rows disabled by default."""
        imported = self.import_opml(payload, default_trust_tier=default_trust_tier)
        by_id = {source.id: source for source in self.sources}
        for source in imported:
            # A repeated OPML import updates the same disabled entry, never
            # silently enabling a newly supplied feed URL.
            by_id.setdefault(source.id, source)
        self.sources = list(by_id.values())
        self.save_file(path)
        return imported


def _is_safe_public_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
    except ValueError:
        # Prevent public-looking hostnames that resolve into local services.
        try:
            addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme.lower() == "https" else 80))
        except OSError:
            return False
        if not addresses:
            return False
        for address in addresses:
            resolved = address[4][0].split("%", 1)[0]
            try:
                resolved_ip = ipaddress.ip_address(resolved)
            except ValueError:
                return False
            if (
                resolved_ip.is_private or resolved_ip.is_loopback or resolved_ip.is_link_local
                or resolved_ip.is_multicast or resolved_ip.is_reserved or resolved_ip.is_unspecified
            ):
                return False
    return True


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urljoin(req.full_url, newurl)
        if not _is_safe_public_url(target):
            raise urllib.error.HTTPError(target, code, "Unsafe feed redirect", headers, fp)
        if urllib.parse.urlsplit(req.full_url).scheme == "https" and urllib.parse.urlsplit(target).scheme != "https":
            raise urllib.error.HTTPError(target, code, "Refusing HTTPS downgrade", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, target)


class RSSHTTPClient:
    """Bounded HTTP client with in-memory caching and polite transient retries."""

    def __init__(
        self,
        *,
        timeout: float = 8.0,
        cache_ttl_seconds: int = 900,
        max_bytes: int = MAX_FEED_BYTES,
        max_attempts: int = 2,
        opener: Optional[Any] = None,
        sleep_func: Callable[[float], None] = time.sleep,
    ):
        self.timeout = timeout
        self.cache_ttl_seconds = max(0, cache_ttl_seconds)
        self.max_bytes = min(max_bytes, MAX_FEED_BYTES)
        self.max_attempts = max(1, max_attempts)
        self.opener = opener or urllib.request.build_opener(_SafeRedirectHandler())
        self.sleep_func = sleep_func
        self._cache: Dict[str, Tuple[float, bytes, Dict[str, str]]] = {}
        self._cache_lock = threading.RLock()

    def fetch(self, url: str) -> Optional[Tuple[bytes, Dict[str, str]]]:
        if not _is_safe_public_url(url):
            logger.warning("Rejected unsafe feed URL: %s", url)
            return None
        key = url.strip()
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached and cached[0] > now:
                return cached[1], dict(cached[2])
            if cached:
                self._cache.pop(key, None)

        for attempt in range(self.max_attempts):
            req = urllib.request.Request(key, headers={"User-Agent": _USER_AGENT, "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.5"})
            try:
                response = self.opener.open(req, timeout=self.timeout)
                with response:
                    payload = response.read(self.max_bytes + 1)
                    headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
                if len(payload) > self.max_bytes:
                    logger.warning("Feed response exceeded the %d byte limit: %s", self.max_bytes, key)
                    return None
                with self._cache_lock:
                    self._cache[key] = (time.monotonic() + self.cache_ttl_seconds, payload, headers)
                return payload, headers
            except urllib.error.HTTPError as exc:
                if attempt + 1 >= self.max_attempts or exc.code not in {429, 500, 502, 503, 504}:
                    logger.info("Feed fetch failed (%s): HTTP %s", key, exc.code)
                    return None
                retry_after = self._retry_after(exc.headers.get("Retry-After") if exc.headers else None)
                self.sleep_func(retry_after if retry_after is not None else min(0.25 * (2 ** attempt), 2.0))
            except Exception as exc:
                if attempt + 1 >= self.max_attempts:
                    logger.info("Feed fetch failed (%s): %s", key, exc)
                    return None
                self.sleep_func(min(0.25 * (2 ** attempt), 2.0))
        return None

    @staticmethod
    def _retry_after(value: Optional[str]) -> Optional[float]:
        if not value:
            return None
        try:
            return max(0.0, min(30.0, float(value)))
        except ValueError:
            try:
                date = email.utils.parsedate_to_datetime(value)
                return max(0.0, min(30.0, (date - datetime.now(date.tzinfo or timezone.utc)).total_seconds()))
            except Exception:
                return None


class DirectRSSAdapter:
    def __init__(self, client: Optional[RSSHTTPClient] = None):
        self.client = client or RSSHTTPClient()

    def fetch(self, source: FeedSource, *, max_items: int = 50) -> List[FeedItem]:
        result = self.client.fetch(source.feed_url)
        return parse_feed(result[0], source, max_items=max_items) if result else []


class RSSHubAdapter(DirectRSSAdapter):
    """Optional RSSHub route adapter; no public RSSHub instance is assumed."""

    def __init__(self, base_url: str = "", client: Optional[RSSHTTPClient] = None):
        super().__init__(client)
        self.base_url = (base_url or "").rstrip("/")

    def fetch(self, source: FeedSource, *, max_items: int = 50) -> List[FeedItem]:
        if not self.base_url or not source.rsshub_route:
            return []
        route = source.rsshub_route.lstrip("/")
        routed_source = FeedSource(**{**asdict(source), "feed_url": f"{self.base_url}/{route}"})
        return super().fetch(routed_source, max_items=max_items)


class RSSDiscoveryService:
    """Fetch dynamic topic feeds and a bounded set of matching curated sources."""

    def __init__(
        self,
        registry: Optional[FeedRegistry] = None,
        direct_adapter: Optional[DirectRSSAdapter] = None,
        rsshub_adapter: Optional[RSSHubAdapter] = None,
        dynamic_base_url: str = "https://news.google.com/rss/search",
        max_sources: int = RSS_MAX_SOURCES_PER_QUERY,
        rsshub_base_url: Optional[str] = None,
        rsshub_fallback_url: Optional[str] = None,
    ):
        self.registry = registry or FeedRegistry.from_file(RSS_FEED_REGISTRY_PATH)
        client = RSSHTTPClient(
            timeout=RSS_FETCH_TIMEOUT_SECONDS,
            cache_ttl_seconds=RSS_CACHE_TTL_SECONDS,
            max_bytes=RSS_MAX_FEED_BYTES,
        )
        self.direct = direct_adapter or DirectRSSAdapter(client)
        self.rsshub = rsshub_adapter or RSSHubAdapter(rsshub_base_url if rsshub_base_url is not None else RSSHUB_BASE_URL, client)
        self.rsshub_fallback = RSSHubAdapter(rsshub_fallback_url if rsshub_fallback_url is not None else RSSHUB_FALLBACK_URL, client)
        self.dynamic_base_url = dynamic_base_url
        self.max_sources = max(1, min(10, max_sources))

    def discover(self, query: str, *, max_items: int = 25, language: str = "id", country: str = "ID") -> List[FeedItem]:
        if not RSS_DISCOVERY_ENABLED or not query or not query.strip():
            return []
        sources: List[FeedSource] = []
        dynamic_url = self._dynamic_url(query.strip(), language, country)
        sources.append(FeedSource(
            id="google_news_query", name="Google News RSS (discovery)", feed_url=dynamic_url,
            region="international", country=country, language=language, category="news",
            source_type="news_aggregator", trust_tier="S4", rights_policy="editorial_discovery_only",
        ))
        sources.extend(self.registry.enabled_sources(query)[: self.max_sources - 1])

        all_items: List[FeedItem] = []
        for source in sources[: self.max_sources]:
            try:
                if source.route_type == "rsshub":
                    items = self.rsshub.fetch(source, max_items=max_items)
                    if not items:
                        items = self.rsshub_fallback.fetch(source, max_items=max_items)
                else:
                    items = self.direct.fetch(source, max_items=max_items)
                all_items.extend(items)
            except Exception as exc:
                logger.info("RSS source %s failed and was skipped: %s", source.id, exc)
        deduped = self._deduplicate(all_items)
        return deduped[: max(1, min(max_items, 100))]

    def fetch_custom(self, feed_url: str, *, name: str = "User feed", max_items: int = 50) -> List[FeedItem]:
        safe_url = _safe_link(feed_url)
        if not safe_url or not _is_safe_public_url(safe_url):
            return []
        source = FeedSource(
            id="user_feed", name=name[:120], feed_url=safe_url,
            source_type="user_supplied_feed", trust_tier="S7",
            rights_policy="editorial_discovery_only", evidence_role="discovery_only",
        )
        return self.direct.fetch(source, max_items=max_items)

    def _dynamic_url(self, query: str, language: str, country: str) -> str:
        region = (country or "ID").upper()[:2]
        lang = (language or "id").lower()[:5]
        params = urllib.parse.urlencode({"q": query, "hl": lang, "gl": region, "ceid": f"{region}:{lang}"})
        return f"{self.dynamic_base_url}?{params}"

    @staticmethod
    def _deduplicate(items: Iterable[FeedItem]) -> List[FeedItem]:
        seen_urls = set()
        result = []
        for item in items:
            url_key = item.canonical_url.rstrip("/").lower()
            if url_key and url_key in seen_urls:
                continue
            if url_key:
                seen_urls.add(url_key)
            result.append(item)
        return result


def _source_domain(item: FeedItem) -> str:
    host = urllib.parse.urlsplit(item.canonical_url).hostname or item.source_id
    return host.lower().removeprefix("www.")


def _headline_lineage(item: FeedItem) -> str:
    """Estimate syndicated lineage conservatively from explicit markers/bylines."""
    text = f"{item.title} {item.description} {item.content}".lower()
    wire_markers = {
        "reuters": ("reuters",),
        "associated_press": ("associated press", "ap news", "ap photo"),
        "afp": ("agence france-presse", "afp"),
    }
    for wire, markers in wire_markers.items():
        if any(marker in text for marker in markers):
            return f"wire:{wire}"
    authors = sorted({re.sub(r"[^a-z0-9]+", " ", author.lower()).strip() for author in item.authors if author.strip()})
    normalized_title = re.sub(r"[^a-z0-9]+", " ", item.title.lower()).strip()
    if authors:
        return f"byline:{authors[0]}:{normalized_title}"
    return f"headline:{normalized_title}"


def _headline_conflicts(group: Sequence[FeedItem]) -> List[str]:
    conflicts: List[str] = []
    directions = {
        "up": ("rise", "rises", "rose", "increase", "increases", "increased", "naik", "meningkat", "melonjak"),
        "down": ("fall", "falls", "fell", "decrease", "decreases", "decreased", "turun", "menurun", "merosot"),
    }
    observed = set()
    numeric = {}
    for item in group:
        title = item.title.lower()
        for direction, cues in directions.items():
            if any(cue in title for cue in cues):
                observed.add(direction)
        for value, unit in re.findall(r"\b(\d+(?:[.,]\d+)?)\s*(%|percent|juta|million|billion|units?|people|cases?)\b", title):
            numeric.setdefault(unit, set()).add(value.replace(",", "."))
    if len(observed) > 1:
        conflicts.append("Headlines use opposite increase/decrease language; verify against primary sources.")
    for unit, values in numeric.items():
        if len(values) > 1:
            conflicts.append(f"Headlines contain differing numeric values for unit '{unit}'; verify against primary sources.")
            break
    return conflicts


def cluster_feed_items(items: Sequence[FeedItem]) -> List[FeedEventCluster]:
    """Cluster near-identical headlines without treating syndication as corroboration."""
    clusters: List[List[FeedItem]] = []
    for item in items:
        normalized = re.sub(r"[^a-z0-9]+", " ", item.title.lower()).strip()
        target = None
        for group in clusters:
            representative = re.sub(r"[^a-z0-9]+", " ", group[0].title.lower()).strip()
            if normalized == representative or SequenceMatcher(None, normalized, representative).ratio() >= 0.84:
                target = group
                break
        if target is None:
            clusters.append([item])
        else:
            target.append(item)
    results: List[FeedEventCluster] = []
    for index, group in enumerate(clusters, 1):
        title = group[0].title
        sources = sorted({_source_domain(item) for item in group})
        roots = sorted({_headline_lineage(item) for item in group})
        published = min((item.published_at for item in group if item.published_at), default="")
        entities = sorted({entity for item in group for entity in re.findall(r"\b[A-Z][\w-]{2,}(?:\s+[A-Z][\w-]{2,})*", item.title)})
        locations = sorted({match.group(1) for item in group for match in re.finditer(r"\b(?:in|at|near|di|ke|dari)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})", item.title)})
        results.append(FeedEventCluster(
            id=f"event_{index:03d}", canonical_event=title,
            published_at=published, related_entities=entities,
            locations=locations, items=list(group), source_count=len(sources), source_diversity=len(roots),
            lineage_roots=roots,
            corroboration="DISCOVERY_ONLY",
            conflicting_claims=_headline_conflicts(group),
        ))
    return results
