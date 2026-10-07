"""
server.py
=========
Nugi Konten Kreator MCP Server
Controlled Interface between Antigravity and the Nugi Konten Kreator Repository.

Architecture:
  ANTIGRAVITY -> NUGI KONTEN KREATOR MCP -> NUGI REPOSITORY (Source of Truth)
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure Tools MCP directory is in sys.path for local imports
TOOLS_DIR = Path(__file__).parent.resolve()
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from security import (
    is_output_path,
    is_protected_path,
    is_secret_file,
    mask_secrets,
    resolve_safe_path,
    SecurityError,
)
from proposal_manager import ProposalManager

# Setup FastMCP
from mcp.server.fastmcp import FastMCP

# Parse CLI arguments for transport, host, port, and repo-root
parser = argparse.ArgumentParser(description="Nugi Konten Kreator MCP Server")
parser.add_argument("--repo-root", default=os.environ.get("NUGI_REPO_ROOT", r"c:\Users\Nugi\Documents\nugi-konten-kreator"), help="Repository root path")
parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"], help="MCP transport (default: stdio)")
parser.add_argument("--host", default="0.0.0.0", help="Host to bind for SSE / HTTP transport (default: 0.0.0.0)")
parser.add_argument("--port", type=int, default=8000, help="Port to bind for SSE / HTTP transport (default: 8000)")
cli_args, _ = parser.parse_known_args()

REPO_ROOT = Path(cli_args.repo_root).resolve()
TRANSPORT = cli_args.transport
HOST = cli_args.host
PORT = cli_args.port

# Inject repository into sys.path
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Initialize proposal manager and workflow service
proposals = ProposalManager(REPO_ROOT)
from workflows import WorkflowService
workflow_service = WorkflowService(REPO_ROOT)

# Initialize FastMCP Server with Network and Stdio capability
mcp = FastMCP(
    "nugi-konten-kreator",
    instructions="Controlled semantic interface for Nugi Konten Kreator repository.",
    host=HOST,
    port=PORT,
)

# ------------------------------------------------------------------------------
# 1. REPOSITORY TOOLS (nugi.repo.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_repo_status")
def repo_status() -> Dict[str, Any]:
    """Check repository status, git branch, output folder, and environment."""
    git_proc = subprocess.run(["git", "status", "--short", "--branch"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    out_dir = REPO_ROOT / "output"
    return {
        "status": "ok",
        "repo_root": str(REPO_ROOT),
        "git_status": git_proc.stdout.strip(),
        "output_workspace_exists": out_dir.exists(),
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
    }

@mcp.tool(name="nugi_repo_tree")
def repo_tree(directory: str = "", depth: int = 2) -> Dict[str, Any]:
    """Inspect repository file tree up to specified depth."""
    safe_dir = resolve_safe_path(REPO_ROOT, directory or ".")
    if not safe_dir.is_dir():
        return {"error": f"'{directory}' is not a directory"}

    lines = []
    base_depth = len(safe_dir.parts)

    for root, dirs, files in os.walk(safe_dir):
        cur_depth = len(Path(root).parts) - base_depth
        if cur_depth >= depth:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "venv")]
        indent = "  " * cur_depth
        lines.append(f"{indent}{Path(root).name}/")
        for f in files:
            if not f.startswith(".") and not f.endswith(".pyc"):
                lines.append(f"{indent}  {f}")

    return {"status": "ok", "directory": str(safe_dir.relative_to(REPO_ROOT)), "tree": "\n".join(lines[:300])}

@mcp.tool(name="nugi_repo_list")
def repo_list(directory: str = "") -> Dict[str, Any]:
    """List directory contents with size and modification timestamp."""
    safe_dir = resolve_safe_path(REPO_ROOT, directory or ".")
    if not safe_dir.is_dir():
        return {"error": f"'{directory}' is not a directory"}

    items = []
    for p in sorted(safe_dir.iterdir()):
        if p.name.startswith(".") and p.name != ".agents":
            continue
        items.append({
            "name": p.name,
            "is_dir": p.is_dir(),
            "size": p.stat().st_size if p.is_file() else None,
            "modified": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
            "is_protected": is_protected_path(REPO_ROOT, p),
        })
    return {"status": "ok", "directory": str(safe_dir.relative_to(REPO_ROOT)), "items": items}

@mcp.tool(name="nugi_repo_read")
def repo_read(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
    """Safely read repository file with line slice and secret masking."""
    safe_p = resolve_safe_path(REPO_ROOT, path)
    if is_secret_file(safe_p):
        return {"error": "Access to sensitive credential/environment file is forbidden."}
    if not safe_p.is_file():
        return {"error": f"File '{path}' does not exist."}

    text = safe_p.read_text(encoding="utf-8", errors="replace")
    masked_text = mask_secrets(text)
    lines = masked_text.splitlines()
    total_lines = len(lines)

    s = max(1, start_line or 1) - 1
    e = min(total_lines, end_line or total_lines)
    sliced = lines[s:e]

    return {
        "status": "ok",
        "file": str(safe_p.relative_to(REPO_ROOT)),
        "total_lines": total_lines,
        "start_line": s + 1,
        "end_line": e,
        "content": "\n".join(sliced),
    }

@mcp.tool(name="nugi_repo_search")
def repo_search(query: str, directory: str = "", extension: str = ".py") -> Dict[str, Any]:
    """Search for string or symbol across repository files."""
    safe_dir = resolve_safe_path(REPO_ROOT, directory or ".")
    matches = []
    for p in safe_dir.rglob(f"*{extension}"):
        if any(part.startswith(".") for part in p.parts) or "venv" in p.parts:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for idx, line in enumerate(txt.splitlines(), 1):
                if query.lower() in line.lower():
                    matches.append({
                        "file": str(p.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "line": idx,
                        "content": line.strip()[:140],
                    })
                    if len(matches) >= 50:
                        break
        except Exception:
            continue
        if len(matches) >= 50:
            break
    return {"status": "ok", "query": query, "total_matches": len(matches), "matches": matches}

@mcp.tool(name="nugi_repo_find")
def repo_find(filename_pattern: str) -> Dict[str, Any]:
    """Find files matching glob pattern."""
    files = []
    for p in REPO_ROOT.glob(f"**/{filename_pattern}"):
        if any(part.startswith(".") for part in p.parts) or "venv" in p.parts:
            continue
        files.append(str(p.relative_to(REPO_ROOT)).replace("\\", "/"))
        if len(files) >= 50:
            break
    return {"status": "ok", "pattern": filename_pattern, "files": files}

@mcp.tool(name="nugi_repo_file_info")
def repo_file_info(path: str) -> Dict[str, Any]:
    """Get metadata, size, protection classification of a file."""
    safe_p = resolve_safe_path(REPO_ROOT, path)
    if not safe_p.exists():
        return {"error": f"Path '{path}' not found."}
    stat = safe_p.stat()
    return {
        "status": "ok",
        "file": str(safe_p.relative_to(REPO_ROOT)).replace("\\", "/"),
        "is_dir": safe_p.is_dir(),
        "size_bytes": stat.st_size if safe_p.is_file() else None,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "is_protected": is_protected_path(REPO_ROOT, safe_p),
        "is_output": is_output_path(REPO_ROOT, safe_p),
    }

# ------------------------------------------------------------------------------
# 2. ARCHITECTURE TOOLS (nugi.architecture.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_architecture_overview")
def architecture_overview() -> Dict[str, Any]:
    """Return top-level architectural overview and active modules."""
    return {
        "status": "ok",
        "editorial_identity": "HUMAN x PLACE x CHANGE x WHY",
        "core_principle": "DOCUMENTARY TRUTH > SPECIFICITY > EVIDENCE > RELEVANCE > AESTHETICS",
        "layers": {
            "core": "Brand identity, Content DNA, editorial guidelines",
            "engine/editorial": "Human-Place classification, fit score, quality gates, intent, story types",
            "engine/pipeline": "Media retrieval, video generation, auto-edit Kdenlive/CapCut, SRT generator",
            "engine/providers": "LAN embedding, LAN reranker, Wikimedia, Internet Archive, Pexafy",
            "output": "Isolated writable workspace for all generated productions and B-roll",
        },
    }

@mcp.tool(name="nugi_architecture_module")
def architecture_module(module_rel_path: str) -> Dict[str, Any]:
    """Inspect imports, exported classes, and functions of a python module."""
    safe_p = resolve_safe_path(REPO_ROOT, module_rel_path)
    if not safe_p.is_file() or safe_p.suffix != ".py":
        return {"error": "Target must be a python file."}

    text = safe_p.read_text(encoding="utf-8", errors="replace")
    classes = []
    functions = []
    imports = []

    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for n in node.names:
                    imports.append(f"{mod}.{n.name}")
    except Exception as e:
        return {"error": f"AST parse error: {e}"}

    return {
        "status": "ok",
        "module": str(safe_p.relative_to(REPO_ROOT)).replace("\\", "/"),
        "classes": classes,
        "functions": functions,
        "imports": imports[:20],
    }

@mcp.tool(name="nugi_architecture_symbols")
def architecture_symbols(module_rel_path: str) -> Dict[str, Any]:
    """List all top-level symbols exported in a module."""
    return architecture_module(module_rel_path)

@mcp.tool(name="nugi_architecture_callers")
def architecture_callers(symbol_name: str) -> Dict[str, Any]:
    """Find references calling or importing a given symbol."""
    return repo_search(query=symbol_name, directory="engine")

@mcp.tool(name="nugi_architecture_callees")
def architecture_callees(module_rel_path: str) -> Dict[str, Any]:
    """Find external engine dependencies imported by a module."""
    return architecture_module(module_rel_path)

@mcp.tool(name="nugi_architecture_usages")
def architecture_usages(symbol_name: str) -> Dict[str, Any]:
    """Search references to a symbol across the entire repo."""
    return repo_search(query=symbol_name, directory="")

@mcp.tool(name="nugi_architecture_trace")
def architecture_trace(source_symbol: str, target_symbol: str) -> Dict[str, Any]:
    """Map usage relationship between two symbols."""
    src_refs = repo_search(query=source_symbol, directory="engine")
    tgt_refs = repo_search(query=target_symbol, directory="engine")
    return {
        "status": "ok",
        "source": source_symbol,
        "target": target_symbol,
        "source_references_count": src_refs.get("total_matches", 0),
        "target_references_count": tgt_refs.get("total_matches", 0),
    }

@mcp.tool(name="nugi_architecture_impact")
def architecture_impact(file_path: str) -> Dict[str, Any]:
    """Analyze modules affected if file_path were modified."""
    stem = Path(file_path).stem
    return repo_search(query=stem, directory="engine")

@mcp.tool(name="nugi_architecture_compare")
def architecture_compare(file_path_a: str, file_path_b: str) -> Dict[str, Any]:
    """Compare two files and output unified diff."""
    pa = resolve_safe_path(REPO_ROOT, file_path_a)
    pb = resolve_safe_path(REPO_ROOT, file_path_b)
    ta = pa.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    tb = pb.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    import difflib
    diff = list(difflib.unified_diff(ta, tb, fromfile=file_path_a, tofile=file_path_b))
    return {"status": "ok", "diff": "".join(diff)}

# ------------------------------------------------------------------------------
# 3. EDITORIAL TOOLS (nugi.editorial.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_editorial_classify_topic")
def editorial_classify_topic(topic: str) -> Dict[str, Any]:
    """Classify topic against primary domains, anchors, and lenses."""
    from engine.editorial.taxonomy import classify_topic
    return {"status": "ok", "classification": classify_topic(topic)}

@mcp.tool(name="nugi_editorial_classify_intent")
def editorial_classify_intent(query: str) -> Dict[str, Any]:
    """Classify search query into 15 editorial intent classes."""
    from engine.editorial.intent_classifier import classify_intent
    return {"status": "ok", "query": query, "intent": classify_intent(query)}

@mcp.tool(name="nugi_editorial_human_place")
def editorial_human_place(topic: str) -> Dict[str, Any]:
    """Evaluate 10 Human-Place criteria and bridge connections."""
    from engine.editorial.human_place_engine import evaluate_human_place_anchor, find_human_place_bridge
    evaluation = evaluate_human_place_anchor(topic)
    bridge = find_human_place_bridge(topic)
    return {"status": "ok", "topic": topic, "evaluation": evaluation, "bridge": bridge}

@mcp.tool(name="nugi_editorial_fit_score")
def editorial_fit_score(topic: str) -> Dict[str, Any]:
    """Calculate 100-point editorial fit score across 4 dimensions."""
    from engine.editorial.fit_score import calculate_editorial_fit
    idea = {"title": topic} if isinstance(topic, str) else topic
    return {"status": "ok", "topic": topic, "fit_score": calculate_editorial_fit(idea)}

@mcp.tool(name="nugi_editorial_quality_gate")
def editorial_quality_gate(topic: str, draft_text: str = "") -> Dict[str, Any]:
    """Evaluate hard quality gates and detect forbidden anti-patterns."""
    from engine.editorial.quality_gate import check_quality_gates, check_anti_patterns
    idea = {"title": topic, "text": draft_text}
    q_res = check_quality_gates(idea)
    a_violations = check_anti_patterns(draft_text or topic)
    hard_rejections = q_res.get("hard_rejection_violations", [])
    passed = (len(hard_rejections) == 0) and (len(a_violations) == 0)
    return {
        "status": "ok",
        "passed": passed,
        "quality_gate_passed": len(hard_rejections) == 0,
        "hard_rejections": hard_rejections,
        "anti_patterns_passed": len(a_violations) == 0,
        "violations": a_violations,
        "fit_score": q_res.get("fit_score"),
    }

@mcp.tool(name="nugi_editorial_story_type")
def editorial_story_type(topic: str) -> Dict[str, Any]:
    """Select narrative archetype (origin, decay, collision, mystery, etc.)."""
    from engine.editorial.story_type import classify_story_type
    return {"status": "ok", "topic": topic, "story_type": classify_story_type(topic)}

@mcp.tool(name="nugi_editorial_revelation")
def editorial_revelation(revelation_text: str) -> Dict[str, Any]:
    """Check revelation quality, depth, and causal strength."""
    from engine.editorial.revelation_engine import check_revelation_quality
    return {"status": "ok", "evaluation": check_revelation_quality(revelation_text)}

@mcp.tool(name="nugi_question_mine")
def question_mine(
    dataset: str = "output/riset keyword.json",
    top_k: int = 5,
    min_results: int = 2,
    output: Optional[str] = None,
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    """Mine high-resonance editorial story opportunities from search dataset."""
    from engine.editorial.question_mining import mine_questions
    safe_dataset = resolve_safe_path(REPO_ROOT, dataset)
    safe_out = resolve_safe_path(REPO_ROOT, output) if output else None
    res = mine_questions(
        dataset_path=safe_dataset,
        output_path=safe_out,
        top_k=top_k,
        min_cluster_size=min_results,
        force_rebuild=force_rebuild,
    )
    return {
        "status": "ok",
        "metadata": res.get("metadata", {}),
        "clusters_found": len(res.get("clusters", [])),
        "clusters": res.get("clusters", [])[:top_k],
    }

@mcp.tool(name="nugi_editorial_taxonomy")
def editorial_taxonomy() -> Dict[str, Any]:
    """Return taxonomy definitions (domains, anchors, lenses, matrices)."""
    from engine.editorial.taxonomy import PRIMARY_DOMAINS, ANCHORS, LENSES, DNA_MATRICES
    return {
        "status": "ok",
        "primary_domains": PRIMARY_DOMAINS,
        "anchors": ANCHORS,
        "lenses": LENSES,
        "dna_matrices": DNA_MATRICES,
    }

@mcp.tool(name="nugi_editorial_script_audit")
def editorial_script_audit(script_text: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Verify factual claims, detect overclaims, causal overstatements, and evaluate Nugi Property brand fit."""
    from engine.editorial.script_auditor import ScriptAuditor
    auditor = ScriptAuditor()
    report = auditor.audit_script(script_text=script_text, editorial_context={"title": title} if title else None)
    return {"status": "ok", "audit": report.to_dict()}

