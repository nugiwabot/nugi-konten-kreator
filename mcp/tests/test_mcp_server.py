import pytest
from pathlib import Path
import sys
import tempfile
import shutil

# Ensure MCP directory and repo root are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_DIR = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

import security
from proposal_manager import ProposalManager
import server


def test_security_resolve_safe_path_valid():
    """Verify safe paths inside repo resolve correctly."""
    rel = "engine/pipeline/visual_requirements.py"
    safe = security.resolve_safe_path(REPO_ROOT, rel)
    assert safe.resolve() == (REPO_ROOT / rel).resolve()


def test_security_path_traversal_blocked():
    """Verify directory traversal is strictly blocked."""
    with pytest.raises(PermissionError):
        security.resolve_safe_path(REPO_ROOT, "../../Windows/System32")


def test_security_is_output_path():
    """Verify output path check."""
    out_file = REPO_ROOT / "output" / "test_project" / "broll" / "shot_001.mp4"
    engine_file = REPO_ROOT / "engine" / "pipeline" / "visual_requirements.py"
    assert security.is_output_path(REPO_ROOT, out_file) is True
    assert security.is_output_path(REPO_ROOT, engine_file) is False


def test_security_is_protected_path():
    """Verify protected path check."""
    engine_file = REPO_ROOT / "engine" / "pipeline" / "visual_requirements.py"
    out_file = REPO_ROOT / "output" / "test.txt"
    env_file = REPO_ROOT / ".env"
    assert security.is_protected_path(REPO_ROOT, engine_file) is True
    assert security.is_protected_path(REPO_ROOT, env_file) is True
    assert security.is_protected_path(REPO_ROOT, out_file) is False


def test_proposal_lifecycle(tmp_path):
    """Verify proposal propose, review, and apply workflow."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    (fake_repo / "engine").mkdir()
    target_file = fake_repo / "engine" / "sample.py"
    target_file.write_text("def hello():\n    return 'old'\n", encoding="utf-8")

    pm = ProposalManager(fake_repo)
    prop_res = pm.propose(
        target_files=["engine/sample.py"],
        reason="Upgrade greeting",
        requested_behavior="Return new greeting",
        new_contents={"engine/sample.py": "def hello():\n    return 'new'\n"},
    )
    assert prop_res["status"] == "ok"
    prop = prop_res["proposal"]
    assert prop["proposal_id"].startswith("chg_")
    assert "diff_preview" in prop_res
    # Target file unchanged before apply
    assert target_file.read_text(encoding="utf-8") == "def hello():\n    return 'old'\n"

    # Inspect
    insp = pm.inspect(prop["proposal_id"])
    assert insp["status"] == "ok"

    # Apply
    applied = pm.apply(prop["proposal_id"])
    assert applied["status"] == "ok"
    assert target_file.read_text(encoding="utf-8") == "def hello():\n    return 'new'\n"


def test_proposal_budget_warning(tmp_path):
    """Verify exceeding change budget triggers HIGH risk classification."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    files = [f"file_{i}.py" for i in range(7)]
    for f in files:
        (fake_repo / f).write_text("# code", encoding="utf-8")

    pm = ProposalManager(fake_repo, max_budget_files=5)
    prop_res = pm.propose(
        target_files=files,
        reason="Large change",
        requested_behavior="Refactor all files",
    )
    assert "EXCEEDS_CHANGE_BUDGET" in prop_res["proposal"]["risk"]


def test_mcp_repo_status():
    """Verify repo status tool."""
    res = server.repo_status()
    assert res["status"] == "ok"
    assert "repo_root" in res
    assert "git_status" in res


def test_mcp_editorial_classify():
    """Verify editorial topic classification tool."""
    res = server.editorial_classify_topic("Investasi ruko dan perubahan lanskap kota")
    assert res["status"] == "ok"
    assert "classification" in res


def test_mcp_visual_classify():
    """Verify visual classification tool."""
    res = server.visual_classify("Menara Eiffel dibangun pada tahun 1889 di Paris.")
    assert res["status"] == "ok"
    assert res["visual_requirement"] == "REAL_REQUIRED"
    assert any("1889" in str(e) or "Paris" in str(e) or "Menara Eiffel" in str(e) for e in res["entities"])


