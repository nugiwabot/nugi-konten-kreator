"""
engine/pipeline/media_library.py
================================
Lightweight Persistent Local Media Library Catalog for Nugi Content Intelligence Engine.

Maintains engine/data/media_library.json to enable:
LOCAL LIBRARY FIRST
→ REUSE EXISTING ASSETS
→ IF INSUFFICIENT, SEARCH EXTERNAL PROVIDERS
→ DOWNLOAD NEW ASSETS
→ INDEX NEW ASSETS

Zero external database dependencies, zero locks, fully portable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.config import BASE_DIR, MEDIA_ASSETS_DIR

logger = logging.getLogger(__name__)

DEFAULT_MEDIA_LIBRARY_PATH = BASE_DIR / "engine" / "data" / "media_library.json"


@dataclass
class MediaLibraryEntry:
    id: str
    local_path: str
    sha256: str
    provider: str
    source_url: str
    download_url: str
    title: str
    description: str
    creator: str
    date: str
    media_type: str
    entities: List[str] = field(default_factory=list)
    query: str = ""
    visual_requirement: str = "GENERIC_ALLOWED"
    retrieved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    file_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MediaLibrary:
    """
    Manages the local media asset catalog.
    Enables local-first searching and automatic indexing of downloaded media.
    """

    def __init__(self, catalog_path: Optional[Path] = None):
        self.catalog_path = catalog_path or DEFAULT_MEDIA_LIBRARY_PATH
        self._entries: Dict[str, MediaLibraryEntry] = {}
        self._load()

    def _load(self):
        if self.catalog_path.exists():
            try:
                data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
                raw_entries = data.get("entries", [])
                for item in raw_entries:
                    entry = MediaLibraryEntry(**item)
                    self._entries[entry.id] = entry
                logger.info(f"Loaded {len(self._entries)} entries from media library catalog.")
            except Exception as e:
                logger.warning(f"Failed to load media library from {self.catalog_path}: {e}")
                self._entries = {}
        else:
            self._entries = {}

    def _save(self):
        try:
            self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "total_entries": len(self._entries),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": [e.to_dict() for e in self._entries.values()]
            }
            self.catalog_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save media library catalog: {e}")

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    def register_asset(
        self,
        local_path: str,
        provider: str,
        source_url: str,
        download_url: str,
        title: str,
        description: str,
        creator: str = "",
        date: str = "",
        media_type: str = "image",
        entities: Optional[List[str]] = None,
        query: str = "",
        visual_requirement: str = "GENERIC_ALLOWED",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MediaLibraryEntry]:
        """Registers a downloaded asset into the catalog."""
        p = Path(local_path)
        if not p.exists():
            logger.warning(f"Cannot register asset: local file '{local_path}' does not exist.")
            return None

        # Calculate file sha256 checksum and size
        sha256_hash = ""
        try:
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            sha256_hash = hasher.hexdigest()
            file_size = p.stat().st_size
        except Exception:
            file_size = 0

        # Unique asset ID derived from sha256 or download url
        asset_id = sha256_hash[:16] if sha256_hash else hashlib.sha256(download_url.encode()).hexdigest()[:16]

        entry = MediaLibraryEntry(
            id=asset_id,
            local_path=str(p.resolve()),
            sha256=sha256_hash,
            provider=provider,
            source_url=source_url,
            download_url=download_url,
            title=title,
            description=description,
            creator=creator,
            date=date,
            media_type=media_type,
            entities=entities or [],
            query=query,
            visual_requirement=visual_requirement,
            file_size_bytes=file_size,
            metadata=metadata or {},
        )
        self._entries[asset_id] = entry
        self._save()
        return entry

    def search_local(
        self,
        query: str,
        media_type: str = "any",
        entities: Optional[List[str]] = None,
        visual_requirement: str = "GENERIC_ALLOWED",
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches the local library.
        Returns candidate entries whose physical files still exist on disk.
        """
        if not self._entries:
            return []

        q_lower = query.lower()
        q_words = set(re.findall(r"\w+", q_lower))
        target_entities = set(e.lower() for e in (entities or []))

        scored_candidates = []

        for entry in self._entries.values():
            # Verify file exists on disk
            if not Path(entry.local_path).exists():
                continue

            # Media type filter
            if media_type != "any" and entry.media_type != media_type:
                continue

            score = 0.0
            
            # Exact entity match (Highest weight: 0.5)
            entry_entities = set(e.lower() for e in entry.entities)
            if target_entities and target_entities.intersection(entry_entities):
                score += 0.5
            elif any(qw in entry_entities or any(qw in ee for ee in entry_entities) for qw in q_words if len(qw) >= 3):
                score += 0.25

            # Title & Description keyword overlap (Weight: 0.35)
            text_corpus = f"{entry.title} {entry.description} {entry.query}".lower()
            corpus_words = set(re.findall(r"\w+", text_corpus))
            overlap = len(q_words.intersection(corpus_words))
            score += min(0.35, overlap * 0.12)

            # Visual requirement compatibility
            if visual_requirement in (entry.visual_requirement, "auto", "any") or visual_requirement == "GENERIC_ALLOWED":
                score += 0.1

            # Minimum score threshold
            if score >= 0.15:
                scored_candidates.append({
                    "score": round(score, 3),
                    "entry": entry
                })

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        results = []
        for item in scored_candidates[:max_results]:
            e = item["entry"]
            results.append({
                "id": e.id,
                "title": e.title,
                "provider": f"local_library({e.provider})",
                "media_type": e.media_type,
                "score": item["score"],
                "source_url": e.source_url,
                "download_url": e.download_url,
                "local_path": e.local_path,
                "creator": e.creator,
                "date": e.date,
                "visual_requirement": e.visual_requirement,
                "entities": e.entities,
                "metadata": e.metadata,
                "is_local_reuse": True
            })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Summary metrics of the local media library."""
        total = len(self._entries)
        existing = sum(1 for e in self._entries.values() if Path(e.local_path).exists())
        images = sum(1 for e in self._entries.values() if e.media_type in ("image", "photo"))
        videos = sum(1 for e in self._entries.values() if e.media_type == "video")
        total_bytes = sum(e.file_size_bytes for e in self._entries.values())
        
        return {
            "total_registered": total,
            "physically_present": existing,
            "images_count": images,
            "videos_count": videos,
            "total_disk_mb": round(total_bytes / (1024 * 1024), 2),
            "catalog_path": str(self.catalog_path),
        }
