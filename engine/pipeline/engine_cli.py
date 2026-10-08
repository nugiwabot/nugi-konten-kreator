import argparse
import json
import sys
from typing import Optional

# Ensure Windows consoles don't crash on emojis or unicode characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from engine.pipeline.retriever import KnowledgeRetriever
from engine.pipeline.research_runner import ResearchRunner
from engine.ingestion.indexer import build_knowledge_index


def cmd_retrieve(args):
    query = args.query
    top_n = args.top_n
    print(f"\n[Retrieval] Query: '{query}' (Top {top_n} reranked chunks)\n")
    retriever = KnowledgeRetriever()
    results = retriever.retrieve(query=query, top_k_candidates=15, top_k_reranked=top_n)
    
    if not results:
        print("No matching knowledge found.")
        return
        
    for i, res in enumerate(results, 1):
        print(f"--- #{i} [{res.get('book')}] ({res.get('concept')}) ---")
        print(f"Author: {res.get('author')} | Chapter: {res.get('chapter')}")
        print(f"Cosine Similarity: {res.get('similarity_score', 0):.4f} | Rerank Score: {res.get('rerank_score', 0):.4f}")
        print(f"Excerpt: {res.get('text', '')[:280]}...\n")


def cmd_research(args):
    topic = args.topic
    print(f"\n[Research] Fetching current web intelligence on: '{topic}'...\n")
    runner = ResearchRunner()
    data = runner.run_research(topic=topic, max_results=args.max_results)
    
    print(f"Total Sources Found: {data['total_sources_found']}")
    for s in data["sources"]:
        print(f"- [{s['source_tier_name']}] {s['title']}")
        print(f"  URL: {s['url']}")
        print(f"  Snippet: {s['content'][:140]}...\n")


def cmd_reindex(args):
    print("\n[Indexing] Building local vector store from curated knowledge & PDFs...\n")
    count = build_knowledge_index(pdf_sample_pages_per_book=args.pages, batch_size=32)
    print(f"\nIndexing complete! {count} total chunks ready.\n")


# ==============================================================================
# QUESTION MINING COMMAND
# ==============================================================================

def cmd_question_mine(args):
    """Mine editorial story opportunities from a search results dataset."""
    from pathlib import Path
    from engine.editorial.question_mining import mine_questions

    dataset_path = Path(args.dataset)
    output_path = Path(args.output) if args.output else None
    top_k = args.top_k
    min_results = args.min_results
    force_rebuild = getattr(args, "force_rebuild", False)
    as_json = getattr(args, "json", False)

    if not as_json:
        print("\n" + "=" * 65)
        print("  NUGI QUESTION MINING ENGINE — Human x Place x Change x WHY")
        print("=" * 65)
        print(f"  Dataset:      {dataset_path}")
        print(f"  Output:       {output_path or '(console only)'}")
        print(f"  Top-k:        {top_k}")
        print(f"  Min cluster:  {min_results}")
        print("=" * 65 + "\n")

    # Validate dataset exists
    if not dataset_path.exists():
        if as_json:
            print(json.dumps({
                "error": f"Dataset not found: {dataset_path}",
                "hint": "Use --dataset <PATH> to specify a valid dataset file."
            }, ensure_ascii=False))
        else:
            print(f"[ERROR] Dataset not found: {dataset_path}")
            print(f"        Use --dataset <PATH> to specify the dataset location.")
            print(f"        Example: python -m engine.pipeline.engine_cli question-mine \\")
            print(f"                   --dataset \"output/riset keyword.json\"")
        sys.exit(1)

    threshold = getattr(args, "threshold", None)
    adaptive = not getattr(args, "no_adaptive", False)
    max_queries = getattr(args, "max_queries", None)

    try:
        result = mine_questions(
            dataset_path=dataset_path,
            output_path=output_path,
            top_k=top_k,
            min_cluster_size=min_results,
            force_rebuild=force_rebuild,
            threshold=threshold,
            adaptive=adaptive,
            max_queries=max_queries
        )
    except FileNotFoundError as e:
        if as_json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        if as_json:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}")
        sys.exit(1)

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Human-readable output
    meta = result.get("metadata", {})
    thresh_val = meta.get("adaptive_threshold", meta.get("clustering_threshold", "N/A"))
    thresh_src = meta.get("threshold_source", "adaptive")
    method = meta.get("clustering_method", "agglomerative_cosine")

    print(f"  Total records in dataset:  {meta.get('total_records', 0)}")
    print(f"  Unique queries found:      {meta.get('total_queries', 0)}")
    print(f"  Queries with HP anchor:    {meta.get('human_place_queries', 0)}")
    print(f"  Clustering method:         {method}")
    print(f"  Clustering threshold:      {thresh_val} ({thresh_src})")
    print(f"  Clusters formed:           {meta.get('cluster_count', 0)}")
    print(f"  Story opportunities:       {meta.get('opportunity_count', 0)}")
    print(f"  Embedding available:       {'Yes' if meta.get('embedding_available') else 'No (fallback used)'}")

    if output_path:
        print(f"\n  Results saved to: {output_path}")

    clusters = result.get("clusters", [])
    if clusters:
        print(f"\n{'─' * 65}")
        print("  CLUSTERS DISCOVERED")
        print(f"{'─' * 65}")
        for cluster in clusters[:10]:
            print(f"\n  [{cluster['cluster_id']}] {cluster['cluster_name']}")
            print(f"  Queries: {cluster['member_count']} | Coherence: {cluster['cluster_coherence_score']:.3f}")
            print(f"  Representative: {cluster['representative_query']}")
            if cluster['member_queries'][1:3]:
                for q in cluster['member_queries'][1:3]:
                    print(f"    + {q}")

    opportunities = result.get("story_opportunities", [])
    if opportunities:
        print(f"\n{'─' * 65}")
        print("  STORY OPPORTUNITIES")
        print(f"{'─' * 65}")
        for i, opp in enumerate(opportunities[:top_k], 1):
            print(f"\n  #{i} [{opp.get('type', '').upper()}] {opp.get('cluster_name', '')}")
            print(f"  Angle: {opp.get('suggested_title_direction', '')}")
            print(f"  Story Type: {opp.get('suggested_story_type', '')}")
            if opp.get("human_place_bridge"):
                bridge_str = " → ".join(opp["human_place_bridge"][:3])
                print(f"  HP Bridge: {bridge_str}")
            print(f"  Note: {opp.get('note', '')}")

    print(f"\n{'=' * 65}")
    print("  Done. Use results as research signals, not final titles.")
    print(f"{'=' * 65}\n")


