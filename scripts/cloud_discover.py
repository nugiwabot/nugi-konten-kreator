#!/usr/bin/env python3
"""Run Nugi's discovery-only editorial workflow in a clean cloud runner.

Feed items remain discovery leads. This entry point deliberately disables
research enrichment; evidence gathering is a separate workflow operation.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5, help="Number of ideas to return (1-20).")
    parser.add_argument(
        "--queries",
        default="",
        help="Optional semicolon-separated discovery queries; defaults to the editorial engine's configured queries.",
    )
    parser.add_argument("--output-dir", default="cloud-output/discover", help="Directory for JSON and Markdown results.")
    return parser.parse_args(argv)


def render_markdown(result: dict[str, Any], generated_at: str) -> str:
    lines = [
        "# Nugi Cloud Discovery",
        "",
        f"- Generated at: {generated_at}",
        f"- Candidates returned: {result.get('count_returned', 0)}",
        f"- Discovery signals considered: {result.get('signals_considered', 0)}",
        f"- Existing titles indexed: {result.get('topic_memory', {}).get('indexed_titles', 0)}",
        "",
        "> RSS/news signals and evergreen seeds are discovery leads, not verified evidence. Research is not run by this operation.",
        "",
    ]
    candidates = result.get("candidates", [])
    if not candidates:
        lines.extend(["## Results", "", "No candidates were returned. Check the workflow log and feed availability.", ""])
    for index, candidate in enumerate(candidates, start=1):
        title = str(candidate.get("suggested_title") or candidate.get("source_headline") or "Untitled idea")
        lines.extend([
            f"## {index}. {title}",
            "",
            f"- Origin: {candidate.get('origin_kind', 'unknown')}",
            f"- Domain: {candidate.get('primary_domain', 'unknown')}",
            f"- Editorial fit: {candidate.get('editorial_fit_score', 0)}/100",
            f"- Niche alignment: {candidate.get('niche_decision', 'NEEDS_SCOPING')} ({candidate.get('niche_fit_score', 0)}/100)",
            f"- Opportunity score: {candidate.get('opportunity_score', 0)}",
            f"- Research status: {candidate.get('research_status', 'NOT_RESEARCHED')}",
            f"- Central question: {candidate.get('central_question', '')}",
            f"- Source headline: {candidate.get('source_headline', '')}",
            f"- Source URL: {candidate.get('source_url', '')}",
            f"- Scoping note: {candidate.get('scoping_reason', '')}",
            "",
        ])
        reasons = candidate.get("selection_reason") or []
        if reasons:
            lines.extend(["Selection notes:"] + [f"- {reason}" for reason in reasons] + [""])
    lines.extend([
        "## Next step",
        "",
        "Select an idea, then run the separate research operation before relying on factual claims or drafting a script.",
        "",
    ])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    count = max(1, min(20, args.count))
    queries = [item.strip() for item in args.queries.split(";") if item.strip()] or None
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from engine.editorial.idea_discovery import IdeaDiscoveryEngine

        engine = IdeaDiscoveryEngine(repo_root=REPO_ROOT)
        result = engine.discover(
            count=count,
            queries=queries,
            include_evergreen_fallback=True,
            enrich_with_research=False,
        )
        generated_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema_version": 1,
            "operation": "discover",
            "generated_at": generated_at,
            "repository_commit": __import__("os").environ.get("GITHUB_SHA", "local"),
            "research_executed": False,
            "media_downloaded": False,
            "result": result,
        }
        (output_dir / "discovery.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output_dir / "discovery.md").write_text(
            render_markdown(result, generated_at), encoding="utf-8"
        )
        print(f"Discovery completed: {result.get('count_returned', 0)} candidates")
        print(f"JSON: {output_dir / 'discovery.json'}")
        print(f"Markdown: {output_dir / 'discovery.md'}")
        return 0
    except Exception as exc:
        print(f"Cloud discovery failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