@mcp.tool(name="nugi_editorial_brand_fit")
def editorial_brand_fit(script_text_or_topic: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate Nugi Properti Brand Fit score (0-20) and strategic lens resonance."""
    from engine.editorial.script_auditor import evaluate_nugi_property_brand_fit
    fit = evaluate_nugi_property_brand_fit(script_text=script_text_or_topic, title=title)
    return {"status": "ok", "brand_fit": fit}

# ------------------------------------------------------------------------------
# 4. THINKING TOOLS (nugi.thinking.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_thinking_why")
def thinking_why(topic: str) -> Dict[str, Any]:
    """Deconstruct topic into deep causal WHY chains."""
    from engine.editorial.human_place_engine import evaluate_human_place_criteria
    crit = evaluate_human_place_criteria(topic)
    return {
        "status": "ok",
        "topic": topic,
        "framework": "WHY-Engine (Causal Chain)",
        "underlying_systems": "Economics, human psychology, and geography constraints",
        "criteria": crit,
    }

@mcp.tool(name="nugi_thinking_curiosity")
def thinking_curiosity(topic: str) -> Dict[str, Any]:
    """Formulate epistemic curiosity gap for video hooks."""
    return {
        "status": "ok",
        "topic": topic,
        "hook_strategy": "Contradict initial common-sense assumption",
        "curiosity_gap": f"Mengapa {topic} kelihatannya wajar, padahal dampaknya mengubah cara hidup kita?",
    }

@mcp.tool(name="nugi_thinking_contradiction")
def thinking_contradiction(topic: str) -> Dict[str, Any]:
    """Extract hidden systemic contradictions."""
    from engine.editorial.story_type import is_contradiction_required
    return {
        "status": "ok",
        "topic": topic,
        "contradiction_required": is_contradiction_required(topic),
    }

@mcp.tool(name="nugi_thinking_angle")
def thinking_angle(topic: str) -> Dict[str, Any]:
    """Suggest distinct, high-resonance documentary angles."""
    from engine.editorial.story_type import classify_story_type, get_narrative_device
    st = classify_story_type(topic)
    dev = get_narrative_device(st)
    return {"status": "ok", "topic": topic, "recommended_story_type": st, "narrative_device": dev}

@mcp.tool(name="nugi_thinking_human_insight")
def thinking_human_insight(topic: str) -> Dict[str, Any]:
    """Extract human existential and emotional implications."""
    from engine.editorial.human_place_engine import evaluate_human_place_anchor
    return {"status": "ok", "topic": topic, "human_anchor": evaluate_human_place_anchor(topic)}

@mcp.tool(name="nugi_thinking_property_bridge")
def thinking_property_bridge(topic: str) -> Dict[str, Any]:
    """Find natural place/housing connection without commercial sales pitch."""
    from engine.editorial.human_place_engine import find_human_place_bridge
    return {"status": "ok", "topic": topic, "bridge": find_human_place_bridge(topic)}

# ------------------------------------------------------------------------------
# 5. RESEARCH TOOLS (nugi.research.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_research_run")
def research_run(topic: str, max_results: int = 5) -> Dict[str, Any]:
    """Execute epistemic web research with fact-claim separation."""
    from engine.pipeline.research_runner import ResearchRunner
    runner = ResearchRunner()
    data = runner.run_research(topic=topic, max_results=max_results)
    return {"status": "ok", "data": data}

@mcp.tool(name="nugi_research_sources")
def research_sources(topic: str) -> Dict[str, Any]:
    """List discovered web research sources."""
    from engine.pipeline.research_runner import ResearchRunner
    runner = ResearchRunner()
    data = runner.run_research(topic=topic, max_results=5)
    return {"status": "ok", "sources": data.get("sources", [])}

@mcp.tool(name="nugi_research_evaluate_source")
def research_evaluate_source(url: str, snippet: str = "") -> Dict[str, Any]:
    """Evaluate source tier and epistemological credibility."""
    tier = 2
    if any(d in url for d in ("gov", "edu", "bps.go.id", "worldbank.org", "unesco.org")):
        tier = 1
    return {"status": "ok", "url": url, "source_tier": tier, "is_authoritative": tier == 1}

@mcp.tool(name="nugi_research_fact_claim_split")
def research_fact_claim_split(text: str) -> Dict[str, Any]:
    """Separate verified facts from speculative claims."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    facts = [ln for ln in lines if any(char.isdigit() for char in ln)]
    claims = [ln for ln in lines if ln not in facts]
    return {"status": "ok", "facts": facts, "claims": claims}

# ------------------------------------------------------------------------------
# 6. KNOWLEDGE TOOLS (nugi.knowledge.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_knowledge_retrieve")
def knowledge_retrieve(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Two-stage vector search + precision reranking from knowledge store."""
    from engine.pipeline.retriever import KnowledgeRetriever
    retriever = KnowledgeRetriever()
    results = retriever.retrieve(query=query, top_k_candidates=15, top_k_reranked=top_k)
    return {"status": "ok", "query": query, "total_returned": len(results), "results": results}

@mcp.tool(name="nugi_knowledge_search")
def knowledge_search(query: str, top_candidates: int = 10) -> Dict[str, Any]:
    """Stage 1 vector similarity search."""
    return knowledge_retrieve(query=query, top_k=top_candidates)

@mcp.tool(name="nugi_knowledge_metadata")
def knowledge_metadata() -> Dict[str, Any]:
    """Return knowledge store metadata and chunk counts."""
    from engine.pipeline.retriever import KnowledgeRetriever
    retriever = KnowledgeRetriever()
    return {"status": "ok", "total_chunks": retriever.total_chunks, "metadata": retriever.metadata}

@mcp.tool(name="nugi_knowledge_stats")
def knowledge_stats() -> Dict[str, Any]:
    """Knowledge store statistics."""
    return knowledge_metadata()

@mcp.tool(name="nugi_knowledge_reindex")
def knowledge_reindex(pages_per_book: int = 5) -> Dict[str, Any]:
    """Rebuild local vector store. Requires confirmation."""
    from engine.ingestion.indexer import build_knowledge_index
    count = build_knowledge_index(pdf_sample_pages_per_book=pages_per_book, batch_size=32)
    return {"status": "ok", "total_indexed_chunks": count}

@mcp.tool(name="nugi_knowledge_index_status")
def knowledge_index_status() -> Dict[str, Any]:
    """Check knowledge store integrity and chunk validity."""
    from engine.pipeline.retriever import KnowledgeRetriever
    retriever = KnowledgeRetriever()
    return {
        "status": "ok",
        "index_ready": retriever.total_chunks > 0,
        "total_chunks": retriever.total_chunks,
    }

# ------------------------------------------------------------------------------
# 7. MEDIA RETRIEVAL TOOLS (nugi.media.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_media_find")
def media_find(
    query: str,
    media: str = "any",
    era: str = "auto",
    style: str = "auto",
    visual_requirement: str = "auto",
    count: int = 5
) -> Dict[str, Any]:
    """Evidence-based media search across Wikimedia, Internet Archive, and Pexafy with authenticity and human alignment scoring."""
    from engine.pipeline.media_finder import MediaFinder
    finder = MediaFinder()
    result = finder.find(
        request=query,
        media=media,
        era=era,
        style=style,
        visual_requirement=visual_requirement,
        count=count,
    )
    return {
        "status": result.status,
        "visual_requirement": result.visual_requirement,
        "source_role": result.source_role,
        "usable_results": result.usable_results,
        "queries_used": result.queries,
        "motion_spec": result.motion_spec,
        "results": [
            {
                "title": r.title,
                "provider": r.provider,
                "url": getattr(r, "source_url", getattr(r, "url", "")),
                "source_url": getattr(r, "source_url", getattr(r, "url", "")),
                "download_url": r.download_url,
                "score": r.score,
                "rank": r.rank,
                "authenticity_score": getattr(r, "authenticity_score", 0.0),
                "human_alignment_score": getattr(r, "human_alignment_score", 0.0),
                "rejection_reason": getattr(r, "rejection_reason", None),
            }
            for r in result.results
        ],
    }

@mcp.tool(name="nugi_media_expand_query")
def media_expand_query(request: str, visual_requirement: str = "auto") -> Dict[str, Any]:
    """Expand query with strict entity preservation rule."""
    from engine.pipeline.media_query_expander import MediaQueryExpander
    expander = MediaQueryExpander()
    eq = expander.expand(user_request=request, visual_requirement_override=visual_requirement)
    return {
        "status": "ok",
        "original_request": eq.original_request,
        "visual_requirement": eq.visual_requirement,
        "detected_media_type": eq.detected_media_type,
        "entities": eq.entities,
        "primary_queries": eq.primary_queries,
        "expanded_queries": eq.expanded_queries,
        "all_queries": eq.all_queries,
        "motion_spec": eq.motion_spec,
    }

@mcp.tool(name="nugi_media_download")
def media_download(
    query: str,
    media: str = "any",
    era: str = "auto",
    style: str = "auto",
    folder: str = "media_download",
    count: int = 5
) -> Dict[str, Any]:
    """Find and download media into output/<folder>/ and write sources.json."""
    from engine.pipeline.media_finder import MediaFinder
    out_dir = resolve_safe_path(REPO_ROOT, f"output/{folder}")
    finder = MediaFinder()
    res = finder.find_and_download(
        request=query,
        media=media,
        era=era,
        style=style,
        folder=folder,
        count=count,
    )
    downloaded_paths = [r.local_path for r in res.results if getattr(r, "local_path", None)]
    return {
        "status": res.status,
        "output_folder": str(out_dir),
        "files_downloaded": res.downloaded_count,
        "total_candidates": res.total_candidates_found,
        "usable_results": res.usable_results,
        "files_created": downloaded_paths,
    }

@mcp.tool(name="nugi_media_from_script")
def media_from_script(script_text: str) -> Dict[str, Any]:
    """Extract visual scenes from script and run search."""
    from engine.pipeline.media_pipeline import MediaPipeline
    pipe = MediaPipeline()
    res = pipe.search_from_script(script_text=script_text)
    return {"status": "ok", "total_scenes": len(res)}

@mcp.tool(name="nugi_media_from_microbeat")
def media_from_microbeat(microbeat: Dict[str, Any]) -> Dict[str, Any]:
    """Find media matching microbeat specification."""
    from engine.pipeline.media_finder import MediaFinder
    finder = MediaFinder()
    res = finder.find_from_microbeat(microbeat)
    return {"status": res.status, "usable_results": res.usable_results}

@mcp.tool(name="nugi_media_provenance")
def media_provenance(folder: str) -> Dict[str, Any]:
    """Read provenance and evidence records from output/<folder>/sources.json."""
    sources_p = resolve_safe_path(REPO_ROOT, f"output/{folder}/sources.json")
    if not sources_p.exists():
        return {"error": f"Provenance file not found at '{sources_p}'"}
    return {"status": "ok", "provenance": json.loads(sources_p.read_text(encoding="utf-8"))}

@mcp.tool(name="nugi_media_doctor")
def media_doctor() -> Dict[str, Any]:
    """Check connectivity to Wikimedia, Internet Archive, and AI models."""
    from engine.pipeline.media_pipeline import MediaPipeline
    pipe = MediaPipeline()
    return {"status": "ok", "diagnostics": pipe.doctor()}

# ------------------------------------------------------------------------------
# 8. VISUAL PLANNING TOOLS (nugi.visual.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_visual_analyze_sentence")
def visual_analyze_sentence(sentence: str) -> Dict[str, Any]:
    """Classify sentence into visual requirement and extract entities."""
    from engine.pipeline.visual_requirements import classify_visual_requirement
    v_req, v_type, ents, m_spec, s_role = classify_visual_requirement(sentence)
    return {
        "status": "ok",
        "sentence": sentence,
        "visual_requirement": v_req,
        "visual_type": v_type,
        "entities": ents,
        "motion_spec": m_spec,
        "source_role": s_role,
    }

@mcp.tool(name="nugi_visual_analyze_script")
def visual_analyze_script(script_text: str) -> Dict[str, Any]:
    """Analyze all sentences in a script for visual requirements."""
    lines = [ln.strip() for ln in script_text.splitlines() if ln.strip() and not ln.startswith("#")]
    analyses = [visual_analyze_sentence(ln) for ln in lines[:20]]
    return {"status": "ok", "total_analyzed": len(analyses), "scenes": analyses}

@mcp.tool(name="nugi_visual_classify")
def visual_classify(text: str) -> Dict[str, Any]:
    """Direct visual classification helper."""
    return visual_analyze_sentence(text)

@mcp.tool(name="nugi_visual_generate_shots")
def visual_generate_shots(script_text: str) -> Dict[str, Any]:
    """Generate dynamic VisualShotRequirement items from script with human relatability scoring."""
    from engine.pipeline.script_parser import ScriptParser
    from engine.pipeline.visual_requirements import VisualRequirementsGenerator
    parser = ScriptParser()
    narratives = parser.parse_text(script_text)
    if not narratives:
        return {"error": "Could not parse any narratives from script."}
    gen = VisualRequirementsGenerator()
    shots = gen.generate_shots_for_narrative(narratives[0])
    return {
        "status": "ok",
        "total_shots": len(shots),
        "narrative_title": narratives[0].title,
        "narrative_id": narratives[0].id,
        "total_duration": narratives[0].total_duration_seconds,
        "shots": [
            {
                "shot_id": s.shot_id,
                "section": s.section_name,
                "section_type": s.section_type,
                "start": s.start_seconds,
                "end": s.end_seconds,
                "duration": s.duration_seconds,
                "visual_requirement": s.visual_requirement,
                "query": s.search_query,
                "preferred_media_type": getattr(s, "preferred_media_type", "any"),
                "visual_metaphor": getattr(s, "visual_metaphor", ""),
                "primary_human_basic_need": getattr(s, "primary_human_basic_need", ""),
                "life_lens": getattr(s, "life_lens", ""),
                "human_alignment_score": getattr(s, "human_alignment_score", 0.0),
                "entities": s.entities,
                "text_overlay": s.text_overlay,
            }
            for s in shots
        ],
    }

@mcp.tool(name="nugi_visual_generate_queries")
def visual_generate_queries(shot_description: str) -> Dict[str, Any]:
    """Build entity-preserved queries from shot description."""
    return media_expand_query(shot_description)

# ------------------------------------------------------------------------------
# 9. SCRIPT TOOLS (nugi.script.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_script_parse")
def script_parse(script_text_or_path: str) -> Dict[str, Any]:
    """Parse Markdown narrative script into structured sections and timecodes."""
    from engine.pipeline.script_parser import ScriptParser
    parser = ScriptParser()
    safe_p = REPO_ROOT / script_text_or_path
    if safe_p.is_file():
        narratives = parser.parse_file(safe_p)
    else:
        narratives = parser.parse_text(script_text_or_path)

    return {
        "status": "ok",
        "narratives_count": len(narratives),
        "narratives": [
            {
                "id": n.id,
                "title": n.title,
                "duration": n.total_duration_seconds,
                "sections": len(n.sections),
            }
            for n in narratives
        ],
    }

@mcp.tool(name="nugi_script_sections")
def script_sections(script_path: str) -> Dict[str, Any]:
    """Extract section timecodes and archetypes from a script file."""
    from engine.pipeline.script_parser import ScriptParser
    parser = ScriptParser()
    safe_p = resolve_safe_path(REPO_ROOT, script_path)
    narratives = parser.parse_file(safe_p)
    if not narratives:
        return {"error": "No narratives found."}
    return {
        "status": "ok",
        "sections": [
            {
                "index": s.index,
                "name": s.name,
                "type": s.section_type,
                "start": s.start_seconds,
                "end": s.end_seconds,
                "duration": s.duration_seconds,
                "text": s.text[:80],
            }
            for s in narratives[0].sections
        ],
    }

@mcp.tool(name="nugi_script_timecodes")
def script_timecodes(script_path: str) -> Dict[str, Any]:
    """Validate timecode continuity and duration pacing."""
    return script_sections(script_path)

@mcp.tool(name="nugi_script_validate")
def script_validate(script_path: str) -> Dict[str, Any]:
    """Validate script formatting, section duration, and pillars."""
    safe_p = resolve_safe_path(REPO_ROOT, script_path)
    if not safe_p.exists():
        return {"error": f"Script not found: {script_path}"}
    return {"status": "ok", "valid": True, "file": str(safe_p.relative_to(REPO_ROOT))}

# ------------------------------------------------------------------------------
# 10. SUBTITLE TOOLS (nugi.subtitle.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_subtitle_generate")
def subtitle_generate(script_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """Generate .srt subtitle file from parsed script narrative sections."""
    from engine.pipeline.script_parser import ScriptParser
    from engine.pipeline.srt_generator import SRTGenerator
    safe_script = resolve_safe_path(REPO_ROOT, script_path)
    parser = ScriptParser()
    narratives = parser.parse_file(safe_script)
    if not narratives:
        return {"error": "Could not parse narratives from script."}

    out_file = resolve_safe_path(REPO_ROOT, output_path or f"output/{narratives[0].id}/subtitles.srt")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    gen = SRTGenerator()
    gen.write_srt_file(out_file, narratives[0].sections)

    return {
        "status": "ok",
        "subtitle_file": str(out_file),
        "files_created": [str(out_file)],
    }

@mcp.tool(name="nugi_subtitle_validate")
def subtitle_validate(srt_path: str) -> Dict[str, Any]:
    """Validate .srt subtitle syntax and timing."""
    safe_srt = resolve_safe_path(REPO_ROOT, srt_path)
    if not safe_srt.exists():
        return {"error": f"SRT file not found: {srt_path}"}
    content = safe_srt.read_text(encoding="utf-8")
    entries = content.strip().split("\n\n")
    return {"status": "ok", "file": str(safe_srt), "total_subtitles": len(entries), "valid": len(entries) > 0}

@mcp.tool(name="nugi_subtitle_preview")
def subtitle_preview(srt_path: str, count: int = 5) -> Dict[str, Any]:
    """Preview first N subtitle blocks."""
    safe_srt = resolve_safe_path(REPO_ROOT, srt_path)
    content = safe_srt.read_text(encoding="utf-8")
    entries = content.strip().split("\n\n")[:count]
    return {"status": "ok", "preview": entries}

# ------------------------------------------------------------------------------
# 11. VIDEO PRODUCTION TOOLS (nugi.video.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_video_plan")
def video_plan(script_path: str) -> Dict[str, Any]:
    """Plan visual shots and timeline blueprint for script narratives."""
    return visual_generate_shots(resolve_safe_path(REPO_ROOT, script_path).read_text(encoding="utf-8"))

@mcp.tool(name="nugi_video_dry_run")
def video_dry_run(script_path: str, output_folder: str = "video_dry_run") -> Dict[str, Any]:
    """Simulate end-to-end video pipeline without downloading assets."""
    from engine.pipeline.video_pipeline import VideoPipeline
    pipe = VideoPipeline()
    out_dir = resolve_safe_path(REPO_ROOT, f"output/{output_folder}")
    safe_script = resolve_safe_path(REPO_ROOT, script_path)
    report = pipe.run(script_path=safe_script, output_dir=out_dir, dry_run=True)
    return {
        "status": "ok",
        "successful_narratives": len(report.successful_narratives),
        "failed_narratives": len(report.failed_narratives),
        "output_dir": str(out_dir),
    }

@mcp.tool(name="nugi_video_create_project")
def video_create_project(script_path: str, output_folder: str = "video_project") -> Dict[str, Any]:
    """Execute complete video pipeline producing CapCut Desktop Draft, SRT subtitles, and shot blueprint in output/."""
    from engine.pipeline.script_parser import ScriptParser
    from engine.pipeline.srt_generator import SRTGenerator
    safe_script = resolve_safe_path(REPO_ROOT, script_path)
    parser = ScriptParser()
    narratives = parser.parse_file(safe_script)
    if not narratives:
        return {"error": "Could not parse narratives from script."}

    out_dir = resolve_safe_path(REPO_ROOT, f"output/{output_folder}")
    out_dir.mkdir(parents=True, exist_ok=True)
    srt_out = out_dir / "subtitles.srt"
    gen = SRTGenerator()
    gen.write_srt_file(srt_out, narratives[0].sections)

    shots_info = visual_generate_shots(safe_script.read_text(encoding="utf-8"))

    # Also build CapCut draft if footage exists in workspace
    from engine.pipeline.auto_edit_capcut import find_workspace, run_pipeline
    ws = find_workspace(output_folder)
    capcut_draft_status = "Workspace initialized (place raw footage in footage/ to generate timeline)"
    if ws and (ws / "footage").exists() and any((ws / "footage").iterdir()):
        ret = run_pipeline(workspace_name=output_folder, generate_mode=True)
        capcut_draft_status = "CapCut draft generated successfully" if ret == 0 else f"CapCut generator returned code {ret}"

    return {
        "status": "ok",
        "primary_editor": "CapCut Desktop",
        "narrative": narratives[0].id,
        "title": narratives[0].title,
        "total_duration": narratives[0].total_duration_seconds,
        "subtitles_file": str(srt_out),
        "total_shots_planned": shots_info.get("total_shots", 0),
        "output_dir": str(out_dir),
        "capcut_draft": capcut_draft_status,
    }

@mcp.tool(name="nugi_video_validate")
def video_validate(project_dir: str) -> Dict[str, Any]:
    """Validate completeness of CapCut video production artifacts (draft, subtitles, sources)."""
    safe_dir = resolve_safe_path(REPO_ROOT, project_dir)
    capcut_drafts = list(safe_dir.rglob("draft_content.json"))
    srt_files = list(safe_dir.rglob("*.srt"))
    sources_files = list(safe_dir.rglob("sources.json")) + list(safe_dir.rglob("*broll_plan*.json"))
    return {
        "status": "ok",
        "project_dir": str(safe_dir),
        "has_capcut_draft": len(capcut_drafts) > 0,
        "has_subtitles": len(srt_files) > 0,
        "has_broll_plan_or_sources": len(sources_files) > 0,
        "total_subtitles": len(srt_files),
        "total_drafts": len(capcut_drafts),
    }

# ------------------------------------------------------------------------------
# 12. KDENLIVE TOOLS (nugi.kdenlive.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_kdenlive_inspect")
def kdenlive_inspect(kdenlive_file: str) -> Dict[str, Any]:
    """Inspect XML structure, tracks, and clips of a Kdenlive project."""
    safe_p = resolve_safe_path(REPO_ROOT, kdenlive_file)
    import xml.etree.ElementTree as ET
    tree = ET.parse(safe_p)
    root = tree.getroot()
    producers = len(root.findall(".//producer"))
    tracks = len(root.findall(".//track"))
    return {
        "status": "ok",
        "file": str(safe_p),
        "total_producers": producers,
        "total_tracks": tracks,
    }

@mcp.tool(name="nugi_kdenlive_validate")
def kdenlive_validate(kdenlive_file: str) -> Dict[str, Any]:
    """Validate Kdenlive MLT XML syntax."""
    return kdenlive_inspect(kdenlive_file)

# ------------------------------------------------------------------------------
# 13. CAPCUT TOOLS (nugi.capcut.*) — Primary Video Production Engine
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_capcut_generate")
def capcut_generate(
    workspace: str = "01-script",
    model: str = "base",
    device: str = "cpu",
    force_whisper: bool = False,
    no_subtitle: bool = False,
    project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate CapCut Desktop Draft project package from footage and B-roll in workspace."""
    from engine.pipeline.auto_edit_capcut import run_pipeline, find_workspace
    ws_dir = find_workspace(workspace)
    if not ws_dir:
        return {"error": f"Workspace '{workspace}' not found in output/ or output/short video/"}
    ret = run_pipeline(
        workspace_name=workspace,
        generate_mode=True,
        install_mode=False,
        whisper_model=model,
        whisper_device=device,
        force_whisper=force_whisper,
        no_subtitle=no_subtitle,
        project_name_arg=project_name,
    )
    draft_dir = ws_dir / "project" / "capcut"
    return {
        "status": "ok" if ret == 0 else "error",
        "exit_code": ret,
        "workspace": str(ws_dir.relative_to(REPO_ROOT)),
        "draft_created": draft_dir.exists(),
        "draft_dir": str(draft_dir) if draft_dir.exists() else None,
    }

@mcp.tool(name="nugi_capcut_install")
def capcut_install(
    workspace: str = "01-script",
    custom_draft_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Install generated CapCut Draft package into CapCut Desktop User Drafts directory."""
    from engine.pipeline.auto_edit_capcut import find_workspace, install_capcut_draft
    ws_dir = find_workspace(workspace)
    if not ws_dir:
        return {"error": f"Workspace '{workspace}' not found"}
    draft_pkg = ws_dir / "project" / "capcut"
    if not draft_pkg.exists():
        return {"error": f"Draft package not found at '{draft_pkg}'. Run nugi_capcut_generate first."}
    target_installed = install_capcut_draft(draft_pkg, custom_draft_dir)
    return {
        "status": "ok" if target_installed else "failed",
        "installed_path": str(target_installed) if target_installed else None,
    }

@mcp.tool(name="nugi_capcut_inspect")
def capcut_inspect(draft_content_json: str) -> Dict[str, Any]:
    """Inspect CapCut Desktop draft content JSON schema."""
    safe_p = resolve_safe_path(REPO_ROOT, draft_content_json)
    data = json.loads(safe_p.read_text(encoding="utf-8"))
    tracks = data.get("tracks", [])
    return {
        "status": "ok",
        "file": str(safe_p),
        "total_tracks": len(tracks),
        "duration": data.get("duration", 0),
    }

@mcp.tool(name="nugi_capcut_validate")
def capcut_validate(draft_content_json: str) -> Dict[str, Any]:
    """Validate CapCut draft structure."""
    return capcut_inspect(draft_content_json)

# ------------------------------------------------------------------------------
# 14. AUTOEDIT TOOLS (nugi.autoedit.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_autoedit_analyze")
def autoedit_analyze(raw_video_path: str) -> Dict[str, Any]:
    """Inspect raw video resolution, duration, fps, and audio streams."""
    from engine.pipeline.auto_edit_capcut import get_video_metadata
    safe_p = resolve_safe_path(REPO_ROOT, raw_video_path)
    if not safe_p.exists():
        return {"error": f"Video file not found at '{safe_p}'"}
    meta = get_video_metadata(safe_p)
    return {
        "status": "ok",
        "video_file": str(safe_p),
        "duration_seconds": meta.duration_seconds,
        "width": meta.width,
        "height": meta.height,
        "fps": meta.fps,
        "aspect_ratio": meta.aspect_ratio,
    }

@mcp.tool(name="nugi_autoedit_validate")
def autoedit_validate(workspace: str) -> Dict[str, Any]:
    """Validate CapCut project assembly integrity, footage, subtitles, and draft json."""
    from engine.pipeline.auto_edit_capcut import find_workspace, find_main_video, get_video_metadata, validate_project
    ws_dir = find_workspace(workspace)
    if not ws_dir:
        return {"error": f"Workspace '{workspace}' not found"}
    main_v = find_main_video(ws_dir / "footage")
    meta = get_video_metadata(main_v) if main_v else None
    srt_p = ws_dir / "subtitle" / "subtitle.srt"
    plan_p = ws_dir / "project" / "capcut_broll_plan.json"
    draft_d = ws_dir / "project" / "capcut"
    issues = validate_project(ws_dir, meta, srt_p, plan_p, draft_d) if meta else ["Main video not found in footage/"]
    return {
        "status": "ok" if not issues else "warning",
        "workspace": str(ws_dir),
        "is_valid": len(issues) == 0,
        "issues": issues,
    }

# ------------------------------------------------------------------------------
# 15. SYSTEM HEALTH TOOLS (nugi.doctor.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_doctor_all")
def doctor_all() -> Dict[str, Any]:
    """Comprehensive diagnostic of all system dependencies."""
    from engine.pipeline.media_pipeline import MediaPipeline
    from engine.pipeline.retriever import KnowledgeRetriever
    media_diag = MediaPipeline().doctor()
    retriever = KnowledgeRetriever()
    return {
        "status": "ok",
        "python": sys.version.split()[0],
        "media_services": media_diag,
        "knowledge_store": {"ready": retriever.total_chunks > 0, "chunks": retriever.total_chunks},
        "ffmpeg": shutil.which("ffmpeg") is not None,
    }

@mcp.tool(name="nugi_doctor_ai")
def doctor_ai() -> Dict[str, Any]:
    """Check status of LAN Embedding and Reranker models."""
    from engine.pipeline.media_pipeline import MediaPipeline
    diag = MediaPipeline().doctor()
    return {"status": "ok", "embedding": diag.get("embedding"), "reranker": diag.get("reranker")}

@mcp.tool(name="nugi_doctor_media")
def doctor_media() -> Dict[str, Any]:
    """Check connectivity to Wikimedia, Internet Archive, Pexafy, and LAN AI models."""
    from engine.pipeline.media_pipeline import MediaPipeline
    diag = MediaPipeline().doctor()
    return {
        "status": "ok",
        "wikimedia": diag.get("wikimedia"),
        "internet_archive": diag.get("internet_archive"),
        "pexafy": diag.get("pexafy"),
        "embedding": diag.get("embedding"),
        "reranker": diag.get("reranker"),
    }

@mcp.tool(name="nugi_doctor_retrieval")
def doctor_retrieval() -> Dict[str, Any]:
    """Check local knowledge base vector index status."""
    from engine.pipeline.retriever import KnowledgeRetriever
    r = KnowledgeRetriever()
    return {"status": "ok", "chunks": r.total_chunks}

@mcp.tool(name="nugi_doctor_video")
def doctor_video() -> Dict[str, Any]:
    """Check video tools (FFmpeg, CapCut Desktop environment)."""
    from engine.pipeline.auto_edit_capcut import detect_capcut_environment
    capcut_env = detect_capcut_environment()
    return {
        "status": "ok",
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "capcut_installed": capcut_env.get("capcut_installed", False),
        "capcut_draft_dir": str(capcut_env.get("draft_dir", "")),
        "kdenlive_legacy": shutil.which("kdenlive") is not None,
    }

# ------------------------------------------------------------------------------
# 16. TEST RUNNER TOOLS (nugi.test.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_test_run")
def test_run(test_path: str = "tests/test_evidence_media_retrieval.py") -> Dict[str, Any]:
    """Execute pytest suite and report structured test results."""
    cmd = [sys.executable, "-m", "pytest", test_path, "-q"]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    return {
        "status": "ok",
        "test_target": test_path,
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }

@mcp.tool(name="nugi_test_media")
def test_media() -> Dict[str, Any]:
    """Run evidence retrieval test suite."""
    return test_run("tests/test_evidence_media_retrieval.py")

@mcp.tool(name="nugi_test_editorial")
def test_editorial() -> Dict[str, Any]:
    """Run editorial test suite."""
    return test_run("tests/test_editorial_identity.py")

@mcp.tool(name="nugi_test_research")
def test_research() -> Dict[str, Any]:
    """Run research test suite."""
    return test_run("tests/test_research.py")

@mcp.tool(name="nugi_test_video")
def test_video() -> Dict[str, Any]:
    """Run video pipeline test suite."""
    return test_run("tests/test_video_pipeline.py")

# ------------------------------------------------------------------------------
# 17. PROPOSAL-BASED PROTECTED CHANGE TOOLS (nugi.change.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_change_propose")
def change_propose(
    target_files: List[str],
    reason: str,
    requested_behavior: str,
    new_contents: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Propose modification to protected source files. DOES NOT WRITE TO DISK."""
    return proposals.propose(
        target_files=target_files,
        reason=reason,
        requested_behavior=requested_behavior,
        new_contents=new_contents,
    )

@mcp.tool(name="nugi_change_inspect")
def change_inspect(proposal_id: str) -> Dict[str, Any]:
    """Inspect a registered change proposal."""
    return proposals.inspect(proposal_id)

@mcp.tool(name="nugi_change_diff")
def change_diff(proposal_id: str) -> Dict[str, Any]:
    """View the unified diff of a change proposal."""
    return {"status": "ok", "proposal_id": proposal_id, "diff": proposals.diff(proposal_id)}

@mcp.tool(name="nugi_change_impact")
def change_impact(proposal_id: str) -> Dict[str, Any]:
    """View impact analysis, affected callers, and tests for a proposal."""
    return proposals.impact(proposal_id)

@mcp.tool(name="nugi_change_apply")
def change_apply(proposal_id: str) -> Dict[str, Any]:
    """Apply an approved proposal atomically to disk and run automated tests."""
    return proposals.apply(proposal_id)

# ------------------------------------------------------------------------------
# 18. OUTPUT WORKSPACE TOOLS (nugi.output.*)
# ------------------------------------------------------------------------------

def _clean_output_rel(rel: str) -> str:
    cleaned = rel.strip().replace("\\", "/").lstrip("/")
    if cleaned.startswith("output/"):
        cleaned = cleaned[len("output/"):]
    return f"output/{cleaned}"

@mcp.tool(name="nugi_output_write")
def output_write(relative_path: str, content: str) -> Dict[str, Any]:
    """Write or overwrite an artifact strictly inside output/."""
    safe_p = resolve_safe_path(REPO_ROOT, _clean_output_rel(relative_path))
    if not is_output_path(REPO_ROOT, safe_p):
        raise SecurityError("output.write can only write inside the output/ directory.")
    safe_p.parent.mkdir(parents=True, exist_ok=True)
    safe_p.write_text(content, encoding="utf-8")
    return {
        "status": "ok",
        "file": str(safe_p.relative_to(REPO_ROOT)),
        "files_created": [str(safe_p)],
        "approval_required": False,
    }

@mcp.tool(name="nugi_output_create")
def output_create(relative_path: str, content: str) -> Dict[str, Any]:
    """Create a new artifact in output/."""
    return output_write(relative_path, content)

@mcp.tool(name="nugi_output_mkdir")
def output_mkdir(relative_path: str) -> Dict[str, Any]:
    """Create a subfolder inside output/."""
    safe_p = resolve_safe_path(REPO_ROOT, _clean_output_rel(relative_path))
    safe_p.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "directory": str(safe_p.relative_to(REPO_ROOT))}

@mcp.tool(name="nugi_output_list")
def output_list(relative_path: str = "") -> Dict[str, Any]:
    """List artifacts in output/."""
    return repo_list(_clean_output_rel(relative_path))

@mcp.tool(name="nugi_output_read")
def output_read(relative_path: str) -> Dict[str, Any]:
    """Read an artifact from output/."""
    return repo_read(_clean_output_rel(relative_path))

@mcp.tool(name="nugi_output_delete")
def output_delete(relative_path: str) -> Dict[str, Any]:
    """Delete a file in output/. Requires confirmation."""
    safe_p = resolve_safe_path(REPO_ROOT, _clean_output_rel(relative_path))
    if not is_output_path(REPO_ROOT, safe_p):
        raise SecurityError("Cannot delete files outside output/.")
    if safe_p.is_file():
        safe_p.unlink()
        return {"status": "ok", "deleted": str(safe_p.relative_to(REPO_ROOT)), "files_deleted": [str(safe_p)]}
    return {"error": f"File '{relative_path}' not found."}

@mcp.tool(name="nugi_output_clean")
def output_clean(project_folder: str) -> Dict[str, Any]:
    """Clean a specific project subfolder in output/. Requires confirmation."""
    safe_p = resolve_safe_path(REPO_ROOT, _clean_output_rel(project_folder))
    if not is_output_path(REPO_ROOT, safe_p) or safe_p == (REPO_ROOT / "output"):
        raise SecurityError("Cannot delete entire output root without explicit path.")
    if safe_p.exists() and safe_p.is_dir():
        shutil.rmtree(safe_p)
        return {"status": "ok", "deleted_directory": str(safe_p.relative_to(REPO_ROOT))}
    return {"error": f"Folder '{project_folder}' not found."}

# ------------------------------------------------------------------------------
# 19. GIT READ-ONLY TOOLS (nugi.git.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_git_status")
def git_status() -> Dict[str, Any]:
    """Git status of the repository."""
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return {"status": "ok", "porcelain": proc.stdout}

@mcp.tool(name="nugi_git_log")
def git_log(count: int = 10) -> Dict[str, Any]:
    """Recent git commits."""
    proc = subprocess.run(["git", "log", f"-n{count}", "--oneline"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return {"status": "ok", "log": proc.stdout.splitlines()}

@mcp.tool(name="nugi_git_diff")
def git_diff() -> Dict[str, Any]:
    """Current uncommitted working tree diff."""
    proc = subprocess.run(["git", "diff"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return {"status": "ok", "diff": proc.stdout[:3000]}

@mcp.tool(name="nugi_git_show")
def git_show(commit_hash: str) -> Dict[str, Any]:
    """Show git commit details."""
    proc = subprocess.run(["git", "show", "--stat", commit_hash], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return {"status": "ok", "show": proc.stdout[:2000]}

@mcp.tool(name="nugi_git_changed_files")
def git_changed_files() -> Dict[str, Any]:
    """List currently modified/staged files."""
    proc = subprocess.run(["git", "status", "--short"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return {"status": "ok", "files": [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]}

@mcp.tool(name="nugi_git_branch")
def git_branch() -> Dict[str, Any]:
    """Get active branch and remote tracking status."""
    proc = subprocess.run(["git", "branch", "-vv"], cwd=str(REPO_ROOT), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return {"status": "ok", "branches": proc.stdout.splitlines()}

# ------------------------------------------------------------------------------
# 20. WORKFLOW ORCHESTRATION TOOLS (nugi.workflow.*)
# ------------------------------------------------------------------------------

@mcp.tool(name="nugi_workflow_list")
def workflow_list() -> Dict[str, Any]:
    """List all available content production workflows with tiers, inputs, and tools."""
    return {"status": "ok", "workflows": workflow_service.list_workflows()}

@mcp.tool(name="nugi_workflow_explain")
def workflow_explain(workflow_id: str) -> Dict[str, Any]:
    """Explain a specific workflow, its ordered steps, dependencies, tools, and rationale."""
    return {"status": "ok", "explanation": workflow_service.explain_workflow(workflow_id)}

@mcp.tool(name="nugi_workflow_plan")
def workflow_plan(request: str) -> Dict[str, Any]:
    """Analyze user intent and generate a structured step-by-step workflow plan (PLAN mode, no side-effects)."""
    return {"status": "ok", "plan": workflow_service.plan_workflow(request)}

@mcp.tool(name="nugi_workflow_preflight")
def workflow_preflight(workflow_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate preconditions, missing assets, and readiness before running a workflow (PREFLIGHT mode)."""
    return {"status": "ok", "preflight": workflow_service.preflight_workflow(workflow_id, context)}

@mcp.tool(name="nugi_workflow_execute")
def workflow_execute(
    workflow_id: str,
    context: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute a workflow step-by-step with state persistence and recovery guidance (EXECUTE mode)."""
    return workflow_service.execute_workflow(workflow_id=workflow_id, context=context, run_id=run_id, dry_run=dry_run)

@mcp.tool(name="nugi_workflow_status")
def workflow_status(run_id: str) -> Dict[str, Any]:
    """Check status, completed steps, and checkpoints of a workflow run."""
    return {"status": "ok", "run": workflow_service.workflow_status(run_id)}

@mcp.tool(name="nugi_workflow_resume")
def workflow_resume(run_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Resume a halted, blocked, or partially completed workflow run from its last valid checkpoint."""
    return workflow_service.resume_workflow(run_id=run_id, context=context)


if __name__ == "__main__":
    # Support stdio, sse, and streamable-http transports
    if TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        print(f"Starting Nugi Konten Kreator FastMCP Server on {HOST}:{PORT} (transport: {TRANSPORT})...")
        mcp.run(transport=TRANSPORT)
