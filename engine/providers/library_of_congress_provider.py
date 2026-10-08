"""Free public Library of Congress digital-collection search adapter."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from engine.config import MEDIA_SEARCH_MAX_RESULTS
from engine.providers.media import MediaItem, MediaProvider

logger = logging.getLogger(__name__)


class LibraryOfCongressProvider(MediaProvider):
    """Search the public loc.gov JSON API; rights advisories remain per-item."""

    PROVIDER_NAME = "loc"
    API_URL = "https://www.loc.gov/search/"
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024

    def __init__(self, timeout: float = 10.0, requests_per_minute: int = 20):
        self.timeout = timeout
        self.min_interval = 60.0 / max(1, requests_per_minute)
        self._last_request = 0.0
        self._cooldown_until = 0.0

    def search_media(self, query: str, media_type: str = "any", max_results: int = MEDIA_SEARCH_MAX_RESULTS) -> List[MediaItem]:
        if media_type not in {"any", "image", "photo", ""} or time.monotonic() < self._cooldown_until:
            return []
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        params = urllib.parse.urlencode({"q": query, "fo": "json", "c": max(1, min(max_results, 20)), "at": "results"})
        req = urllib.request.Request(
            f"{self.API_URL}?{params}",
            headers={"User-Agent": "NugiContentIntelligence/1.0", "Accept": "application/json"},
        )
        self._last_request = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            if len(raw) > self.MAX_RESPONSE_BYTES:
                logger.warning("LOC response exceeded size limit")
                return []
            data = json.loads(raw.decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                try:
                    retry_after = float(exc.headers.get("Retry-After", "60"))
                except (ValueError, TypeError):
                    retry_after = 60.0
                self._cooldown_until = time.monotonic() + max(1.0, min(retry_after, 3600.0))
                logger.info("LOC rate limited; provider placed in cooldown")
            else:
                logger.info("LOC search failed with HTTP %s", exc.code)
            return []
        except Exception as exc:
            logger.info("LOC search failed: %s", exc)
            return []

        results = data.get("results", []) if isinstance(data, dict) else []
        items = []
        for row in results[:max_results]:
            item = self._to_media_item(row)
            if item:
                items.append(item)
        return items

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        url = item_id if item_id.startswith("https://www.loc.gov/item/") else f"https://www.loc.gov/item/{urllib.parse.quote(item_id.strip('/'))}/"
        if urllib.parse.urlsplit(url).hostname != "www.loc.gov":
            return None
        req = urllib.request.Request(f"{url}?fo=json&at=item", headers={"User-Agent": "NugiContentIntelligence/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            if len(raw) > self.MAX_RESPONSE_BYTES:
                return None
            data = json.loads(raw.decode("utf-8", errors="replace"))
            return self._to_media_item(data.get("item", {}), item_url=url)
        except Exception as exc:
            logger.debug("LOC item metadata lookup failed: %s", exc)
            return None

    def _to_media_item(self, row: Dict[str, Any], item_url: str = "") -> Optional[MediaItem]:
        if not isinstance(row, dict):
            return None
        image_urls = row.get("image_url") or row.get("image_urls") or []
        if isinstance(image_urls, str):
            image_urls = [image_urls]
        image_url = next((url for url in image_urls if isinstance(url, str) and url.startswith("https://")), "")
        if not image_url:
            return None
        source_url = row.get("id") or item_url
        if source_url.startswith("http://www.loc.gov/"):
            source_url = "https://" + source_url[len("http://"):]
        if not source_url.startswith("https://www.loc.gov/"):
            return None
        title = str(row.get("title") or row.get("item", {}).get("title") or "Library of Congress item")
        descriptions = row.get("description") or row.get("abstract") or []
        description = " ".join(str(value) for value in descriptions) if isinstance(descriptions, list) else str(descriptions)
        creator = row.get("contributor") or row.get("contributors") or row.get("creator") or ""
        if isinstance(creator, list):
            creator = ", ".join(str(value) for value in creator[:4])
        rights = row.get("rights_advisory") or row.get("rights_information") or row.get("rights") or []
        if isinstance(rights, list):
            rights = " ".join(str(value) for value in rights)
        subjects = row.get("subject") or row.get("subjects") or []
        if isinstance(subjects, list):
            subjects = [str(value) for value in subjects[:30]]
        return MediaItem(
            provider=self.PROVIDER_NAME,
            id=source_url,
            title=title[:300],
            description=description[:2000],
            media_type="image",
            source_url=source_url,
            download_url=image_url,
            thumbnail_url=image_url,
            creator=str(creator)[:300],
            date=str(row.get("date") or "")[:120],
            license="",
            rights_status="UNKNOWN",
            metadata={
                "rights_advisory": str(rights)[:1000],
                "subjects": subjects,
                "rights_policy": "discovery_only_unless_explicit_license_is_reusable",
            },
        )
