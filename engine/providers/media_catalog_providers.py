"""Bounded adapters for public visual-media catalog APIs.

These adapters preserve per-item attribution and rights data. A result is only
downloadable when its item-level rights classify as reusable; an API's general
availability is not treated as a license.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from engine.config import DPLA_API_KEY, DVIDS_API_KEY, EUROPEANA_API_KEY, MEDIA_SEARCH_MAX_RESULTS
from engine.providers.media import MediaItem, MediaProvider
from engine.providers.rights import classify_rights

logger = logging.getLogger(__name__)
_USER_AGENT = "NugiContentIntelligence/1.0 (media catalog metadata retrieval)"


def _https(value: Any) -> str:
    value = str(value or "").strip()
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return ""
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return value


def _rights_url(value: Any) -> str:
    """Preserve HTTP(S) rights URIs; catalog licenses commonly publish HTTP links."""
    value = str(value or "").strip()
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return value


class _CatalogProvider(MediaProvider):
    """Shared small-response HTTP, cache, retry, and cooldown behavior."""

    MAX_RESPONSE_BYTES = 2 * 1024 * 1024

    def __init__(self, *, timeout: float = 10.0, cache_ttl: int = 900):
        self.timeout = timeout
        self.cache_ttl = max(0, int(cache_ttl))
        self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._last_request = 0.0
        self._cooldown_until = 0.0

    def _json(self, url: str, *, min_interval: float = 0.0) -> Optional[Dict[str, Any]]:
        now = time.monotonic()
        if now < self._cooldown_until:
            return None
        cached = self._cache.get(url)
        if cached and cached[0] > now:
            return cached[1]
        if cached:
            self._cache.pop(url, None)
        wait = min_interval - (now - self._last_request)
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(url, headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        })
        self._last_request = time.monotonic()
        for attempt in range(2):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(payload) > self.MAX_RESPONSE_BYTES:
                    logger.info("%s response exceeded size limit", self.PROVIDER_NAME)
                    return None
                data = json.loads(payload.decode("utf-8", errors="replace"))
                if not isinstance(data, dict):
                    return None
                if self.cache_ttl:
                    if len(self._cache) >= 128:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[url] = (time.monotonic() + self.cache_ttl, data)
                return data
            except urllib.error.HTTPError as exc:
                if exc.code == 429 or exc.code in {503, 504}:
                    try:
                        retry = max(0.5, min(float(exc.headers.get("Retry-After", "2")), 60.0))
                    except (ValueError, TypeError, AttributeError):
                        retry = 2.0
                    self._cooldown_until = time.monotonic() + retry
                    if attempt == 0 and exc.code in {503, 504}:
                        time.sleep(min(retry, 2.0))
                        continue
                logger.info("%s request failed with HTTP %s", self.PROVIDER_NAME, exc.code)
                return None
            except Exception as exc:
                logger.info("%s request failed: %s", self.PROVIDER_NAME, exc)
                return None
        return None

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        return None


class OpenverseProvider(_CatalogProvider):
    """Search Openverse image records with their asset-level license fields."""

    PROVIDER_NAME = "openverse"
    API_URL = "https://api.openverse.org/v1/images/"

    def search_media(self, query: str, media_type: str = "any", max_results: int = MEDIA_SEARCH_MAX_RESULTS) -> List[MediaItem]:
        if not query.strip() or media_type == "video":
            return []
        params = urllib.parse.urlencode({"q": query[:300], "page_size": max(1, min(int(max_results), 20))})
        data = self._json(f"{self.API_URL}?{params}", min_interval=0.5)
        items = []
        for row in (data or {}).get("results", [])[:max_results]:
            if not isinstance(row, dict):
                continue
            source = _https(row.get("foreign_landing_url") or row.get("detail_url"))
            download = _https(row.get("url"))
            if not source or not download:
                continue
            license_name = str(row.get("license") or "").strip()
            license_url = _rights_url(row.get("license_url"))
            normalized_license = license_name.lower().replace("-", "_")
            status = {
                "cc0": "CC0", "pdm": "PUBLIC_DOMAIN", "by": "CC_BY", "by_sa": "CC_BY_SA",
            }.get(normalized_license, classify_rights(license_name=license_name, license_url=license_url))
            attribution = str(row.get("attribution") or "").strip()
            items.append(MediaItem(
                provider=self.PROVIDER_NAME, id=str(row.get("id") or source),
                title=str(row.get("title") or "Openverse image")[:300],
                description=str(row.get("description") or "")[:2000], media_type="image",
                source_url=source, download_url=download,
                thumbnail_url=_https(row.get("thumbnail")),
                creator=str(row.get("creator") or "")[:300], date="",
                license=license_name, license_url=license_url, rights_status=status,
                metadata={"attribution": attribution, "source": str(row.get("source") or ""),
                          "provider_rights_policy": "per_asset_openverse_license",
                          "width": row.get("width"), "height": row.get("height")},
                width=int(row.get("width") or 0), height=int(row.get("height") or 0),
            ))
        return items


class DPLAProvider(_CatalogProvider):
    """Digital Public Library of America search; an API key is required."""

    PROVIDER_NAME = "dpla"
    API_URL = "https://api.dp.la/v2/items"

    def __init__(self, api_key: str = DPLA_API_KEY, **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key.strip()

    def search_media(self, query: str, media_type: str = "any", max_results: int = MEDIA_SEARCH_MAX_RESULTS) -> List[MediaItem]:
        if not self.api_key or not query.strip() or media_type == "video":
            return []
        params = urllib.parse.urlencode({"q": query[:300], "page_size": max(1, min(int(max_results), 20)), "api_key": self.api_key})
        data = self._json(f"{self.API_URL}?{params}")
        items = []
        for wrapper in (data or {}).get("docs", [])[:max_results]:
            doc = wrapper.get("doc", wrapper) if isinstance(wrapper, dict) else {}
            if not isinstance(doc, dict):
                continue
            resource = doc.get("sourceResource") or {}
            views = doc.get("hasView") or []
            if isinstance(views, dict):
                views = [views]
            preview = _https(doc.get("object"))
            if not preview:
                preview = next((_https(v.get("@id") or v.get("id")) for v in views if isinstance(v, dict) and _https(v.get("@id") or v.get("id"))), "")
            source = _https(doc.get("isShownAt") or doc.get("@id"))
            if not source or not preview:
                continue
            rights_rows = resource.get("rights") or doc.get("rights") or []
            rights_text = "; ".join(str(v) for v in rights_rows) if isinstance(rights_rows, list) else str(rights_rows)
            license_url = next((_rights_url(v) for v in (rights_rows if isinstance(rights_rows, list) else [rights_rows]) if "creativecommons.org" in str(v).lower()), "")
            license_name = ""
            status = classify_rights(license_name=license_name, license_url=license_url, rights_statement=rights_text)
            creator = resource.get("creator") or []
            if isinstance(creator, list):
                creator = ", ".join(str(v.get("name", v)) if isinstance(v, dict) else str(v) for v in creator[:4])
            dates = resource.get("date") or []
            date = ", ".join(str(x) for x in dates[:3]) if isinstance(dates, list) else str(dates)
            title = resource.get("title") or doc.get("title") or "DPLA item"
            if isinstance(title, list):
                title = title[0] if title else "DPLA item"
            provider = doc.get("provider") or {}
            items.append(MediaItem(
                provider=self.PROVIDER_NAME, id=str(doc.get("id") or source), title=str(title)[:300],
                description=str(resource.get("description") or "")[:2000], media_type="image",
                source_url=source, download_url=preview, thumbnail_url=preview,
                creator=str(creator)[:300], date=date[:120], license=license_name,
                license_url=license_url, rights_status=status,
                metadata={"rights_statement": rights_text[:1200],
                          "provider_name": str(provider.get("name") or provider.get("@id") or "") if isinstance(provider, dict) else str(provider),
                          "rights_policy": "per_item_source_resource_and_view_rights"},
            ))
        return items


class EuropeanaProvider(_CatalogProvider):
    """Europeana Search API adapter; requires a free developer API key."""

    PROVIDER_NAME = "europeana"
    API_URL = "https://api.europeana.eu/record/v2/search.json"

    def __init__(self, api_key: str = EUROPEANA_API_KEY, **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key.strip()

    @staticmethod
    def _first(value: Any) -> str:
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value or "")

    def search_media(self, query: str, media_type: str = "any", max_results: int = MEDIA_SEARCH_MAX_RESULTS) -> List[MediaItem]:
        if not self.api_key or not query.strip() or media_type == "video":
            return []
        params = urllib.parse.urlencode({"query": query[:300], "wskey": self.api_key,
                                         "rows": max(1, min(int(max_results), 20)), "profile": "standard"})
        data = self._json(f"{self.API_URL}?{params}")
        items = []
        for row in (data or {}).get("items", [])[:max_results]:
            if not isinstance(row, dict):
                continue
            landing = self._first(row.get("edmIsShownAt"))
            source = _https(landing) or _https(row.get("guid"))
            direct = self._first(row.get("edmIsShownBy"))
            preview = self._first(row.get("edmPreview"))
            download = _https(direct) or _https(preview)
            if not source or not download:
                continue
            rights = self._first(row.get("edmRights"))
            status = classify_rights(license_url=rights, rights_statement=rights)
            title = self._first(row.get("title")) or "Europeana item"
            creator = self._first(row.get("dcCreator") or row.get("dcCreatorLangAware"))
            provider = self._first(row.get("dataProvider"))
            date = self._first(row.get("year")) or self._first(row.get("dcDate"))
            items.append(MediaItem(
                provider=self.PROVIDER_NAME, id=self._first(row.get("id")) or source,
                title=title[:300], description=self._first(row.get("dcDescription"))[:2000],
                media_type="image", source_url=source, download_url=download,
                thumbnail_url=_https(preview), creator=creator[:300], date=date[:120],
                license=rights, license_url=_rights_url(rights), rights_status=status,
                metadata={"provider": provider, "edm_is_shown_by": _https(direct),
                          "rights_policy": "per_item_edm_rights; preview_is_not_a_license"},
            ))
        return items


class NASAMediaProvider(_CatalogProvider):
    """NASA Images and Video Library search with bounded asset manifest lookup."""

    PROVIDER_NAME = "nasa"
    API_URL = "https://images-api.nasa.gov/search"
    ASSET_URL = "https://images-api.nasa.gov/asset/"

    def search_media(self, query: str, media_type: str = "any", max_results: int = MEDIA_SEARCH_MAX_RESULTS) -> List[MediaItem]:
        if not query.strip():
            return []
        types = ["video"] if media_type == "video" else ["image"] if media_type in {"image", "photo"} else ["image", "video"]
        params = urllib.parse.urlencode({"q": query[:300], "media_type": ",".join(types), "page_size": max(1, min(int(max_results), 10))})
        data = self._json(f"{self.API_URL}?{params}")
        rows = (((data or {}).get("collection") or {}).get("items") or [])
        items = []
        for row in rows[:max_results]:
            if not isinstance(row, dict):
                continue
            fields = (row.get("data") or [{}])[0]
            if not isinstance(fields, dict):
                continue
            media_kind = str(fields.get("media_type") or "image").lower()
            if media_kind not in {"image", "video"} or (media_type in {"image", "photo"} and media_kind != "image") or (media_type == "video" and media_kind != "video"):
                continue
            nasa_id = str(fields.get("nasa_id") or "")
            if not nasa_id:
                continue
            links = row.get("links") or []
            thumbnail = next((_https(link.get("href")) for link in links if isinstance(link, dict) and link.get("rel") == "preview"), "")
            manifest = self._json(self.ASSET_URL + urllib.parse.quote(nasa_id, safe=""), min_interval=0.2)
            files = ((manifest or {}).get("collection") or {}).get("items") or []
            candidates = [_https(v.get("href")) for v in files if isinstance(v, dict)]
            if media_kind == "video":
                download = next((u for u in candidates if u.lower().endswith(".mp4")), "")
            else:
                download = next((u for u in candidates if any(u.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff"))), "")
            if not download:
                # A NASA image preview may still be a usable image file; video
                # results without an MP4 are discovery records only and omitted.
                download = thumbnail if media_kind == "image" else ""
            if not download:
                continue
            title = str(fields.get("title") or "NASA media item")
            creator = str(fields.get("photographer") or fields.get("secondary_creator") or "")
            copyright_text = str(fields.get("copyright") or "")
            rights = classify_rights(rights_statement=copyright_text)
            items.append(MediaItem(
                provider=self.PROVIDER_NAME, id=nasa_id, title=title[:300],
                description=str(fields.get("description") or "")[:2000], media_type=media_kind,
                source_url=f"https://images.nasa.gov/details/{urllib.parse.quote(nasa_id, safe='')}",
                download_url=download, thumbnail_url=thumbnail, creator=creator[:300],
                date=str(fields.get("date_created") or "")[:120], license=copyright_text,
                rights_status=rights,
                metadata={"center": fields.get("center", ""), "location": fields.get("location", ""),
                          "keywords": fields.get("keywords", [])[:30] if isinstance(fields.get("keywords"), list) else [],
                          "rights_policy": "NASA_or_third_party_rights_must_be_checked_per_asset"},
            ))
        return items


class DVIDSMediaProvider(_CatalogProvider):
    """DVIDS search/asset API adapter; requires a registered API key."""

    PROVIDER_NAME = "dvids"
    SEARCH_URL = "https://api.dvidshub.net/search"
    ASSET_URL = "https://api.dvidshub.net/asset"

    def __init__(self, api_key: str = DVIDS_API_KEY, **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key.strip()

    def _with_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        values = dict(params)
        values["api_key"] = self.api_key
        return endpoint + "?" + urllib.parse.urlencode(values)

    def search_media(self, query: str, media_type: str = "any", max_results: int = MEDIA_SEARCH_MAX_RESULTS) -> List[MediaItem]:
        if not self.api_key or not query.strip():
            return []
        types = ["video"] if media_type == "video" else ["image"] if media_type in {"image", "photo"} else ["image", "video"]
        params: Dict[str, Any] = {"q": query[:300], "max_results": max(1, min(int(max_results), 20))}
        # DVIDS accepts repeated type[] fields.
        url = self._with_key(self.SEARCH_URL, params) + "&" + "&".join("type%5B%5D=" + t for t in types)
        data = self._json(url, min_interval=0.25)
        rows = (data or {}).get("results", [])
        items = []
        for row in rows[:max_results]:
            if not isinstance(row, dict):
                continue
            kind = str(row.get("type") or "").lower()
            if kind not in {"image", "video"}:
                continue
            item_id = str(row.get("id") or "")
            if not item_id:
                continue
            detail = self._json(self._with_key(self.ASSET_URL, {"id": item_id}), min_interval=0.25)
            record = (detail or {}).get("results") or row
            if not isinstance(record, dict):
                record = row
            source = _https(record.get("url") or row.get("url"))
            thumb = _https(record.get("thumbnail") or record.get("image") or row.get("thumbnail"))
            if kind == "image":
                download = _https(record.get("image") or row.get("source_file"))
            else:
                files = record.get("files") or []
                download = next((_https(f.get("src")) for f in files if isinstance(f, dict) and "mp4" in str(f.get("type", "")).lower() and _https(f.get("src"))), "")
            if not source or not download:
                continue
            credit = record.get("credit") or row.get("credit") or ""
            if isinstance(credit, list):
                credit = ", ".join(str(c.get("name") or c.get("rank") or "") if isinstance(c, dict) else str(c) for c in credit[:4])
            location = record.get("location") or {}
            if isinstance(location, dict):
                location_text = ", ".join(str(location.get(k)) for k in ("city", "state", "country") if location.get(k))
            else:
                location_text = str(location)
            items.append(MediaItem(
                provider=self.PROVIDER_NAME, id=item_id, title=str(record.get("title") or row.get("title") or "DVIDS media")[:300],
                description=str(record.get("description") or row.get("short_description") or "")[:2000],
                media_type=kind, source_url=source, download_url=download, thumbnail_url=thumb,
                creator=str(credit)[:300], date=str(record.get("date") or row.get("date") or "")[:120],
                license="DVIDS API Terms of Service", license_url="https://api.dvidshub.net/docs/tos",
                rights_status="COMMERCIAL_ALLOWED", width=int((record.get("dimensions") or {}).get("width", 0) or 0) if isinstance(record.get("dimensions"), dict) else int(row.get("width", 0) or 0),
                height=int((record.get("dimensions") or {}).get("height", 0) or 0) if isinstance(record.get("dimensions"), dict) else int(row.get("height", 0) or 0),
                metadata={"attribution": str(credit), "location": location_text,
                          "unit_name": record.get("unit_name") or row.get("unit_name", ""),
                          "branch": record.get("branch") or row.get("branch", ""),
                          "terms_url": "https://api.dvidshub.net/docs/tos",
                          "rights_policy": "DVIDS_API_terms_commercial_use; retain_attribution_and_source_link"},
            ))
        return items
