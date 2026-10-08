"""
Tests for High-Level Unified MCP Orchestration Workflows.
"""
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = REPO_ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import server


def test_mcp_research_deep(tmp_path, monkeypatch, research_offline):
    monkeypatch.setattr(server, "REPO_ROOT", tmp_path)
    res = server.research_deep(
        topic="krisis keterjangkauan rumah",
        recency="w",
        max_evidence=2,
        output_dir=str(tmp_path / "research"),
    )
    assert res["status"] == "ok"
    assert res["epistemic_status"] == "UNVERIFIED"
    assert len(res["subquestions"]) >= 3
    assert res["key_findings"] == ["Tidak ada bukti yang dapat diverifikasi berhasil diambil pada sesi riset ini."]
    assert res["claims_count"] == 0
    assert res["evidence_strength"] == 0.0
    assert "dossier_json" in res
    assert "dossier_md" in res


def test_mcp_research_fact_check():
    sample_script = """
    # Kenapa Rumah Menjauh
    Berdasarkan data BPS, backlog kepemilikan rumah mencapai 9.9 juta unit.
    Satu-satunya penyebab krisis ini adalah mutlak karena spekulan tanah.
    Manusia membutuhkan rasa aman tempat tinggal untuk bertahan hidup.
    """
    res = server.research_fact_check(script_text_or_path=sample_script)
    assert res["status"] == "ok"
    assert res["overall_verdict"] == "DISPUTED"  # Causal overclaim flagged
    assert res["breakdown"]["disputed"] >= 1
    assert res["breakdown"]["verified"] == 0  # No BPS table was retrieved.
    assert res["pass_gate"] is False


def test_mcp_visual_research():
    sample_script = """# Konten Nugi
## 📽️ NARASI 1: SEJARAH KPR
### *Sejarah KPR di Indonesia*
- **Pilar DNA:** `HUMAN × PLACE × WHY`

#### NASKAH TALKING-HEAD
```text
[00:00 - 00:10] HOOK
Manusia purba hidup berpindah sebelum akhirnya membangun pemukiman pertama.

[00:10 - 00:30] CONTEXT & THE REAL DATA
Pada tahun 1976, skema KPR pertama resmi diperkenalkan di Indonesia.
```
"""
    res = server.visual_research(script_text_or_path=sample_script)
    assert res["status"] == "ok"
    assert res["total_shots_planned"] >= 1
    assert "shots" in res


def test_mcp_content_create_dry_run(tmp_path, monkeypatch, research_offline):
    monkeypatch.setattr(server, "REPO_ROOT", tmp_path)
    res = server.content_create(
        topic="Mengapa manusia membangun pemukiman",
        format="short",
        dry_run=True,
        stage_limit="script"
    )
    assert res["status"] == "ok"
    assert res["stage"] == "script"
    assert "script_file" in res
    assert "fact_check_verdict" in res
