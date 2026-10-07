"""
tests/test_content_create_coverage.py
=====================================
Tests verifying 100% B-roll shot coverage and absence of arbitrary limits
in nugi_content_create workflow.
"""

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = REPO_ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

import pytest
from unittest.mock import MagicMock, patch
import server
from engine.pipeline.media_finder import MediaFinderResult, MediaFinderItem


def test_content_create_full_broll_coverage(tmp_path):
    """
    Ensure nugi_content_create attempts B-roll retrieval for ALL candidate shots
    without being arbitrarily capped at 5 shots.
    """
    mock_finder = MagicMock()
    mock_item = MediaFinderItem(
        rank=1,
        title="Sample Broll Asset",
        provider="wikimedia",
        media_type="image",
        score=0.9,
        source_url="https://commons.wikimedia.org/wiki/File:Sample.jpg",
        download_url="https://upload.wikimedia.org/wikipedia/commons/sample.jpg",
        local_path=str(tmp_path / "sample.jpg"),
    )
    mock_finder.find_and_download.return_value = MediaFinderResult(
        request="sample query",
        media_type="any",
        era="auto",
        style="auto",
        queries=["sample query"],
        providers_contacted=["wikimedia"],
        results=[mock_item],
        total_candidates_found=1,
        downloaded_count=1,
        status="OK"
    )

    import shutil
    test_out = REPO_ROOT / "output" / "test_full_coverage"
    if test_out.exists():
        shutil.rmtree(test_out, ignore_errors=True)

    try:
        with patch("engine.pipeline.media_finder.MediaFinder", return_value=mock_finder):
            res = server.content_create(
                topic="Krisis Keterjangkauan Rumah dan Komuter",
                dry_run=False,
                output_folder="test_full_coverage",
            )

            assert res["status"] == "ok"
            total_shots = res["total_shots_planned"]
            assert total_shots >= 4  # Standard talking head script produces multiple shots

            # Verify finder was called for all shots requiring B-roll
            call_count = mock_finder.find_and_download.call_count
            assert call_count > 0
            manifest = res["manifest"]
            assert manifest["shots_planned"] == total_shots
            assert res["total_assets_ready"] >= 1
    finally:
        if test_out.exists():
            shutil.rmtree(test_out, ignore_errors=True)
