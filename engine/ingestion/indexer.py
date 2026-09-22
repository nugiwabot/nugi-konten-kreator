import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from engine.config import KNOWLEDGE_STORE_PATH, BASE_DIR
from engine.providers.embedding import LocalEmbeddingProvider, EmbeddingProvider
from engine.ingestion.pdf_parser import find_book_files, extract_chunks_from_pdf

logger = logging.getLogger(__name__)


def ingest_markdown_knowledge_files(knowledge_dir: Path = BASE_DIR / "knowledge") -> List[Dict[str, Any]]:
    """Ingest curated markdown knowledge files into structured chunks."""
    chunks = []
    if not knowledge_dir.exists():
        return chunks
        
    for md_file in knowledge_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            category = md_file.parent.name
            title = md_file.stem.replace("-", " ").title()
            
            # Divide markdown by H2 sections
            sections = content.split("## ")
            intro = sections[0].strip()
            if intro:
                chunks.append({
                    "source": str(md_file.relative_to(BASE_DIR)),
                    "book": f"Curated Knowledge: {category.title()}",
                    "author": "Nugi Content Brain",
                    "chapter": title,
                    "section": "Overview",
                    "page": 1,
                    "concept": title,
                    "text": intro
                })
                
            for sec in sections[1:]:
                lines = sec.split("\n", 1)
                sec_title = lines[0].strip()
                sec_body = lines[1].strip() if len(lines) > 1 else ""
                if len(sec_body) > 40:
                    chunks.append({
                        "source": str(md_file.relative_to(BASE_DIR)),
                        "book": f"Curated Knowledge: {category.title()}",
                        "author": "Nugi Content Brain",
                        "chapter": title,
                        "section": sec_title,
                        "page": 1,
                        "concept": f"{title} - {sec_title}",
                        "text": f"### {title}: {sec_title}\n{sec_body}"
                    })
        except Exception as e:
            logger.warning(f"Failed to read markdown file {md_file}: {e}")
            
    return chunks


def build_knowledge_index(
    pdf_sample_pages_per_book: Optional[int] = 30,
    batch_size: int = 32,
    output_path: Path = KNOWLEDGE_STORE_PATH,
    provider: Optional[EmbeddingProvider] = None
) -> int:
    """
    Builds the vector store JSON combining curated markdown files and local PDF books.
    """
    if provider is None:
        provider = LocalEmbeddingProvider()
        
    all_chunks: List[Dict[str, Any]] = []
    
    # 1. Ingest curated markdown files first
    print("Ingesting curated markdown knowledge files...", flush=True)
    md_chunks = ingest_markdown_knowledge_files()
    print(f"Loaded {len(md_chunks)} curated knowledge sections.", flush=True)
    all_chunks.extend(md_chunks)
    
    # 2. Ingest local PDF books
    print("Scanning local PDF books in Downloads...", flush=True)
    book_files = find_book_files()
    for b in book_files:
        print(f"Parsing: {b['book']} ({b['path'].name})...", flush=True)
        pdf_chunks = extract_chunks_from_pdf(b, max_pages=pdf_sample_pages_per_book)
        print(f"Extracted {len(pdf_chunks)} chunks from {b['book']}.", flush=True)
        all_chunks.extend(pdf_chunks)
        
    print(f"Total chunks to embed and index: {len(all_chunks)}", flush=True)
    
    # 3. Generate embeddings in batches
    texts_to_embed = [c["text"][:1000] for c in all_chunks]
    embeddings: List[List[float]] = []
    
    total_batches = (len(texts_to_embed) + batch_size - 1) // batch_size
    for i in range(0, len(texts_to_embed), batch_size):
        batch = texts_to_embed[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)...", flush=True)
        try:
            batch_embs = provider.get_embeddings(batch)
            embeddings.extend(batch_embs)
        except Exception as e:
            print(f"Batch embedding failed: {e}. Using fallback...", flush=True)
            from engine.providers.embedding import FallbackEmbeddingProvider
            fallback = FallbackEmbeddingProvider()
            batch_embs = fallback.get_embeddings(batch)
            embeddings.extend(batch_embs)
            
    # 4. Attach embeddings and assign sequential IDs
    final_records = []
    for idx, (chunk, emb) in enumerate(zip(all_chunks, embeddings)):
        record = dict(chunk)
        record["id"] = idx
        record["embedding"] = emb
        final_records.append(record)
        
    # 5. Save to JSON store
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0",
        "total_chunks": len(final_records),
        "chunks": final_records
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        
    print(f"Successfully saved knowledge store to {output_path} ({len(final_records)} chunks).")
    return len(final_records)


if __name__ == "__main__":
    build_knowledge_index()
