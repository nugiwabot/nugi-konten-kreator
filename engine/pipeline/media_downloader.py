"""
engine/pipeline/media_downloader.py
=====================================
Downloads MediaItems to the local filesystem.

Responsibilities:
  - Sanitize filenames (filesystem-safe, human-readable)
  - Avoid filename collisions (append -001 suffix)
  - Enforce path confinement (no path traversal)
  - Respect max file size limit
  - Write sources.json metadata after each batch
  - Return DownloadReport with per-file success/failure detail

SECURITY:
  - User-provided folder names are sanitized before use
  - Downloads are always scoped within MEDIA_ASSETS_DIR or an explicit base
  - No shell commands are executed

LICENSE NOTE:
  - License metadata is stored in sources.json informatively.
  - It is NEVER used as a filter or download gatekeeper.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.config import (
    MEDIA_ASSETS_DIR,
    MEDIA_DOWNLOAD_TIMEOUT,
    MEDIA_MAX_FILE_SIZE_MB,
)
from engine.providers.media import MediaItem

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 (compatible; NugiContentBrain/1.0; +https://github.com/nugiwabot/nugi-konten-kreator)"
)
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_DASH = re.compile(r"-{2,}")
_MAX_FILENAME_LEN = 80  # characters (excl. extension)


@dataclass
class DownloadedFile:
    """Record of a successfully downloaded file."""
    filename: str
    local_path: str
    provider: str
    source_url: str
    download_url: str
    title: str
    creator: str
    date: str
    license: str       # Stored informatively — not a filter
    retrieved_at: str
    file_size_bytes: int = 0
    embedding_similarity: float = 0.0
    reranker_score: float = 0.0
    final_rank: int = 0


@dataclass
class FailedFile:
    """Record of a failed download attempt."""
    title: str
    download_url: str
    provider: str
    reason: str


@dataclass
class DownloadReport:
    """Summary of a download batch."""
    total_attempted: int
    successful: List[DownloadedFile] = field(default_factory=list)
    failed: List[FailedFile] = field(default_factory=list)
    folder: Optional[Path] = None
    sources_json_path: Optional[Path] = None

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def fail_count(self) -> int:
        return len(self.failed)

    def summary_line(self) -> str:
        return (
            f"{self.total_attempted} requested — "
            f"{self.success_count} downloaded successfully, "
            f"{self.fail_count} failed"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_attempted": self.total_attempted,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "folder": str(self.folder) if self.folder else None,
            "sources_json": str(self.sources_json_path) if self.sources_json_path else None,
            "successful": [vars(f) for f in self.successful],
            "failed": [vars(f) for f in self.failed],
        }


class MediaDownloader:
    """
    Downloads MediaItems to the filesystem under a specified subfolder.
    All downloads are confined within `base_dir` (default: MEDIA_ASSETS_DIR).
    """

    def __init__(
        self,
        base_dir: Path = MEDIA_ASSETS_DIR,
        timeout: int = MEDIA_DOWNLOAD_TIMEOUT,
        max_size_mb: int = MEDIA_MAX_FILE_SIZE_MB,
    ):
        self.base_dir = base_dir
        self.timeout = timeout
        self.max_size_bytes = max_size_mb * 1024 * 1024

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def download_batch(
        self,
        items: List[MediaItem],
        folder: str = "general",
        count: int = 5,
    ) -> DownloadReport:
        """
        Download up to `count` items from `items` into base_dir/folder/.

        Args:
            items: Ranked MediaItem list (download in order until count met).
            folder: Subfolder name (will be sanitized, then resolved under base_dir).
            count: Maximum number of files to download.

        Returns:
            DownloadReport with per-file results and sources.json path.
        """
        folder_path = self._resolve_folder(folder)
        folder_path.mkdir(parents=True, exist_ok=True)

        report = DownloadReport(
            total_attempted=min(count, len(items)),
            folder=folder_path,
        )

        downloaded_count = 0
        for item in items:
            if downloaded_count >= count:
                break

            result = self._download_item(item, folder_path, downloaded_count + 1)
            if result:
                report.successful.append(result)
                downloaded_count += 1
            else:
                # Error already logged; item will appear in failed list
                # (logged with reason inside _download_item)
                report.failed.append(FailedFile(
                    title=item.title,
                    download_url=item.download_url,
                    provider=item.provider,
                    reason="Download failed — see log for details",
                ))

        # Write sources.json
        sources_path = self._write_sources_json(folder_path, report.successful)
        report.sources_json_path = sources_path

        return report

    # ------------------------------------------------------------------
    # Internal: single file download
    # ------------------------------------------------------------------

    def _download_item(
        self,
        item: MediaItem,
        folder_path: Path,
        index: int,
    ) -> Optional[DownloadedFile]:
        """
        Download a single MediaItem to folder_path.
        Returns DownloadedFile on success, None on any failure.
        """
        if not item.download_url and not item.thumbnail_url:
            logger.warning(f"Skipping '{item.title}': no download_url or thumbnail_url")
            return None

        # For Wikimedia images, prefer cached 1280px thumbnail_url to avoid 429 CDN rate limits
        target_url = item.download_url
        if item.provider == "wikimedia" and item.media_type == "image" and item.thumbnail_url:
            target_url = item.thumbnail_url

        # Determine file extension from URL or media_type
        ext = self._infer_extension(target_url, item.media_type)
        filename = self._safe_filename(item.title or item.id, ext, index)
        dest_path = self._resolve_collision(folder_path / filename)

        # Perform the download
        success, size, reason = self._fetch_file(target_url, dest_path)
        # If thumbnail failed or was not used and original exists, or vice versa, fallback
        if not success:
            fallback_url = item.thumbnail_url if target_url != item.thumbnail_url else item.download_url
            if fallback_url and fallback_url != target_url:
                logger.info(f"Retrying download with alternate URL for '{item.title}'")
                success, size, reason = self._fetch_file(fallback_url, dest_path)

        if not success:
            logger.warning(f"Failed to download '{item.title}': {reason}")
            return None

        return DownloadedFile(
            filename=dest_path.name,
            local_path=str(dest_path),
            provider=item.provider,
            source_url=item.source_url,
            download_url=item.download_url or target_url,
            title=item.title,
            creator=item.creator,
            date=item.date,
            license=item.license,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            file_size_bytes=size,
            embedding_similarity=item.embedding_similarity,
            reranker_score=item.reranker_score,
            final_rank=item.final_rank,
        )

    def _fetch_file(
        self, url: str, dest: Path
    ) -> tuple[bool, int, str]:
        """
        Stream-download `url` to `dest`.
        Returns (success, bytes_written, error_reason).
        Respects max_size_bytes limit.
        Never raises.
        """
        import time

        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                # Check Content-Length before streaming if available
                content_length = resp.headers.get("Content-Length")
                if content_length:
                    try:
                        size_hint = int(content_length)
                        if size_hint > self.max_size_bytes:
                            return False, 0, (
                                f"File too large: {size_hint / (1024*1024):.1f} MB "
                                f"exceeds limit of {self.max_size_bytes // (1024*1024)} MB"
                            )
                    except ValueError:
                        pass

                # Stream in chunks
                downloaded = 0
                chunk_size = 65536  # 64 KB
                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > self.max_size_bytes:
                            f.close()
                            dest.unlink(missing_ok=True)
                            return False, 0, (
                                f"File exceeded size limit during download "
                                f"({downloaded / (1024*1024):.1f} MB)"
                            )
                        f.write(chunk)

                return True, downloaded, ""

        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning(f"CDN rate limit (429). Retrying after 2s for {dest.name}...")
                time.sleep(2.0)
                try:
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        downloaded = 0
                        with open(dest, "wb") as f:
                            while True:
                                chunk = resp.read(65536)
                                if not chunk:
                                    break
                                downloaded += len(chunk)
                                f.write(chunk)
                        return True, downloaded, ""
                except Exception as retry_err:
                    dest.unlink(missing_ok=True)
                    return False, 0, f"HTTP 429 (retry failed: {retry_err})"
            return False, 0, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, 0, f"URL error: {e.reason}"
        except OSError as e:
            dest.unlink(missing_ok=True)
            return False, 0, f"Filesystem error: {e}"
        except Exception as e:
            dest.unlink(missing_ok=True)
            return False, 0, f"Unexpected: {e}"

    # ------------------------------------------------------------------
    # Filename helpers
    # ------------------------------------------------------------------

    def _safe_filename(self, title: str, ext: str, index: int) -> str:
        """
        Convert a media title to a filesystem-safe filename.

        Examples:
          "D-Day Landing at Omaha Beach" + ".jpg" + 1 → "d-day-landing-at-omaha-beach-001.jpg"
          "Albert Einstein 1921 portrait" + ".jpg" + 2 → "albert-einstein-1921-portrait-002.jpg"
        """
        # Lowercase
        name = title.lower()
        # Replace illegal and whitespace chars with dash
        name = _ILLEGAL_CHARS.sub("-", name)
        name = re.sub(r"\s+", "-", name)
        # Collapse multiple dashes
        name = _MULTI_DASH.sub("-", name)
        # Strip leading/trailing dashes
        name = name.strip("-")
        # Truncate to max length
        name = name[:_MAX_FILENAME_LEN]
        name = name.rstrip("-")
        # Append zero-padded index
        name = f"{name}-{index:03d}"
        return f"{name}{ext}"

    @staticmethod
    def _infer_extension(url: str, media_type: str) -> str:
        """Infer file extension from URL path; fall back to media_type defaults."""
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        for ext in [".mp4", ".ogv", ".webm", ".avi", ".mov",
                    ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff",
                    ".pdf", ".mp3", ".ogg"]:
            if path.endswith(ext):
                return ".jpg" if ext == ".jpeg" else ext
        # Fallback by media_type
        fallbacks = {"video": ".mp4", "image": ".jpg", "audio": ".mp3"}
        return fallbacks.get(media_type, ".bin")

    @staticmethod
    def _resolve_collision(path: Path) -> Path:
        """If path exists, append -002, -003, … to the stem until unique."""
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        # Strip existing -NNN suffix if present, then re-add
        base_stem = re.sub(r"-\d{3}$", "", stem)
        counter = 2
        while True:
            new_path = parent / f"{base_stem}-{counter:03d}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    # ------------------------------------------------------------------
    # Folder resolution (path confinement)
    # ------------------------------------------------------------------

    def _resolve_folder(self, folder: str) -> Path:
        """
        Resolve user-provided folder name safely within base_dir.

        SECURITY: Sanitize path components to prevent directory traversal.
        Only alphanumeric characters, dashes, underscores, and forward
        slashes (for sub-paths) are allowed.
        """
        # Normalise separators to forward slash, sanitize each component
        parts = folder.replace("\\", "/").strip("/").split("/")
        safe_parts = []
        for part in parts:
            # Keep only safe chars
            safe = re.sub(r"[^a-zA-Z0-9_\-.]", "_", part).strip("._")
            if safe and safe not in (".", ".."):
                safe_parts.append(safe)

        if not safe_parts:
            safe_parts = ["general"]

        resolved = self.base_dir.joinpath(*safe_parts).resolve()

        # Final guard: ensure the resolved path starts with base_dir
        try:
            resolved.relative_to(self.base_dir.resolve())
        except ValueError:
            logger.warning(
                f"Path traversal attempt detected for folder='{folder}'. "
                f"Falling back to base_dir."
            )
            resolved = self.base_dir / "general"

        return resolved

    # ------------------------------------------------------------------
    # sources.json
    # ------------------------------------------------------------------

    def _write_sources_json(
        self,
        folder_path: Path,
        downloaded: List[DownloadedFile],
    ) -> Optional[Path]:
        """
        Write / merge sources.json in folder_path.
        Merges with existing file if present (append new entries).
        License info is stored as-is — never used as a filter.
        """
        sources_path = folder_path / "sources.json"

        existing_assets: List[Dict] = []
        if sources_path.exists():
            try:
                with open(sources_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    existing_assets = existing.get("assets", [])
            except Exception:
                existing_assets = []

        # Map by filename to avoid duplicate entries on re-run
        asset_map: Dict[str, Dict] = {a["filename"]: a for a in existing_assets}

        for df in downloaded:
            asset_map[df.filename] = {
                "filename": df.filename,
                "provider": df.provider,
                "source_url": df.source_url,
                "download_url": df.download_url,
                "title": df.title,
                "creator": df.creator,
                "date": df.date,
                "license": df.license,
                "retrieved_at": df.retrieved_at,
                "file_size_bytes": df.file_size_bytes,
                "relevance_scores": {
                    "embedding_similarity": df.embedding_similarity,
                    "reranker_score": df.reranker_score,
                    "final_rank": df.final_rank,
                },
            }

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": (
                "License information is stored informatively for traceability only. "
                "It does not imply any particular usage right or restriction."
            ),
            "assets": list(asset_map.values()),
        }

        try:
            with open(sources_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return sources_path
        except Exception as e:
            logger.error(f"Failed to write sources.json: {e}")
            return None