def test_mcp_media_find_signature_and_ranking(monkeypatch):
    """Verify media_find works properly with updated media parameter without crash."""
    from engine.pipeline.media_finder import MediaFinderResult, MediaFinderItem

    dummy_item = MediaFinderItem(
        rank=1,
        title="Pasar Tradisional Pagi",
        provider="wikimedia",
        media_type="photo",
        score=0.92,
        source_url="https://commons.wikimedia.org/wiki/File:Sample.jpg",
        download_url="https://upload.wikimedia.org/wikipedia/commons/sample.jpg",
        human_alignment_score=0.88,
        authenticity_score=0.90,
    )
    dummy_res = MediaFinderResult(
        request="pasar tradisional di pagi hari",
        media_type="photo",
        era="contemporary",
        style="documentary",
        queries=["pasar tradisional pagi"],
        providers_contacted=["wikimedia"],
        results=[dummy_item],
        total_candidates_found=1,
        usable_results=1,
    )
    monkeypatch.setattr("engine.pipeline.media_finder.MediaFinder.find", lambda self, *args, **kwargs: dummy_res)

    res = server.media_find(query="pasar tradisional di pagi hari", media="photo", count=3)
    assert res["status"] == "OK"
    assert "results" in res
    assert len(res["results"]) > 0
    # Check that human alignment or authenticity attributes exist
    first = res["results"][0]
    assert "human_alignment_score" in first
    assert "authenticity_score" in first


def test_mcp_visual_generate_shots_human_relatability():
    """Verify visual shot planning extracts human relatability metadata from naskah."""
    script = (
        "## SHORT 06 — Kenapa Kamar Tidur Dipisahkan?\n\n"
        "### 🪝 HOOK\nBayangin kalau rumah kita nggak punya kamar tidur.\n\n"
        "### 🔓 OPEN LOOP\nTapi sebenarnya kenapa kamar tidur dipisahkan?\n"
    )
    res = server.visual_generate_shots(script)
    assert res["status"] == "ok"
    assert res["total_shots"] > 0
    shot = res["shots"][0]
    assert "primary_human_basic_need" in shot
    assert "human_alignment_score" in shot
    assert shot["primary_human_basic_need"] in ("shelter", "autonomy", "safety", "health", "")


def test_mcp_question_mine(monkeypatch):
    """Verify question mining tool executes successfully."""
    dummy_res = {
        "metadata": {"total_queries": 10, "fingerprint": "abc123"},
        "clusters": [
            {"cluster_id": 1, "size": 3, "theme": "Kenapa manusia tidur", "queries": ["tidur malam"]}
        ]
    }
    monkeypatch.setattr("engine.editorial.question_mining.mine_questions", lambda **kwargs: dummy_res)
    res = server.question_mine(dataset="output/dummy.json", top_k=2, min_results=1)
    assert res["status"] == "ok"
    assert "metadata" in res
    assert res["clusters_found"] == 1


def test_mcp_doctor_media_has_providers():
    """Verify doctor_media reports all media provider diagnostic statuses."""
    res = server.doctor_media()
    assert res["status"] == "ok"
    assert "wikimedia" in res
    assert "internet_archive" in res
    assert "pexafy" in res


def test_mcp_capcut_environment_detection():
    """Verify doctor_video reports CapCut environment details."""
    res = server.doctor_video()
    assert res["status"] == "ok"
    assert "capcut_installed" in res
    assert "capcut_draft_dir" in res


def test_mcp_output_write_and_read():
    """Verify output tools operate safely in output/ without proposal."""
    test_rel = "test_scratch/sample_output.txt"
    w_res = server.output_write(test_rel, "Sample output content")
    assert w_res["status"] == "ok"
    assert len(w_res["files_created"]) > 0

    r_res = server.output_read(test_rel)
    assert r_res["status"] == "ok"
    assert "Sample output content" in r_res["content"]

    d_res = server.output_delete(test_rel)
    assert d_res["status"] == "ok"


def test_mcp_output_cannot_write_protected_files():
    """Verify output.write strictly prevents writing to protected paths outside output/."""
    with pytest.raises(Exception):
        server.output_write("../engine/pipeline/sample.py", "# malicious injection")
