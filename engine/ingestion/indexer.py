import datetime
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from engine.config import KNOWLEDGE_STORE_PATH, BASE_DIR, EMBEDDING_MODEL
from engine.providers.embedding import LocalEmbeddingProvider, EmbeddingProvider
from engine.ingestion.pdf_parser import find_book_files, extract_chunks_from_pdf

logger = logging.getLogger(__name__)


def infer_chunk_taxonomy(category: str, title: str, text: str) -> Dict[str, str]:
    """Infers primary domain, anchor, and lens from chunk content."""
    cat_lower = (category + " " + title + " " + text[:200]).lower()
    
    # 1. Primary domain
    if any(k in cat_lower for k in ["properti", "property", "rumah", "hunian", "tanah", "kpr", "bangunan"]):
        domain = "property"
    elif any(k in cat_lower for k in ["kota", "city", "urban", "transport", "jalan", "macet"]):
        domain = "city"
    elif any(k in cat_lower for k in ["ai", "kecerdasan", "otomasi", "algoritma", "komputasi"]):
        domain = "ai"
    elif any(k in cat_lower for k in ["ekonomi", "uang", "gaji", "investasi", "modal", "pasar"]):
        domain = "economy"
    elif any(k in cat_lower for k in ["kerja", "kantor", "karir", "profesi", "remote"]):
        domain = "work"
    else:
        domain = "human"
        
    # 2. Anchor
    if any(k in cat_lower for k in ["tanah", "land"]):
        anchor = "land"
    elif any(k in cat_lower for k in ["kota", "city", "wilayah", "kawasan"]):
        anchor = "city"
    elif any(k in cat_lower for k in ["kerja", "kantor", "meja"]):
        anchor = "work"
    elif any(k in cat_lower for k in ["milik", "kepemilikan", "sertifikat", "aset"]):
        anchor = "ownership"
    elif any(k in cat_lower for k in ["komuter", "mobilitas", "transport"]):
        anchor = "mobility"
    elif any(k in cat_lower for k in ["ruang", "space", "kamar"]):
        anchor = "space"
    else:
        anchor = "housing"
        
    # 3. Lens
    if any(k in cat_lower for k in ["psikolog", "emosi", "takut", "curiosity", "influence", "persuasi"]):
        lens = "psychology"
    elif any(k in cat_lower for k in ["harga", "biaya", "uang", "ekonomi", "pasar", "suku bunga"]):
        lens = "economics"
    elif any(k in cat_lower for k in ["sosial", "masyarakat", "komunitas", "kelas"]):
        lens = "sociology"
    elif any(k in cat_lower for k in ["sejarah", "kolonial", "zaman", "masa lalu"]):
        lens = "history"
    elif any(k in cat_lower for k in ["arsitektur", "tata ruang", "zonasi"]):
        lens = "urbanism"
    elif any(k in cat_lower for k in ["teknologi", "alat", "komputasi"]):
        lens = "technology"
    else:
        lens = "philosophy"
        
    return {"domain": domain, "anchor": anchor, "lens": lens}


def ingest_markdown_knowledge_files(knowledge_dir: Path = BASE_DIR / "knowledge") -> List[Dict[str, Any]]:
    """Ingest curated markdown knowledge files into structured chunks with v2 taxonomy."""
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
                tax = infer_chunk_taxonomy(category, title, intro)
                chunks.append({
                    "source": str(md_file.relative_to(BASE_DIR)),
                    "book": f"Curated Knowledge: {category.title()}",
                    "author": "Nugi Content Brain",
                    "chapter": title,
                    "section": "Overview",
                    "page": 1,
                    "concept": title,
                    "text": intro,
                    "domain": tax["domain"],
                    "anchor": tax["anchor"],
                    "lens": tax["lens"]
                })
                
            for sec in sections[1:]:
                lines = sec.split("\n", 1)
                sec_title = lines[0].strip()
                sec_body = lines[1].strip() if len(lines) > 1 else ""
                if len(sec_body) > 40:
                    text_block = f"### {title}: {sec_title}\n{sec_body}"
                    tax = infer_chunk_taxonomy(category, sec_title, text_block)
                    chunks.append({
                        "source": str(md_file.relative_to(BASE_DIR)),
                        "book": f"Curated Knowledge: {category.title()}",
                        "author": "Nugi Content Brain",
                        "chapter": title,
                        "section": sec_title,
                        "page": 1,
                        "concept": f"{title} - {sec_title}",
                        "text": text_block,
                        "domain": tax["domain"],
                        "anchor": tax["anchor"],
                        "lens": tax["lens"]
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
    Saves v2 metadata: version, embedding_provider, embedding_model, embedding_dimension, created_at.
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
    print("Scanning local PDF books...", flush=True)
    book_files = find_book_files()
    for b in book_files:
        print(f"Parsing: {b['book']} ({b['path'].name})...", flush=True)
        pdf_chunks = extract_chunks_from_pdf(b, max_pages=pdf_sample_pages_per_book)
        for pc in pdf_chunks:
            tax = infer_chunk_taxonomy(b['book'], pc.get('concept', ''), pc.get('text', ''))
            pc['domain'] = tax['domain']
            pc['anchor'] = tax['anchor']
            pc['lens'] = tax['lens']
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
        batch_embs = provider.get_embeddings(batch)
        embeddings.extend(batch_embs)
            
    # 4. Attach embeddings, dimensions, and assign sequential IDs
    embedding_dimension = len(embeddings[0]) if embeddings else 0
    provider_name = provider.__class__.__name__
    model_name = getattr(provider, "model_name", EMBEDDING_MODEL)

    final_records = []
    for idx, (chunk, emb) in enumerate(zip(all_chunks, embeddings)):
        record = dict(chunk)
        record["id"] = idx
        record["embedding"] = emb
        record["embedding_model"] = model_name
        record["embedding_dimension"] = len(emb)
        final_records.append(record)
        
    # 5. Save to JSON store with v2 metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "2.0",
        "embedding_provider": provider_name,
        "embedding_model": model_name,
        "embedding_dimension": embedding_dimension,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_chunks": len(final_records),
        "chunks": final_records
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        
    print(f"Successfully saved knowledge store to {output_path} ({len(final_records)} chunks, dim={embedding_dimension}).")
    return len(final_records)


if __name__ == "__main__":
    build_knowledge_index()
