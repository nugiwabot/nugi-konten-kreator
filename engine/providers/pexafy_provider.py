"""
engine/providers/pexafy_provider.py
===================================
Pexafy semantic photo search provider.

Pexafy is a semantic stock-photo search engine that accesses curated photos
across Unsplash, Pexels, Pixabay, and other sources.

IMPORTANT:
- Pexafy provides PHOTO / IMAGE search ONLY. It does NOT provide video search.
- When media_type == "video", search_media immediately returns [] without
  making an API call.
- License metadata is preserved informatively (free, cc0, etc.).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from engine.config import PEXAFY_API_KEY, PEXAFY_MCP_URL
from engine.providers.media import MediaItem, MediaProvider

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15  # seconds


def _get_pexafy_token() -> str:
    """
    Retrieve Pexafy bearer token from:
    1. config.PEXAFY_API_KEY
    2. PEXAFY_API_KEY environment variable
    3. PEXAFY_TOKEN environment variable
    4. ~/.gemini/config/mcp_config.json (local Gemini IDE MCP registration)
    """
    if PEXAFY_API_KEY:
        token = PEXAFY_API_KEY.strip()
        if token.startswith("Bearer "):
            return token.split("Bearer ", 1)[1].strip()
        return token

    env_token = os.environ.get("PEXAFY_API_KEY") or os.environ.get("PEXAFY_TOKEN")
    if env_token:
        token = env_token.strip()
        if token.startswith("Bearer "):
            return token.split("Bearer ", 1)[1].strip()
        return token

    config_path = os.path.expanduser(r"~/.gemini/config/mcp_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                auth = data.get("mcpServers", {}).get("pexafy", {}).get("headers", {}).get("Authorization", "")
                if auth.startswith("Bearer "):
                    return auth.split("Bearer ", 1)[1].strip()
                return auth.strip()
        except Exception as e:
            logger.debug(f"Could not read mcp_config.json: {e}")

    return ""


class PexafyProvider(MediaProvider):
    """
    MediaProvider implementation for Pexafy semantic photo search.
    """

    PROVIDER_NAME: str = "pexafy"

    def __init__(self, mcp_url: Optional[str] = None, token: Optional[str] = None):
        self.mcp_url = mcp_url or PEXAFY_MCP_URL
        self._token = token
        self._session_id: Optional[str] = None
        self._session_initialized_at: float = 0.0

    @property
    def token(self) -> str:
        if self._token:
            return self._token
        return _get_pexafy_token()

    def is_available(self) -> bool:
        """Check whether a token is configured for Pexafy."""
        return bool(self.token)

    def _get_headers(self) -> Dict[str, str]:
        token = self.token
        auth = f"Bearer {token}" if token and not token.startswith("Bearer ") else (token or "")
        return {
            "Authorization": auth,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; NugiMediaFinder/1.0)",
            "Accept": "application/json, text/event-stream",
        }

    def _init_mcp_session(self) -> Optional[str]:
        """Initialize MCP session if needed."""
        # Reuse existing session if under 10 minutes old
        if self._session_id and (time.time() - self._session_initialized_at < 600):
            return self._session_id

        if not self.token:
            return None

        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "nugi-media-finder", "version": "1.0"},
            },
        }

        try:
            req = urllib.request.Request(
                self.mcp_url,
                data=json.dumps(init_payload).encode("utf-8"),
                headers=self._get_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
                session_id = resp.headers.get("mcp-session-id")
                if session_id:
                    self._session_id = session_id
                    self._session_initialized_at = time.time()
                return self._session_id
        except Exception as e:
            logger.debug(f"Pexafy MCP session initialization failed: {e}")
            return None

    def search_media(
        self,
        query: str,
        media_type: str = "any",
        max_results: int = 20,
    ) -> List[MediaItem]:
        """
        Search Pexafy for photos matching the natural-language query.

        NOTE:
        - If media_type == "video", returns [] immediately (Pexafy is photo-only).
        """
        norm_type = media_type.lower().strip()
        if norm_type in ("video", "audio", "document"):
            # Pexafy does NOT support video
            return []

        if not self.is_available():
            logger.debug("PexafyProvider: No API token configured, skipping search.")
            return []

        try:
            session_id = self._init_mcp_session()
            headers = self._get_headers()
            if session_id:
                headers["mcp-session-id"] = session_id

            call_payload = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000) % 100000,
                "method": "tools/call",
                "params": {
                    "name": "search_photos",
                    "arguments": {
                        "q": query,
                    },
                },
            }

            # Enforce rate limit (max 50 req/min => 1.2s delay between requests)
            now = time.time()
            if hasattr(self, "_last_request_time"):
                elapsed = now - self._last_request_time
                if elapsed < 1.2:
                    time.sleep(1.2 - elapsed)
            self._last_request_time = time.time()

            req = urllib.request.Request(
                self.mcp_url,
                data=json.dumps(call_payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            raw_items: List[Dict[str, Any]] = []
            with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
                content = resp.read().decode("utf-8")
                for line in content.splitlines():
                    if line.startswith("data: "):
                        res = json.loads(line[6:])
                        result_obj = res.get("result", {})
                        if result_obj.get("isError"):
                            err_msg = result_obj.get("content", [{}])[0].get("text", "")
                            if "faster than your plan allows" in err_msg:
                                logger.warning("Pexafy rate limit reached. Waiting 60s for quota reset...")
                                time.sleep(60.0)
                                return self.search_media(query, media_type, max_results)
                            logger.warning(f"Pexafy returned error: {err_msg}")
                            return []

                        text_content = result_obj.get("content", [{}])[0].get("text", "{}")
                        try:
                            parsed = json.loads(text_content)
                            raw_items = parsed.get("data", [])
                        except Exception:
                            raw_items = []
                        break

            items: List[MediaItem] = []
            for i, raw in enumerate(raw_items[:max_results]):
                item = self._parse_pexafy_item(raw, query, i)
                if item:
                    items.append(item)

            return items

        except Exception as e:
            logger.warning(f"PexafyProvider search failed for query '{query}': {e}")
            return []

    def _parse_pexafy_item(self, raw: Dict[str, Any], query: str, index: int) -> Optional[MediaItem]:
        """Parse raw Pexafy API result into standard MediaItem."""
        urls = raw.get("urls") or {}
        download_url = urls.get("regular") or raw.get("image_url") or urls.get("full")
        if not download_url:
            return None

        photo_id = str(raw.get("photo_id") or raw.get("source_photo_id") or f"pex-{index}")
        full_desc = raw.get("description") or raw.get("alt_description") or raw.get("source_description") or ""

        # Keep title concise and readable
        if raw.get("alt_description"):
            title = raw["alt_description"][:120].strip()
        elif full_desc:
            title = full_desc[:120].strip()
        else:
            title = f"{raw.get('source', 'Photo')} by {raw.get('photographer_full_name', 'Photographer')}"

        description = full_desc[:280].strip()
        creator = raw.get("photographer_full_name") or raw.get("photographer_username") or ""
        source_url = raw.get("photographer_url") or raw.get("source_image_url") or download_url
        thumbnail_url = urls.get("small") or urls.get("thumb") or raw.get("preview_url") or download_url
        license_type = raw.get("license_type") or "free"

        metadata = {
            "source": raw.get("source", ""),
            "color_name": raw.get("color_name", ""),
            "attribution": raw.get("attribution", ""),
            "orientation": raw.get("orientation", ""),
        }

        return MediaItem(
            provider="pexafy",
            id=photo_id,
            title=title,
            description=description,
            media_type="image",
            source_url=source_url,
            download_url=download_url,
            thumbnail_url=thumbnail_url,
            creator=creator,
            date=raw.get("uploaded_on", ""),
            license=license_type,
            file_size_bytes=0,
            width=int(raw.get("width") or 0),
            height=int(raw.get("height") or 0),
            duration_seconds=0,
            metadata=metadata,
        )

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        """Fetch metadata by photo ID (best-effort stub for MediaProvider interface)."""
        return None
