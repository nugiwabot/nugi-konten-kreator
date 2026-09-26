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
# MEDIA RETRIEVAL AGENT COMMANDS
# ==============================================================================

def cmd_media_search(args):
    """Preview media search results without downloading."""
    from engine.pipeline.media_pipeline import MediaPipeline
    request = args.request
    count = args.count
    media_type = args.type or None

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
    media_type = args.type or None
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
            print(f"  [{df.final_rank}] {df.filename}")
            print(f"        Provider: {df.provider} | Type: N/A")
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
    print()



def cmd_create_video(args):
    """Batch faceless video production from structured script."""
    from engine.pipeline.video_pipeline import VideoPipeline

    print("\n" + "=" * 65)
    print("🎬 NUGI CONTENT CREATOR — AUTOMATED VIDEO PRODUCTION PIPELINE")
    print("=" * 65)
    print(f"Script:     {args.script}")
    print(f"Output dir: {args.output}")
    print(f"Target:     {args.narasi}")
    print(f"Mode:       {'DRY RUN (placeholders)' if args.dry_run else 'FULL PRODUCTION (downloading assets)'}")
    print("=" * 65 + "\n")

    pipeline = VideoPipeline()
    report = pipeline.run(
        script_path=args.script,
        output_dir=args.output,
        target_narasi=args.narasi,
        dry_run=args.dry_run,
    )
    report.print_summary()


def main():
    parser = argparse.ArgumentParser(description="Nugi Content Intelligence & Influence Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-video command
    p_cv = subparsers.add_parser(
        "create-video",
        help="Batch faceless video production: script -> retrieval -> rough cut -> subtitles -> Kdenlive project",
    )
    p_cv.add_argument(
        "--script",
        type=str,
        required=True,
        help="Path to markdown script file (e.g. 5_Narasi_Konten_TikTok_Shorts_Nugi.md)",
    )
    p_cv.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory (default: output)",
    )
    p_cv.add_argument(
        "--narasi",
        type=str,
        default="all",
        help="Process specific narasi ID/index (e.g. '1', 'narasi-01', or 'all')",
    )
    p_cv.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate timeline, subtitles, and Kdenlive projects without downloading media files",
    )
    p_cv.set_defaults(func=cmd_create_video)

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
    p_ms.add_argument("--type", choices=["image", "video", "any"],
                      default=None, help="Force media type (auto-detected if omitted)")
    p_ms.set_defaults(func=cmd_media_search)

    # media download
    p_md = media_sub.add_parser("download", help="Search, rank, and download media files")
    p_md.add_argument("request", type=str,
                      help="Natural-language visual request")
    p_md.add_argument("--count", type=int, default=5,
                      help="Number of files to download (default: 5)")
    p_md.add_argument("--folder", type=str, default="general",
                      help="Destination folder under assets/media/ (default: general)")
    p_md.add_argument("--type", choices=["image", "video", "any"],
                      default=None, help="Force media type (auto-detected if omitted)")
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

    def _media_help(args):
        p_media.print_help()

    p_media.set_defaults(func=_media_help)
    # ── end media command group ───────────────────────────────────────

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
        
    args.func(args)


if __name__ == "__main__":
    main()
