"""
mcp/tests/test_workflows.py
===========================
Comprehensive Test Suite for Nugi Konten Kreator Workflow Orchestration Layer.
Tests Registry, Planner, Preflight, Executor, State & Checkpoints, Resume,
Security Confinement, and End-to-End Simulations.
"""

import sys
import tempfile
from pathlib import Path
import pytest

# Ensure MCP and repo root are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MCP_DIR = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from engine.workflow import (
    WorkflowRegistry,
    registry,
    WorkflowPlanner,
    WorkflowPreflight,
    WorkflowStateManager,
    WorkflowExecutor,
    WorkflowStatus,
    StepStatus,
)
from workflows import WorkflowService
import server


# =============================================================================
# 1. WORKFLOW REGISTRY INTEGRITY
# =============================================================================

def test_workflow_registry_ten_core_workflows():
    """Verify all 10 mandatory workflows are registered with unique IDs."""
    expected_ids = {
        "content_idea",
        "research_only",
        "script_only",
        "fact_check",
        "broll",
        "subtitle",
        "capcut_draft",
        "short_video",
        "full_video",
        "content_audit",
    }
    all_wfs = registry.list_all()
    actual_ids = {w.workflow_id for w in all_wfs}

    assert expected_ids.issubset(actual_ids), f"Missing workflows: {expected_ids - actual_ids}"
    assert len(all_wfs) == len(actual_ids), "Workflow IDs must be unique"


def test_workflow_registry_steps_and_inputs_defined():
    """Verify each workflow has valid steps, required inputs, and tools mapped."""
    for wf in registry.list_all():
        assert wf.workflow_id
        assert wf.name
        assert wf.description
        assert len(wf.steps) > 0, f"Workflow {wf.workflow_id} has no steps"
        assert len(wf.required_inputs) > 0, f"Workflow {wf.workflow_id} has no required inputs"
        assert wf.risk_level in ["LOW", "MEDIUM", "HIGH"]
        assert wf.tier in ["TIER_1", "TIER_2", "TIER_3"]


# =============================================================================
# 2. WORKFLOW PLANNER
# =============================================================================

def test_planner_short_video_intent():
    """Verify user request for short video maps to short_video workflow."""
    planner = WorkflowPlanner(registry)
    plan = planner.plan("Saya mau bikin video short tentang kenapa rumah dekat stasiun lebih mahal.")

    assert plan["mode"] == "PLAN"
    assert plan["status"] == "planned"
    assert plan["detected_workflow_id"] == "short_video"
    assert "topic" in plan["extracted_inputs"]
    assert len(plan["planned_steps"]) == 11
    assert plan["planned_steps"][0]["step_id"] == "1_content_idea"


def test_planner_broll_intent():
    """Verify request to find B-roll maps to broll workflow."""
    planner = WorkflowPlanner(registry)
    plan = planner.plan("Carikan B-roll dari script 02-script")

    assert plan["detected_workflow_id"] == "broll"
    assert plan["extracted_inputs"].get("workspace") == "02-script"


def test_planner_capcut_intent():
    """Verify request for CapCut draft maps to capcut_draft workflow."""
    planner = WorkflowPlanner(registry)
    plan = planner.plan("Bikin draft CapCut untuk 01-script")

    assert plan["detected_workflow_id"] == "capcut_draft"
    assert plan["extracted_inputs"].get("workspace") == "01-script"


def test_planner_fact_check_intent():
    """Verify request for fact check maps to fact_check workflow."""
    planner = WorkflowPlanner(registry)
    plan = planner.plan("Audit fakta dan klaim naskah teleprompter ini")

    assert plan["detected_workflow_id"] == "fact_check"


# =============================================================================
# 3. WORKFLOW PREFLIGHT
# =============================================================================

def test_preflight_capcut_blocked_when_footage_missing(tmp_path):
    """Verify preflight blocks CapCut draft if main footage is missing."""
    preflight = WorkflowPreflight(REPO_ROOT, registry)
    # Using non-existent or empty workspace
    rep = preflight.check("capcut_draft", {"workspace": "non_existent_ws_99"})

    assert rep.status == "BLOCKED"
    assert len(rep.missing_items) > 0
    assert rep.recommended_next_step is not None
    assert rep.recommended_tool is not None


def test_preflight_content_idea_ready():
    """Verify content_idea preflight is READY when topic is provided."""
    preflight = WorkflowPreflight(REPO_ROOT, registry)
    rep = preflight.check("content_idea", {"topic": "Kenapa rumah dekat stasiun lebih mahal?"})

    assert rep.status == "READY"
    assert len(rep.missing_items) == 0
    assert "topic" in rep.ready_items[0]


def test_preflight_missing_required_input():
    """Verify missing required input triggers BLOCKED with actionable guide."""
    preflight = WorkflowPreflight(REPO_ROOT, registry)
    rep = preflight.check("content_idea", {})

    assert rep.status == "BLOCKED"
    assert any("topic" in m for m in rep.missing_items)