# ==============================================================================
# MEDIA RETRIEVAL AGENT COMMANDS
# ==============================================================================

def cmd_media_search(args):
    """Preview media search results without downloading."""
    from engine.pipeline.media_pipeline import MediaPipeline
    request = args.request
    count = args.count
    media_type = getattr(args, "media", None) or getattr(args, "type", None) or None

    print(f"\n[Media Search] '{request}'")
    print(f"  Count: {count} | Type: {media_type or 'auto-detect'}\n")

    pipeline = MediaPipeline()
    result = pipeline.search(request=request, count=count, media_type=media_type)

    print(f"Expanded queries used ({len(result.expanded_queries)}):")
    for q in result.expanded_queries:
        print(f"  • {q}")

    print(f"\nTotal raw candidates found: {result.total_candidates_found}")
    print(f"Embedding used: {result.embedding_used} | Reranker used: {result.reranker_used}")

    if result.fallback_reason:
        print(f"\n⚠ Ranking note: {result.fallback_reason}")

    print(f"\nTop {min(count, len(result.candidates))} Ranked Results:\n")
    for line in result.preview_lines(top=count):
        print(line)

    if not result.candidates:
        print("No results found. Try different keywords or check provider connectivity.")


def cmd_media_download(args):
    """Search and download media files."""
    from engine.pipeline.media_pipeline import MediaPipeline
    request = args.request
    count = args.count
    folder = args.folder
    media_type = getattr(args, "media", None) or getattr(args, "type", None) or None
    max_size = args.max_size_mb

    print(f"\n[Media Download] '{request}'")
    print(f"  Count: {count} | Type: {media_type or 'auto-detect'} | Folder: {folder}")
    print(f"  Max file size: {max_size} MB\n")

    from engine.pipeline.media_downloader import MediaDownloader
    from engine.config import MEDIA_ASSETS_DIR
    from pathlib import Path

    downloader = MediaDownloader(
        base_dir=MEDIA_ASSETS_DIR,
        max_size_mb=max_size,
    )
    pipeline = MediaPipeline(downloader=downloader)
    report = pipeline.search_and_download(
        request=request,
        count=count,
        folder=folder,
        media_type=media_type,
    )

    print(f"\n{'='*60}")
    print(f"DOWNLOAD REPORT")
    print(f"{'='*60}")
    print(f"Result: {report.summary_line()}")
    if report.folder:
        print(f"Folder: {report.folder}")
    if report.sources_json_path:
        print(f"Metadata: {report.sources_json_path}")

    if report.successful:
        print(f"\n✅ Downloaded files:")
        for df in report.successful:
            mtype = getattr(df, "media_type", "") or ("video" if df.filename.endswith((".mp4", ".ogv", ".webm", ".avi", ".mov", ".mpg", ".mpeg")) else "image")
            print(f"  [{df.final_rank}] {df.filename}")
            print(f"        Provider: {df.provider} | Type: {mtype}")
            print(f"        Title: {df.title[:60]}")
            print(f"        Size: {df.file_size_bytes / 1024:.1f} KB | "
                  f"Rerank: {df.reranker_score:.3f}")

    if report.failed:
        print(f"\n❌ Failed downloads:")
        for ff in report.failed:
            print(f"  • {ff.title[:60]} — {ff.reason}")


