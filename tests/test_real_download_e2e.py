"""
tests/test_real_download_e2e.py
===============================
Non-dry-run End-to-End Media Retrieval, Ranking, Real Download,
Local File Verification, Media Library Indexing, and Metadata Persistence.
"""

import os
from pathlib import Path
import pytest

from engine.pipeline.media_finder import MediaFinder
from engine.pipeline.media_library import MediaLibrary
from engine.pipeline.media_ranker import MediaRanker
from engine.providers.embedding import FallbackEmbeddingProvider
from engine.providers.reranker import FallbackRerankerProvider
from engine.pipeline.visual_requirements import REAL_PREFERRED


@pytest.mark.filterwarnings("ignore::urllib3.exceptions.InsecureRequestWarning")
def test_real_download_e2e_pipeline():
    """
    Executes a real non-dry-run E2E retrieval:
    Visual requirement -> Provider search -> Ranking -> Download ->
    Local file on disk -> Media library indexing -> Metadata persistence in sources.json.
    """
    fast_ranker = MediaRanker(
        embedding_provider=FallbackEmbeddingProvider(),
        reranker_provider=FallbackRerankerProvider(),
    )
    finder = MediaFinder(ranker=fast_ranker)
    test_folder = "test_e2e_real_download"

    # Search for an authentic, publicly accessible documentary photo on Wikimedia Commons
    result = finder.find_and_download(
        request="Monumen Nasional Jakarta",
        media="photo",
        count=1,
        folder=test_folder,
        visual_requirement=REAL_PREFERRED
    )

    assert result.status.upper() == "OK", f"Expected OK status, got: {result.status}"
    assert len(result.results) >= 1, "Expected at least 1 candidate ranked"

    downloaded = [r for r in result.results if r.local_path]
    assert len(downloaded) >= 1, "Expected at least 1 file to be successfully downloaded"

    item = downloaded[0]
    local_path = Path(item.local_path)

    # 1. Verify file exists on local filesystem and has non-zero size
    assert local_path.is_file(), f"File does not exist: {local_path}"
    file_size = local_path.stat().st_size
    assert file_size > 0, f"Downloaded file is empty (size={file_size})"

    # 2. Verify sources.json exists and contains metadata persistence
    sources_json_path = local_path.parent / "sources.json"
    assert sources_json_path.exists(), f"sources.json was not created at {sources_json_path}"
    sources_content = sources_json_path.read_text(encoding="utf-8")
    assert item.download_url in sources_content or item.source_url in sources_content

    # 3. Verify Local Media Library Indexing and Reuse
    library = MediaLibrary()
    stats = library.get_stats()
    assert stats["total_registered"] >= 1, "MediaLibrary should have registered downloaded asset"

    # Search local library for the asset we just downloaded
    local_hits = library.search_local("Monumen Nasional", media_type="any")
    assert len(local_hits) >= 1, "Local Media Library should find and reuse the newly downloaded asset"
    assert local_hits[0]["is_local_reuse"] is True
    assert Path(local_hits[0]["local_path"]).exists()
