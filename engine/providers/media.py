"""
engine/providers/media.py
=========================
Abstract MediaItem dataclass and MediaProvider base class.

All media providers (Wikimedia, Internet Archive, future providers)
implement MediaProvider and return a consistent List[MediaItem].

Scoring fields (embedding_similarity, reranker_score, keyword_score, final_rank)
are populated later by MediaRanker — they are NOT part of provider responsibility.

License metadata is stored informationally only.
It is NEVER used as a download filter or gatekeeper.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """
    Consistent media result structure returned by all MediaProvider implementations.

    Fields marked with (*) are populated by MediaRanker after search,
    not by the provider itself.
    """

    # Core identity
    provider: str        # "wikimedia" | "internet_archive"
    id: str              # Provider-specific unique identifier
    title: str
    description: str
    media_type: str      # "image" | "video" | "audio" | "document"

    # URLs
    source_url: str      # Human-browsable page URL
    download_url: str    # Direct downloadable file URL
    thumbnail_url: str   # Preview/thumb URL (may be empty)

    # Provenance metadata (informational only)
    creator: str
    date: str
    license: str         # Stored as-is — never used as download filter

    # Technical info (best-effort — 0 if unknown)
    file_size_bytes: int = 0
    width: int = 0
    height: int = 0
    duration_seconds: int = 0

    # Extra provider-specific metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Scoring fields — populated by MediaRanker, not providers (*)
    keyword_score: float = 0.0
    embedding_similarity: float = 0.0
    reranker_score: float = 0.0
    final_rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return plain dict representation (embedding excluded)."""
        return asdict(self)

    def build_text_representation(self) -> str:
        """
        Build rich text representation from metadata for embedding.
        Uses: title + description + creator + date + provider + media_type.
        Does NOT embed the scoring fields.
        """
        parts: List[str] = []
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.description:
            parts.append(f"Description: {self.description[:500]}")
        if self.creator:
            parts.append(f"Creator: {self.creator}")
        if self.date:
            parts.append(f"Date: {self.date}")
        if self.media_type:
            parts.append(f"Media type: {self.media_type}")
        parts.append(f"Provider: {self.provider}")
        # Include license informatively so embedding can weight archival items
        if self.license:
            parts.append(f"License: {self.license}")
        return "\n".join(parts)

    def dedup_key(self) -> str:
        """
        Key used for deduplication across providers and queries.
        Uses download_url as primary key; falls back to provider:id.
        """
        if self.download_url:
            return self.download_url.lower().strip()
        return f"{self.provider}:{self.id}"


class MediaProvider:
    """
    Abstract base class for all media search providers.

    Subclasses implement:
        search_media()     → List[MediaItem]
        get_media_metadata() → Optional[MediaItem]

    Providers MUST NOT filter results based on license.
    Providers MUST handle HTTP errors gracefully and return partial results.
    """

    PROVIDER_NAME: str = "base"

    def search_media(
        self,
        query: str,
        media_type: str = "any",
        max_results: int = 20
    ) -> List[MediaItem]:
        """
        Search for media matching query.

        Args:
            query: Search terms (English preferred for best API coverage).
            media_type: "image" | "video" | "any"
            max_results: Maximum number of items to return.

        Returns:
            List of MediaItem — may be empty on error (never raises).
        """
        raise NotImplementedError

    def get_media_metadata(self, item_id: str) -> Optional[MediaItem]:
        """
        Fetch full metadata for a specific item by its provider ID.
        Returns None if not found or on error.
        """
        raise NotImplementedError

    @staticmethod
    def _mime_to_media_type(mime: str) -> str:
        """Convert MIME type string to normalised media_type label."""
        if not mime:
            return "document"
        m = mime.lower()
        if m.startswith("image/"):
            return "image"
        if m.startswith("video/"):
            return "video"
        if m.startswith("audio/"):
            return "audio"
        return "document"