def cmd_media_from_script(args):
    """Extract visual scenes from a script file and download media for each."""
    from engine.pipeline.media_pipeline import MediaPipeline
    from pathlib import Path

    script_path = Path(args.file)
    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}")
        sys.exit(1)

    try:
        script_text = script_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading script file: {e}")
        sys.exit(1)

    folder = args.folder
    count_per_scene = args.count_per_scene

    print(f"\n[Script-to-Asset] File: {script_path.name}")
    print(f"  Folder: {folder} | Count per scene: {count_per_scene}\n")

    pipeline = MediaPipeline()
    reports = pipeline.search_from_script(
        script_text=script_text,
        folder=folder,
        count_per_scene=count_per_scene,
    )

    if not reports:
        print("No visual scenes detected in the script.")
        return

    print(f"\n{'='*60}")
    print(f"SCRIPT-TO-ASSET REPORT — {len(reports)} scene(s) processed")
    print(f"{'='*60}")
    for i, report in enumerate(reports, 1):
        print(f"\nScene {i:03d}: {report.summary_line()}")
        if report.folder:
            print(f"  Folder: {report.folder}")
        for df in report.successful:
            print(f"  ✅ {df.filename}")
        for ff in report.failed:
            print(f"  ❌ {ff.title[:50]} — {ff.reason}")


def cmd_media_find(args):
    """Find photos and videos using MediaFinder."""
    import json
    from pathlib import Path
    from engine.pipeline.media_finder import MediaFinder

    finder = MediaFinder()
    query = getattr(args, "query", "") or ""
    media = getattr(args, "media", None) or getattr(args, "type", None) or "any"
    era = getattr(args, "era", "auto")
    style = getattr(args, "style", "auto")
    count = getattr(args, "count", 8)
    folder = getattr(args, "folder", None)
    download = getattr(args, "download", False)
    visual_requirement = getattr(args, "visual_requirement", None) or getattr(args, "vr", "auto")

    if download:
        result = finder.find_and_download(
            request=query,
            media=media,
            era=era,
            style=style,
            count=count,
            folder=folder,
            visual_requirement=visual_requirement,
        )
    else:
        result = finder.find(
            request=query,
            media=media,
            era=era,
            style=style,
            count=count,
            visual_requirement=visual_requirement,
        )

    print(result.preview(max_items=count))

    if getattr(args, "output", None):
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Saved results to: {out_path}\n")


def cmd_media_doctor(args):
    """Health check for all media retrieval services."""
    from engine.pipeline.media_pipeline import MediaPipeline
    from engine.config import EMBEDDING_URL, RERANKER_URL, WIKIMEDIA_API_URL, INTERNET_ARCHIVE_API_URL

    pipeline = MediaPipeline()
    status = pipeline.doctor()

    print(f"\n{'='*50}")
    print("MEDIA RETRIEVAL — HEALTH CHECK")
    print(f"{'='*50}")

    services = [
        ("Wikimedia Commons", "wikimedia", f"  URL: {WIKIMEDIA_API_URL}"),
        ("Internet Archive", "internet_archive", f"  URL: {INTERNET_ARCHIVE_API_URL}"),
        ("Embedding API", "embedding", f"  URL: {EMBEDDING_URL}"),
        ("Reranker API", "reranker", f"  URL: {RERANKER_URL}"),
    ]

    for label, key, detail in services:
        s = status.get(key, "UNKNOWN")
        icon = "✅" if s == "OK" else "⚠️"
        print(f"\n  {icon} {label:<25} {s}")
        print(f"  {detail}")

    print(f"\n{'='*50}")
    all_critical_ok = status.get("wikimedia") == "OK" or status.get("internet_archive") == "OK"
    if all_critical_ok:
        print("  Media providers are reachable. Ready to search & download.")
    else:
        print("  ⚠ No media providers reachable. Check network connection.")

    emb_ok = status.get("embedding") == "OK"
    rer_ok = status.get("reranker") == "OK"
    if not emb_ok or not rer_ok:
        print("  ⚠ Semantic AI services offline — keyword fallback ranking will be used.")
