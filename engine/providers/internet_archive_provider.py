"""
engine/providers/internet_archive_provider.py
=============================================
Internet Archive (archive.org) media search provider.

Uses public Archive.org search API — no API key required.

Key endpoints:
  https://archive.org/advancedsearch.php  → search items by query + mediatype
  https://archive.org/metadata/{id}       → full item metadata + file list
  https://archive.org/download/{id}/      → file download root

Historical footage is prioritised: when searching for video/any,
the provider queries with mediatype:movies first.

License metadata is stored as-is in MediaItem.license.
It is NEVER used to filter or reject download candidates.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from engine.config import INTERNET_ARCHIVE_API_URL
from engine.providers.media import MediaItem, MediaProvider

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "NugiContentBrain/1.0 (nugi-konten-kreator; general-purpose-media-retrieval)"
)
_REQUEST_TIMEOUT = 3  # seconds (fail fast if IA is sluggish or blocked)

# Preferred downloadable video formats (in priority order)
_PREFERRED_VIDEO_EXTS = [".mp4", ".ogv", ".webm", ".avi", ".mov", ".mpg", ".mpeg"]
_PREFERRED_IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"]


def _ia_get(url: str) -> Optional[Dict[str, Any]]:
    """
    GET request to archive.org, return parsed JSON or None.
    Never raises — errors are logged.
    """
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            # Enforce read timeout on the underlying socket so chunked reads cannot stall
            try:
                if hasattr(resp, "fp") and resp.fp and hasattr(resp.fp, "raw") and resp.fp.raw:
                    sock = getattr(resp.fp.raw, "_sock", None)
                    if sock and hasattr(sock, "settimeout"):
                        sock.settimeout(_REQUEST_TIMEOUT)
            except Exception:
                pass
            raw_data = resp.read()
            return json.loads(raw_data.decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning(f"Internet Archive request failed: {e}")
    except Exception as e:
        logger.warning(f"Internet Archive unexpected error: {e}")
    return None


def _build_search_url(
    query: str,
    mediatype: str,
    rows: int,
    fields: List[str]
) -> str:
    """Build an archive.org advancedsearch URL."""
    params = {
        "q": query,
        "fl[]": ",".join(fields),
        "rows": str(rows),
        "output": "json",
        "page": "1",
    }
    if mediatype:
        params["q"] = f"({query}) AND mediatype:{mediatype}"
    return (
        f"{INTERNET_ARCHIVE_API_URL}/advancedsearch.php?"
        + urllib.parse.urlencode(params)
    )


class InternetArchiveProvider(MediaProvider):
    """
    Searches Internet Archive for images, video, and historical footage.
    No API key required. Returns empty list on errors — never raises.

    Prioritises historical/archival results when query suggests history.
    """

    PROVIDER_NAME = "internet_archive"

    def __init__(self, base_url: str = INTERNET_ARCHIVE_API_URL):
        self.base_url = base_url.rstrip("/")
        self._is_available: bool = True

    @property
    def is_available(self) -> bool:
        return self._is_available

    @is_available.setter
    def is_available(self, val: bool) -> None:
        self._is_available = val

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
        Search Internet Archive for media matching query.

        Strategy:
          - media_type="video" → search mediatype:movies
          - media_type="image" → search mediatype:image
          - media_type="any"   → search both, deduplicate by id
        """
        if not self._is_available or not query.strip():
            return []

        items: List[MediaItem] = []
        seen_ids: set = set()

        if media_type in ("video", "any"):
            video_items = self._search_by_mediatype(query, "movies", max_results)
            for item in video_items:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    items.append(item)

        if not self._is_available:
            return items

        if media_type in ("image", "any"):
            image_items = self._search_by_mediatype(query, "image", max_results)
            for item in image_items:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    items.append(item)

        return items[:max_results]

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        """Fetch metadata for a specific Archive.org identifier."""
        if not self._is_available:
            return None
        return self._fetch_item_metadata(item_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _search_by_mediatype(
        self, query: str, mediatype: str, limit: int
    ) -> List[MediaItem]:
        """Run one search for a specific IA mediatype."""
        if not self._is_available:
            return []
        fields = [
            "identifier", "title", "description", "creator",
            "date", "subject", "licenseurl", "mediatype",
        ]
        url = _build_search_url(query, mediatype, limit, fields)
        data = _ia_get(url)
        if not data:
            self._is_available = False
            return []

        docs = data.get("response", {}).get("docs", [])
        items: List[MediaItem] = []
        for doc in docs[:max(1, limit)]:
            item = self._doc_to_media_item(doc, mediatype)
            if item:
                items.append(item)
        return items

    def _doc_to_media_item(
        self, doc: Dict[str, Any], mediatype_hint: str
    ) -> Optional[MediaItem]:
        """
        Convert a search result doc to MediaItem.
        We do a lightweight metadata fetch to get the best download URL.
        """
        identifier = doc.get("identifier", "")
        if not identifier:
            return None

        title = str(doc.get("title", identifier))
        description = str(doc.get("description", ""))
        creator_raw = doc.get("creator", "")
        creator = (
            ", ".join(creator_raw)
            if isinstance(creator_raw, list)
            else str(creator_raw)
        )[:200]
        date = str(doc.get("date", ""))[:50]
        subjects = doc.get("subject", [])
        subject_str = (
            ", ".join(subjects) if isinstance(subjects, list) else str(subjects)
        )
        license_url = str(doc.get("licenseurl", ""))

        # Determine media_type from mediatype hint
        ia_mediatype = str(doc.get("mediatype", mediatype_hint))
        if ia_mediatype in ("movies", "video"):
            media_type = "video"
        elif ia_mediatype == "image":
            media_type = "image"
        elif ia_mediatype == "audio":
            media_type = "audio"
        else:
            media_type = "document"

        source_url = f"{self.base_url}/details/{identifier}"
        thumb_url = f"{self.base_url}/services/img/{identifier}"

        # Resolve a concrete downloadable file
        download_url, file_size = self._resolve_download_file(
            identifier, media_type
        )
        if not download_url:
            # No downloadable file found — still include as searchable result
            download_url = f"{self.base_url}/download/{identifier}/"

        return MediaItem(
            provider=self.PROVIDER_NAME,
            id=identifier,
            title=title[:300],
            description=description[:600],
            media_type=media_type,
            source_url=source_url,
            download_url=download_url,
            thumbnail_url=thumb_url,
            creator=creator,
            date=date,
            license=license_url,
            file_size_bytes=file_size,
            metadata={
                "ia_mediatype": ia_mediatype,
                "subjects": subject_str,
            },
        )

    def _fetch_item_metadata(self, identifier: str) -> Optional[MediaItem]:
        """Fetch full IA item metadata and return as MediaItem."""
        url = f"{self.base_url}/metadata/{identifier}"
        data = _ia_get(url)
        if not data:
            return None

        meta = data.get("metadata", {})
        files = data.get("files", [])

        title = str(meta.get("title", identifier))
        description = str(meta.get("description", ""))
        creator_raw = meta.get("creator", "")
        creator = (
            ", ".join(creator_raw)
            if isinstance(creator_raw, list)
            else str(creator_raw)
        )[:200]
        date = str(meta.get("date", ""))[:50]
        license_url = str(meta.get("licenseurl", ""))
        ia_mediatype = str(meta.get("mediatype", ""))

        if ia_mediatype in ("movies", "video"):
            media_type = "video"
        elif ia_mediatype == "image":
            media_type = "image"
        else:
            media_type = "document"

        download_url, file_size = self._pick_best_file(files, media_type)
        source_url = f"{self.base_url}/details/{identifier}"
        thumb_url = f"{self.base_url}/services/img/{identifier}"

        if not download_url:
            download_url = f"{self.base_url}/download/{identifier}/"

        return MediaItem(
            provider=self.PROVIDER_NAME,
            id=identifier,
            title=title[:300],
            description=description[:600],
            media_type=media_type,
            source_url=source_url,
            download_url=download_url,
            thumbnail_url=thumb_url,
            creator=creator,
            date=date,
            license=license_url,
            file_size_bytes=file_size,
            metadata={"ia_mediatype": ia_mediatype},
        )

    def _resolve_download_file(
        self, identifier: str, media_type: str
    ) -> Tuple[str, int]:
        """
        Fetch /metadata/{identifier} and pick best downloadable file.
        Returns (download_url, file_size_bytes) — ("", 0) on failure.
        """
        url = f"{self.base_url}/metadata/{identifier}"
        data = _ia_get(url)
        if not data:
            return "", 0
        files = data.get("files", [])
        return self._pick_best_file(files, media_type)

    def _pick_best_file(
        self, files: List[Dict], media_type: str
    ) -> Tuple[str, int]:
        """
        From an IA item's file list, pick the best downloadable file.

        Selection strategy:
        - Prefer the appropriate format based on media_type.
        - For video: prefer mp4 > ogv > webm > others.
        - For image: prefer jpg > png > others.
        - Among equal-format matches, prefer SMALLER file (avoid huge raw files).
        - Excludes metadata/index files (xml, sqlite, etc.).
        """
        preferred_exts = (
            _PREFERRED_VIDEO_EXTS if media_type == "video"
            else _PREFERRED_IMAGE_EXTS
        )

        candidates: List[Tuple[int, int, str, int]] = []
        # (priority_rank, size, name, size_bytes)

        for f in files:
            name = f.get("name", "")
            size_str = f.get("size", "0")
            try:
                size_bytes = int(size_str)
            except (ValueError, TypeError):
                size_bytes = 0

            lower = name.lower()
            # Skip metadata/text/derivative files
            if any(lower.endswith(ext) for ext in [
                ".xml", ".sqlite", ".torrent", ".gz", ".zip",
                "_meta.txt", "_files.xml", "_reviews.xml",
            ]):
                continue

            for rank, ext in enumerate(preferred_exts):
                if lower.endswith(ext):
                    candidates.append((rank, size_bytes, name, size_bytes))
                    break

        if not candidates:
            return "", 0

        # Sort by priority rank ASC, then size ASC (prefer smaller files)
        candidates.sort(key=lambda x: (x[0], x[1]))
        best = candidates[0]
        best_name = best[2]

        # The identifier is embedded in self via the caller context, but since
        # this is a static helper, we need the caller to build the URL.
        # We return only the filename; the caller builds the full URL.
        return best_name, best[3]

    def _resolve_download_file(  # noqa: F811 — intentional override
        self, identifier: str, media_type: str
    ) -> Tuple[str, int]:
        """
        Fetch /metadata/{identifier} and pick best downloadable file.
        Returns full download URL and file size.
        """
        url = f"{self.base_url}/metadata/{identifier}"
        data = _ia_get(url)
        if not data:
            return "", 0
        files = data.get("files", [])
        filename, size = self._pick_best_file(files, media_type)
        if not filename:
            return "", 0
        download_url = f"{self.base_url}/download/{identifier}/{urllib.parse.quote(filename)}"
        return download_url, size