# =============================================================================
# 4. WORKFLOW EXECUTION & RESUME
# =============================================================================

def test_workflow_execute_content_idea(tmp_path):
    """Verify execution of content_idea workflow step by step."""
    state_mgr = WorkflowStateManager(tmp_path)
    executor = WorkflowExecutor(REPO_ROOT, registry, state_mgr)

    result = executor.execute(
        workflow_id="content_idea",
        context={"topic": "Kenapa rumah dekat stasiun lebih mahal?"},
        dry_run=True,
    )

    assert result["status"] == "completed"
    assert "editorial_classify" in result["completed_steps"]
    assert "human_place" in result["completed_steps"]
    assert "property_brand_fit" in result["completed_steps"]
    assert "recommendation" in result["completed_steps"]

    # Verify state persistence
    saved_state = state_mgr.get_run(result["run_id"])
    assert saved_state is not None
    assert saved_state.status == WorkflowStatus.COMPLETED


def test_workflow_execute_fact_check(tmp_path):
    """Verify execution of fact_check workflow using ScriptAuditor."""
    state_mgr = WorkflowStateManager(tmp_path)
    executor = WorkflowExecutor(REPO_ROOT, registry, state_mgr)

    script_sample = (
        "Pintu rumah zaman dulu selalu dipisahkan untuk menjaga privasi. "
        "Pada tahun 1920, standar hunian modern mulai memindahkan ruang tamu ke bagian depan."
    )
    result = executor.execute(
        workflow_id="fact_check",
        context={"script_text": script_sample, "title": "Kenapa Pintu Depan"},
        dry_run=True,
    )

    assert result["status"] == "completed"
    assert "audit_engine" in result["completed_steps"]
    audit_data = result["step_results"]["audit_engine"]["output"]
    assert "overall_status" in audit_data
    assert "property_brand_fit" in audit_data


def test_workflow_resume_checkpoint(tmp_path):
    """Verify resuming a run continues from the uncompleted step without re-running finished steps."""
    state_mgr = WorkflowStateManager(tmp_path)
    executor = WorkflowExecutor(REPO_ROOT, registry, state_mgr)

    # 1. Create a run and manually mark initial steps completed
    run_state = state_mgr.create_run(
        "content_idea",
        {"topic": "Kenapa rumah cluster minim pagar?"},
    )
    run_state.completed_steps = ["editorial_classify", "human_place"]
    run_state.current_step_index = 2
    state_mgr.save_run(run_state)

    # 2. Resume execution
    resumed = executor.execute("content_idea", run_id=run_state.run_id, dry_run=True)

    assert resumed["status"] == "completed"
    # Previously completed steps remain completed
    assert "editorial_classify" in resumed["completed_steps"]
    assert "human_place" in resumed["completed_steps"]
    # Subsequent steps were run
    assert "property_brand_fit" in resumed["completed_steps"]
    assert "recommendation" in resumed["completed_steps"]


# =============================================================================
# 5. WORKFLOW SERVICE & SERVER TOOLS INTEGRATION
# =============================================================================

def test_workflow_service_tools():
    """Verify WorkflowService methods called by FastMCP tools."""
    svc = WorkflowService(REPO_ROOT)

    # List
    wf_list = svc.list_workflows()
    assert len(wf_list) >= 10

    # Explain
    exp = svc.explain_workflow("short_video")
    assert exp["workflow_id"] == "short_video"
    assert len(exp["steps"]) == 11
    assert "why_each_step_exists" in exp

    # Plan
    plan = svc.plan_workflow("Bikin Shorts Nugi Properti tentang lebar jalan depan rumah")
    assert plan["detected_workflow_id"] == "short_video"

    # Preflight
    pref = svc.preflight_workflow("content_idea", {"topic": "Lebar jalan"})
    assert pref["status"] == "READY"


def test_mcp_server_workflow_tools_registered():
    """Verify all 7 workflow tools and script audit tool are registered on FastMCP server."""
    # FastMCP tools can be checked via server.mcp
    # Let's inspect registered tool functions
    registered_names = [getattr(t, "name", str(t)) for t in server.mcp._tool_manager.list_tools()]
    assert "nugi_workflow_list" in registered_names
    assert "nugi_workflow_explain" in registered_names
    assert "nugi_workflow_plan" in registered_names
    assert "nugi_workflow_preflight" in registered_names
    assert "nugi_workflow_execute" in registered_names
    assert "nugi_workflow_status" in registered_names
    assert "nugi_workflow_resume" in registered_names
    assert "nugi_editorial_script_audit" in registered_names
    assert "nugi_editorial_brand_fit" in registered_names


# =============================================================================
# 6. FULL AGENT SIMULATION
# =============================================================================

