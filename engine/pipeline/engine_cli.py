import argparse
import json
import sys
from typing import Optional

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


def main():
    parser = argparse.ArgumentParser(description="Nugi Content Intelligence & Influence Engine CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

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

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
        
    args.func(args)


if __name__ == "__main__":
    main()
