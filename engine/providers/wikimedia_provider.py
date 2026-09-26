"""
engine/providers/wikimedia_provider.py
=======================================
Wikimedia Commons media search provider.

Uses the public MediaWiki Action API — no API key required.
Endpoint: https://commons.wikimedia.org/w/api.php

Key API actions used:
  action=query&list=search&srnamespace=6   → full-text file search
  action=query&prop=imageinfo&iiprop=...   → metadata + download URL

License information is stored as-is in MediaItem.license.
It is NEVER used to filter or reject download candidates.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from engine.config import WIKIMEDIA_API_URL
from engine.providers.media import MediaItem, MediaProvider

logger = logging.getLogger(__name__)

# Request headers — identify ourselves politely per Wikimedia API etiquette
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 (compatible; NugiContentBrain/1.0; +https://github.com/nugiwabot/nugi-konten-kreator)"
)
_REQUEST_TIMEOUT = 15  # seconds


def _api_get(params: Dict[str, str], retry_on_429: bool = True) -> Optional[Dict[str, Any]]:
    """
    Make a GET request to the Wikimedia Commons API.
    Returns parsed JSON dict or None on error.
    Never raises — errors are logged and swallowed.
    """
    import time

    params["format"] = "json"
    params["formatversion"] = "2"
    url = f"{WIKIMEDIA_API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429 and retry_on_429:
            logger.warning("Wikimedia 429 rate limit hit. Backing off 2.0s...")
            time.sleep(2.0)
            return _api_get(params, retry_on_429=False)
        logger.warning(f"Wikimedia API HTTP {e.code} for params={params}")
    except urllib.error.URLError as e:
        logger.warning(f"Wikimedia API URL error: {e.reason}")
    except Exception as e:
        logger.warning(f"Wikimedia API unexpected error: {e}")
    return None


def _extract_license(extmetadata: Dict) -> str:
    """
    Extract license string from extmetadata dict.
    Returns empty string if not available.
    """
    license_val = extmetadata.get("License", {})
    if isinstance(license_val, dict):
        return license_val.get("value", "")
    return str(license_val) if license_val else ""


def _extract_creator(extmetadata: Dict) -> str:
    """Extract creator/author from extmetadata, stripping HTML tags."""
    import re
    artist = extmetadata.get("Artist", {})
    val = artist.get("value", "") if isinstance(artist, dict) else str(artist)
    # Strip simple HTML tags
    val = re.sub(r"<[^>]+>", "", val).strip()
    return val[:200]


def _extract_date(extmetadata: Dict) -> str:
    """Extract date from extmetadata."""
    date_field = extmetadata.get("DateTimeOriginal", extmetadata.get("DateTime", {}))
    val = date_field.get("value", "") if isinstance(date_field, dict) else str(date_field)
    return (val or "")[:50]


def _extract_description(extmetadata: Dict, fallback: str = "") -> str:
    """Extract description from extmetadata, stripping HTML."""
    import re
    desc = extmetadata.get("ImageDescription", {})
    val = desc.get("value", "") if isinstance(desc, dict) else str(desc)
    val = re.sub(r"<[^>]+>", "", val).strip()
    return val[:600] if val else fallback[:600]


class WikimediaProvider(MediaProvider):
    """
    Searches Wikimedia Commons for images and video via MediaWiki API.
    No API key required. Fallback-safe: returns empty list on errors.
    """

    PROVIDER_NAME = "wikimedia"

    def __init__(self, api_url: str = WIKIMEDIA_API_URL):
        self.api_url = api_url

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search_media(
        self,
        query: str,
        media_type: str = "any",
        max_results: int = 20
    ) -> List[MediaItem]:
        """
        Search Wikimedia Commons files matching query.

        Args:
            query: Search string (English works best on Commons).
            media_type: "image" | "video" | "any"
            max_results: Cap on returned items (max 50 per Wikimedia API page).

        Returns:
            List[MediaItem] — empty on error or no results.
        """
        if not query.strip():
            return []

        titles = self._search_titles(query, max_results)
        if not titles:
            logger.info(f"Wikimedia: no results for '{query}'")
            return []

        items = self._fetch_imageinfo_batch(titles)

        # Filter by media_type: only return visual media (images/videos)
        if media_type == "image":
            items = [i for i in items if i.media_type == "image"]
        elif media_type == "video":
            items = [i for i in items if i.media_type == "video"]
        else:
            items = [i for i in items if i.media_type in ("image", "video")]

        return items[:max_results]

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        """
        Fetch metadata for a specific Wikimedia Commons file title.
        item_id should be the file page title, e.g. "File:D-Day_Normandy_1944.jpg"
        """
        items = self._fetch_imageinfo_batch([item_id])
        return items[0] if items else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _search_titles(self, query: str, limit: int) -> List[str]:
        """
        Stage 1: Full-text search in File namespace (ns=6).
        Returns list of page titles like ["File:Einstein_1921.jpg", ...].
        """
        capped = min(limit, 50)  # Wikimedia API max srlimit=500 but we cap lower
        data = _api_get({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",   # File namespace
            "srlimit": str(capped),
            "srprop": "title",
        })
        if not data:
            return []
        results = data.get("query", {}).get("search", [])
        return [r["title"] for r in results if "title" in r]

    def _fetch_imageinfo_batch(self, titles: List[str]) -> List[MediaItem]:
        """
        Stage 2: Fetch imageinfo (URL, MIME, size, extmetadata) for title list.
        Processes in batches of 20 (Wikimedia API limit for prop=imageinfo).
        """
        items: List[MediaItem] = []
        batch_size = 20
        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]
            batch_items = self._fetch_batch(batch)
            items.extend(batch_items)
        return items

    def _fetch_batch(self, titles: List[str]) -> List[MediaItem]:
        """Fetch imageinfo for one batch of titles."""
        data = _api_get({
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata|mediatype",
            "iiurlwidth": "1280",   # Standard Wikimedia CDN thumbnail (cached, 1080p-ready, no 429)
            "iilimit": "1",
        })
        if not data:
            return []

        pages = data.get("query", {}).get("pages", [])
        # formatversion=2 returns list; v1 returns dict — handle both
        if isinstance(pages, dict):
            pages = list(pages.values())

        items: List[MediaItem] = []
        for page in pages:
            item = self._page_to_media_item(page)
            if item:
                items.append(item)
        return items

    def _page_to_media_item(self, page: Dict[str, Any]) -> Optional[MediaItem]:
        """Convert a single API page dict to a MediaItem."""
        title = page.get("title", "")
        if not title or page.get("missing"):
            return None

        imageinfo_list = page.get("imageinfo", [])
        if not imageinfo_list:
            return None

        info = imageinfo_list[0]
        url = info.get("url", "")
        if not url:
            return None  # No download URL → useless result

        mime = info.get("mime", "")
        media_type = self._mime_to_media_type(mime)

        # extmetadata contains rich provenance info
        extmeta = info.get("extmetadata", {})
        description = _extract_description(extmeta, fallback=title)
        creator = _extract_creator(extmeta)
        date = _extract_date(extmeta)
        license_str = _extract_license(extmeta)

        # Thumbnail URL (may be absent for non-image files)
        thumb_info = info.get("thumburl", "")

        source_url = (
            f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(title)}"
        )

        return MediaItem(
            provider=self.PROVIDER_NAME,
            id=title,
            title=title.removeprefix("File:"),
            description=description,
            media_type=media_type,
            source_url=source_url,
            download_url=url,
            thumbnail_url=thumb_info,
            creator=creator,
            date=date,
            license=license_str,
            file_size_bytes=info.get("size", 0),
            width=info.get("width", 0),
            height=info.get("height", 0),
            duration_seconds=0,  # Not available in imageinfo
            metadata={
                "mime": mime,
                "canonical_title": title,
            },
        )