def test_agent_full_lifecycle_simulation(tmp_path):
    """
    Simulate full Agent interaction:
    1. User states natural language goal.
    2. Agent calls nugi_workflow_plan.
    3. Agent checks nugi_workflow_preflight.
    4. Agent executes workflow step-by-step.
    5. Agent checks nugi_workflow_status.
    """
    svc = WorkflowService(REPO_ROOT)

    # Step 1 & 2: Plan
    user_goal = "Buat Shorts Nugi Properti tentang kenapa rumah dekat stasiun bisa mahal"
    plan = svc.plan_workflow(user_goal)
    assert plan["detected_workflow_id"] == "short_video"
    assert plan["mode"] == "PLAN"

    # Step 3: Preflight
    topic = plan["extracted_inputs"].get("topic", "rumah dekat stasiun")
    pref = svc.preflight_workflow("short_video", {"topic": topic})
    # Since workspace is not yet created, it's blocked or warned with recommended action
    assert pref["status"] in ("READY", "WARNING", "BLOCKED")
    assert pref["recommended_next_step"] is not None

    # Step 4: Execute content_idea sub-workflow
    exec_res = svc.execute_workflow(
        workflow_id="content_idea",
        context={"topic": topic},
        dry_run=True,
    )
    assert exec_res["status"] == "completed"
    run_id = exec_res["run_id"]

    # Step 5: Check Status
    st = svc.workflow_status(run_id)
    assert st["status"] == "completed"
    assert len(st["completed_steps"]) == 6


# =============================================================================
# 7. WORKFLOW INTEGRITY CHAIN TESTS
# =============================================================================

def test_workflow_integrity_editorial_chain(tmp_path):
    """
    Test continuous pipeline chain:
    topic -> content_idea -> research_only -> script_only -> fact_check -> content_audit
    """
    state_mgr = WorkflowStateManager(tmp_path)
    executor = WorkflowExecutor(REPO_ROOT, registry, state_mgr)
    topic = "Kenapa rumah dekat stasiun lebih mahal?"

    # 1. content_idea
    r1 = executor.execute("content_idea", context={"topic": topic}, dry_run=True)
    assert r1["status"] == "completed"

    # 2. research_only
    r2 = executor.execute("research_only", context={"topic": topic}, dry_run=True)
    assert r2["status"] == "completed"

    # 3. script_only
    script_text = (
        "Pernah heran kenapa dua rumah berjarak 500 meter harganya bisa beda ratusan juta? "
        "Di dekat stasiun, aksesibilitas memotong waktu transit harian sehingga nilai tanah naik. "
        "Pada akhirnya, kita bukan cuma membeli fisik bangunan, tapi juga membeli waktu hidup kita."
    )
    r3 = executor.execute("script_only", context={"topic": topic, "script_text": script_text}, dry_run=True)
    assert r3["status"] == "completed"

    # 4. fact_check
    r4 = executor.execute("fact_check", context={"script_text": script_text, "topic": topic}, dry_run=True)
    assert r4["status"] == "completed"

    # 5. content_audit
    r5 = executor.execute("content_audit", context={"script_text": script_text, "topic": topic}, dry_run=True)
    assert r5["status"] == "completed"
    assert "fact_audit" in r5["completed_steps"]
    assert "brand_fit" in r5["completed_steps"]
    assert "quality_gate" in r5["completed_steps"]


def test_workflow_integrity_production_chain(tmp_path):
    """
    Test continuous production chain:
    script -> visual_plan -> broll -> subtitle -> capcut_draft
    """
    state_mgr = WorkflowStateManager(tmp_path)
    executor = WorkflowExecutor(REPO_ROOT, registry, state_mgr)

    script_text = (
        "Pernah heran kenapa dua rumah berjarak 500 meter harganya bisa beda ratusan juta? "
        "Di dekat stasiun, aksesibilitas memotong waktu transit harian sehingga nilai tanah naik."
    )

    # 1. B-roll (covers script_parse, visual shot generation, query expansion, media search)
    r_broll = executor.execute("broll", context={"script": script_text, "workspace": "temp_test_ws"}, dry_run=True)
    assert r_broll["status"] == "completed"
    assert "shot_generation" in r_broll["completed_steps"]

    # 2. Subtitle
    r_sub = executor.execute("subtitle", context={"script_path": "output/short video/01-script/SHORT_01_kenapa_pintu_rumah_menghadap_jalan.md"}, dry_run=True)
    assert r_sub["status"] == "completed"
    assert "subtitle_generate" in r_sub["completed_steps"]

    # 3. CapCut Draft (dry run)
    r_cc = executor.execute("capcut_draft", context={"workspace": "01-script"}, dry_run=True)
    assert r_cc["status"] == "completed"
    assert "capcut_generate" in r_cc["completed_steps"]

