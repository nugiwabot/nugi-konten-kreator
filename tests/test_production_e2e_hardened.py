"""
tests/test_production_e2e_hardened.py
======================================
End-to-end production validation of the hardened Nugi Konten Kreator pipeline.
Verifies topic qualification, dynamic research dossier, topic-grounded script,
fact checking, visual planning, quality scoring, and artifact packaging.
"""

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = REPO_ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

import json
import pytest
from unittest.mock import MagicMock, patch
import server
from engine.pipeline.media_finder import MediaFinderResult, MediaFinderItem


def test_hardened_production_workflow_e2e(tmp_path):
    """
    Simulates full autonomous execution of content_create with quick depth
    and validates all 7 core workspace production artifacts.
    """
    mock_finder = MagicMock()
    mock_item = MediaFinderItem(
        rank=1,
        title="Sample Archive Footage",
        provider="wikimedia",
        media_type="image",
        score=0.92,
        source_url="https://commons.wikimedia.org/wiki/File:Sample.jpg",
        download_url="https://upload.wikimedia.org/wikipedia/commons/sample.jpg",
        local_path=str(tmp_path / "sample.jpg"),
    )
    mock_finder.find_and_download.return_value = MediaFinderResult(
        request="tech sample",
        media_type="any",
        era="auto",
        style="auto",
        queries=["tech sample"],
        providers_contacted=["wikimedia"],
        results=[mock_item],
        total_candidates_found=1,
        downloaded_count=1,
        status="OK"
    )

    topic = "Transformasi Kecerdasan Buatan dan Pasar Tenaga Kerja"
    folder_name = "test_hardened_prod"

    with patch("engine.pipeline.media_finder.MediaFinder", return_value=mock_finder):
        res = server.content_create(
            topic=topic,
            output_folder=folder_name,
            dry_run=False,
            depth="quick",
        )

    # 1. Assert result status and metrics
    assert res["status"] in ("ok", "PUBLISH_READY", "MINOR_EDIT")
    assert res["content_quality_score"] > 0
    assert "research_strength" in res["dimension_scores"]

    # 2. Assert physical artifacts on disk
    work_dir = REPO_ROOT / "output" / folder_name
    assert (work_dir / "research_dossier.json").exists()
    assert (work_dir / "research_dossier.md").exists()
    assert (work_dir / "script.md").exists()
    assert (work_dir / "fact_check_report.json").exists()
    assert (work_dir / "broll_plan.json").exists()
    assert (work_dir / "content_quality_report.json").exists()
    assert (work_dir / "manifest.json").exists()

    # 3. Assert manifest integration
    manifest = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "content_quality" in manifest
    assert manifest["content_quality"]["overall_score"] == res["content_quality_score"]
    assert "dossier_json" in manifest["artifacts"]
    assert "content_quality_json" in manifest["artifacts"]

    # 4. Assert script is topic-grounded without static housing clichés
    script_text = (work_dir / "script.md").read_text(encoding="utf-8")
    assert "Kecerdasan Buatan" in script_text or "tenaga kerja" in script_text.lower()
    assert "ruang bukan sekadar dinding dan atap" not in script_text.lower()