def cmd_doctor(args):
    """System-wide health check for Nugi Content Engine v2."""
    from engine.config import (
        EMBEDDING_URL, RERANKER_URL, KNOWLEDGE_STORE_PATH
    )
    from engine.providers.embedding import LocalEmbeddingProvider
    from engine.providers.reranker import LocalRerankerProvider
    import json

    print("\nNUGI CONTENT ENGINE HEALTH\n")

    # 1. Embedding
    print("Embedding")
    try:
        embedder = LocalEmbeddingProvider(endpoint_url=EMBEDDING_URL, enable_fallback=False)
        if embedder.is_alive():
            print(f"[OK] {EMBEDDING_URL}\n")
        else:
            print(f"[FAIL] {EMBEDDING_URL} - Service ping failed\n")
    except Exception as e:
        print(f"[FAIL] {EMBEDDING_URL} - {e}\n")

    # 2. Reranker
    print("Reranker")
    try:
        reranker = LocalRerankerProvider(endpoint_url=RERANKER_URL, enable_fallback=False)
        if reranker.is_alive():
            print(f"[OK] {RERANKER_URL}\n")
        else:
            print(f"[FAIL] {RERANKER_URL} - Service ping failed\n")
    except Exception as e:
        print(f"[FAIL] {RERANKER_URL} - {e}\n")

    # 3. Knowledge Store
    print("Knowledge Store")
    try:
        if KNOWLEDGE_STORE_PATH.exists():
            with open(KNOWLEDGE_STORE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                chunks_count = len(data.get("chunks", []))
            print(f"[OK] {chunks_count} chunks\n")
        else:
            print(f"[WARN] File not found at {KNOWLEDGE_STORE_PATH}\n")
    except Exception as e:
        print(f"[FAIL] {e}\n")

    # 4. Web Search
    print("Web Search")
    try:
        from engine.pipeline.research_runner import ResearchRunner
        runner = ResearchRunner()
        print("[OK]\n")
    except Exception as e:
        print(f"[FAIL] {e}\n")

    # 5. Media
    print("Media")
    try:
        from engine.pipeline.media_pipeline import MediaPipeline
        mp = MediaPipeline()
        media_status = mp.doctor()
        if media_status.get("wikimedia") == "OK" or media_status.get("internet_archive") == "OK":
            print("[OK]\n")
        else:
            print("[WARN] Media providers unreachable\n")
    except Exception as e:
        print(f"[FAIL] {e}\n")

    # 6. Configuration
    print("Configuration")
    try:
        from engine.config import BASE_DIR, EMBEDDING_TIMEOUT, RERANKER_TIMEOUT
        if BASE_DIR.exists() and EMBEDDING_TIMEOUT > 0 and RERANKER_TIMEOUT > 0:
            print("[OK]\n")
        else:
            print("[FAIL] Invalid configuration values\n")
    except Exception as e:
        print(f"[FAIL] {e}\n")

    # 7. Editorial Rules
    print("Editorial Rules")
    try:
        from engine.editorial.quality_gate import FORBIDDEN_ANTI_PATTERNS
        from engine.editorial.taxonomy import PRIMARY_DOMAINS
        from engine.editorial.property_bridge import CANONICAL_BRIDGES
        if FORBIDDEN_ANTI_PATTERNS and PRIMARY_DOMAINS and CANONICAL_BRIDGES:
            print("[OK]\n")
        else:
            print("[FAIL] Missing editorial rule definitions\n")
    except Exception as e:
        print(f"[FAIL] {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Nugi Content Intelligence & Influence Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # doctor command
    p_doctor = subparsers.add_parser("doctor", help="Comprehensive health check: Embedding, Reranker, Store, Media, Config, Rules")
    p_doctor.set_defaults(func=cmd_doctor)

    # question-mine command (with 'mine' alias)
    p_qm = subparsers.add_parser(
        "question-mine",
        aliases=["mine"],
        help="Mine editorial story opportunities from a search results dataset (JSON/JSONL)"
    )
    p_qm.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to search results dataset file (JSON or JSONL)"
    )
    p_qm.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save results JSON (optional, defaults to console output)"
    )
    p_qm.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Maximum number of story opportunities to return (default: 10)"
    )
    p_qm.add_argument(
        "--min-results",
        type=int,
        default=1,
        help="Minimum queries per cluster (default: 1)"
    )
    p_qm.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force cluster rebuild even if cache is current"
    )
    p_qm.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Cosine distance clustering threshold override (default: derived adaptively)"
    )
    p_qm.add_argument(
        "--no-adaptive",
        action="store_true",
        help="Disable adaptive threshold calculation and use safe default (0.30)"
    )
    p_qm.add_argument(
        "--max-queries",
        type=int,
        default=None,
        help="Maximum queries to process (useful for fast smoke testing)"
    )
    p_qm.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of human-readable format"
    )
    p_qm.set_defaults(func=cmd_question_mine)

    # retrieve command
    p_retrieve = subparsers.add_parser("retrieve", help="Query permanent knowledge using 2-stage retrieval")
    p_retrieve.add_argument("query", type=str, help="Question or topic to retrieve knowledge for")
    p_retrieve.add_argument("--top-n", type=int, default=3, help="Number of reranked results to return")
    p_retrieve.set_defaults(func=cmd_retrieve)

    # research command
    p_research = subparsers.add_parser("research", help="Perform runtime web research with source evaluation")
    p_research.add_argument("topic", type=str, help="Topic or news to research")
    p_research.add_argument("--max-results", type=int, default=5, help="Number of search results")
    p_research.set_defaults(func=cmd_research)

    # reindex command
    p_reindex = subparsers.add_parser("reindex", help="Re-index local markdown knowledge and PDFs")
    p_reindex.add_argument("--pages", type=int, default=30, help="Pages per PDF book to index")
    p_reindex.set_defaults(func=cmd_reindex)

    # ── media command group ───────────────────────────────────────────
    p_media = subparsers.add_parser(
        "media",
        help="Media Retrieval Agent — search & download visual assets from Wikimedia + Internet Archive"
    )
    media_sub = p_media.add_subparsers(dest="media_command", help="Media subcommands")

    # media search
    p_ms = media_sub.add_parser("search", help="Search media without downloading (preview results)")
    p_ms.add_argument("request", type=str,
                      help="Natural-language visual request, e.g. 'D-Day 1944 Normandy'")
    p_ms.add_argument("--count", type=int, default=10,
                      help="Number of results to return (default: 10)")
    p_ms.add_argument("--type", choices=["image", "photo", "video", "any"],
                      default=None, help="Force media type: image | video | any (auto-detected if omitted)")
    p_ms.add_argument("--media", choices=["photo", "image", "video", "any"],
                      default=None, help="Media type alias (default: auto)")
    p_ms.set_defaults(func=cmd_media_search)

    # media download
    p_md = media_sub.add_parser("download", help="Search, rank, and download media files")
    p_md.add_argument("request", type=str,
                      help="Natural-language visual request")
    p_md.add_argument("--count", type=int, default=5,
                      help="Number of files to download (default: 5)")
    p_md.add_argument("--folder", type=str, default="general",
                      help="Destination folder under assets/media/ (default: general)")
    p_md.add_argument("--type", choices=["image", "photo", "video", "any"],
                      default=None, help="Force media type: image | video | any (auto-detected if omitted)")
    p_md.add_argument("--media", choices=["photo", "image", "video", "any"],
                      default=None, help="Media type alias (default: auto)")
    p_md.add_argument("--max-size-mb", type=int, default=500,
                      help="Maximum file size in MB (default: 500)")
    p_md.set_defaults(func=cmd_media_download)

    # media from-script
    p_mfs = media_sub.add_parser(
        "from-script",
        help="Extract visual scenes from a script file and download media for each scene"
    )
    p_mfs.add_argument("file", type=str, help="Path to script/narration file (.md or .txt)")
    p_mfs.add_argument("--folder", type=str, default="script-assets",
                       help="Base folder under assets/media/ (default: script-assets)")
    p_mfs.add_argument("--count-per-scene", type=int, default=3,
                       help="Files to download per scene (default: 3)")
    p_mfs.set_defaults(func=cmd_media_from_script)

    # media doctor
    p_mdoc = media_sub.add_parser("doctor", help="Health check: Wikimedia, Internet Archive, Embedding, Reranker")
    p_mdoc.set_defaults(func=cmd_media_doctor)

    # media find (inside media group)
    p_mfind = media_sub.add_parser("find", help="Find photos and videos with MediaFinder")
    p_mfind.add_argument("pos_query", nargs="?", default="", help="Natural-language visual request")
    p_mfind.add_argument("--query", "-q", dest="opt_query", type=str, default=None, help="Query option")
    p_mfind.add_argument("--media", "-m", choices=["photo", "image", "video", "any"], default="any", help="Media type: photo | video | any (default: any)")
    p_mfind.add_argument("--type", "-t", choices=["photo", "image", "video", "any"], default=None, help="Media type alias")
    p_mfind.add_argument("--era", "-e", choices=["historical", "past", "present", "future", "timeless", "auto"], default="auto", help="Era hint (default: auto)")
    p_mfind.add_argument("--style", "-s", choices=["formal", "neutral", "documentary", "archival", "cinematic", "conceptual", "auto"], default="auto", help="Visual style hint (default: auto)")
    p_mfind.add_argument("--count", "-n", type=int, default=8, help="Number of results (default: 8)")
    p_mfind.add_argument("--visual-requirement", "--vr", choices=["REAL_REQUIRED", "REAL_PREFERRED", "GENERIC_ALLOWED", "NO_BROLL", "REMOTION_REQUIRED", "auto"], default="auto", help="Visual evidence requirement (default: auto)")
    p_mfind.add_argument("--download", "-d", action="store_true", help="Download top results")
    p_mfind.add_argument("--folder", type=str, default=None, help="Destination subfolder")
    p_mfind.add_argument("--output", "-o", type=str, default=None, help="Path to save result JSON file")

    def _mfind_wrapper(a):
        a.query = a.opt_query or a.pos_query
        return cmd_media_find(a)

    p_mfind.set_defaults(func=_mfind_wrapper)

    def _media_help(args):
        p_media.print_help()

    p_media.set_defaults(func=_media_help)
    # ── end media command group ───────────────────────────────────────

    # media-find top-level command (with 'find-media' alias)
    p_mf = subparsers.add_parser(
        "media-find",
        aliases=["find-media"],
        help="Find photos and videos using MediaFinder (photo/video, era, style, and optional download)"
    )
    p_mf.add_argument("--query", "-q", type=str, required=True,
                      help="Natural-language visual request")
    p_mf.add_argument("--media", "-m", choices=["photo", "image", "video", "any"], default="any",
                      help="Media type: photo | video | any (default: any)")
    p_mf.add_argument("--type", "-t", choices=["photo", "image", "video", "any"], default=None,
                      help="Media type alias")
    p_mf.add_argument("--era", "-e",
                      choices=["historical", "past", "present", "future", "timeless", "auto"],
                      default="auto", help="Era hint (default: auto)")
    p_mf.add_argument("--style", "-s",
                      choices=["formal", "neutral", "documentary", "archival", "cinematic", "conceptual", "auto"],
                      default="auto", help="Visual style hint (default: auto)")
    p_mf.add_argument("--visual-requirement", "--vr",
                      choices=["REAL_REQUIRED", "REAL_PREFERRED", "GENERIC_ALLOWED", "NO_BROLL", "REMOTION_REQUIRED", "auto"],
                      default="auto", help="Visual evidence requirement (default: auto)")
    p_mf.add_argument("--count", "-n", type=int, default=8,
                      help="Number of results to return (default: 8)")
    p_mf.add_argument("--download", "-d", action="store_true",
                      help="Download candidates to local filesystem")
    p_mf.add_argument("--folder", type=str, default=None,
                      help="Destination subfolder for downloads under assets/media/")
    p_mf.add_argument("--output", "-o", type=str, default=None,
                      help="Path to save result JSON file")
    p_mf.set_defaults(func=cmd_media_find)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
        
    args.func(args)


if __name__ == "__main__":
    main()
