import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf

from engine.config import DEFAULT_PDF_DIR


BOOK_DEFINITIONS = [
    {
        "pattern": "*Influence*",
        "book": "Influence: The Psychology of Persuasion",
        "author": "Robert B. Cialdini",
        "concepts": {
            "reciproc": "Reciprocity",
            "commit": "Commitment & Consistency",
            "proof": "Social Proof",
            "liking": "Liking",
            "authorit": "Authority",
            "scarc": "Scarcity",
            "contrast": "Perceptual Contrast",
            "primitive": "Instant Influence"
        }
    },
    {
        "pattern": "*Contagious*",
        "book": "Contagious: Why Things Catch On",
        "author": "Jonah Berger",
        "concepts": {
            "social currency": "Social Currency",
            "trigger": "Triggers",
            "emotion": "Emotion & Arousal",
            "public": "Public Visibility",
            "practical value": "Practical Value",
            "stor": "Stories (Trojan Horse)",
            "arousal": "Physiological Arousal"
        }
    },
    {
        "pattern": "*Made to stick*",
        "book": "Made to Stick: Why Some Ideas Survive and Others Die",
        "author": "Chip Heath & Dan Heath",
        "concepts": {
            "simple": "Simple (Core + Compact)",
            "unexpected": "Unexpected (Curiosity Gaps)",
            "concrete": "Concrete (Sensory Hooks)",
            "credible": "Credible (Testable Credentials)",
            "emotional": "Emotional (Mother Teresa Effect)",
            "curse of knowledge": "Curse of Knowledge",
            "story": "Story (Mental Flight Simulator)"
        }
    }
]


def find_book_files(pdf_dir: Path = DEFAULT_PDF_DIR) -> List[Dict[str, Any]]:
    """Scan directory for the 3 target PDF books."""
    found_books = []
    if not pdf_dir.exists():
        return found_books
        
    for item in pdf_dir.iterdir():
        if not item.name.lower().endswith(".pdf"):
            continue
        for defn in BOOK_DEFINITIONS:
            # Simple wildcard pattern matching
            keyword = defn["pattern"].replace("*", "").lower()
            if keyword in item.name.lower():
                found_books.append({
                    "path": item,
                    "book": defn["book"],
                    "author": defn["author"],
                    "concepts_map": defn["concepts"]
                })
                break
    return found_books


def clean_page_text(text: str) -> str:
    """Clean OCR or PDF extraction quirks."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    # Remove hyphenated line breaks
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_chunks_from_pdf(
    pdf_info: Dict[str, Any],
    max_pages: Optional[int] = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Extract structured chunks with rich metadata from a PDF file.
    """
    path = pdf_info["path"]
    book = pdf_info["book"]
    author = pdf_info["author"]
    concepts_map = pdf_info["concepts_map"]
    
    chunks = []
    try:
        reader = pypdf.PdfReader(str(path))
        num_pages = len(reader.pages) if max_pages is None else min(len(reader.pages), max_pages)
        current_chapter = "General Concepts"
        
        for page_idx in range(num_pages):
            page_num = page_idx + 1
            raw_text = reader.pages[page_idx].extract_text() or ""
            text = clean_page_text(raw_text)
            if len(text) < 80:
                continue
                
            # Detect chapter changes in text
            first_lines = text[:250].split("\n")
            for line in first_lines:
                line_str = line.strip()
                if re.match(r"^(CHAPTER|Chapter|[0-9]+\.)\s+", line_str, re.I) or len(line_str) < 40 and line_str.isupper():
                    if len(line_str) > 4:
                        current_chapter = line_str
                        break

            # Identify dominant concept in this page
            page_concept = "General"
            for keyword, concept_name in concepts_map.items():
                if keyword in text.lower():
                    page_concept = concept_name
                    break

            # Split into sliding window chunks
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                # Adjust end to nearest space
                if end < len(text):
                    space_idx = text.rfind(" ", start, end)
                    if space_idx > start + (chunk_size // 2):
                        end = space_idx
                
                chunk_text = text[start:end].strip()
                if len(chunk_text) > 100:
                    chunks.append({
                        "source": path.name,
                        "book": book,
                        "author": author,
                        "chapter": current_chapter,
                        "section": f"Page {page_num}",
                        "page": page_num,
                        "concept": page_concept,
                        "text": chunk_text
                    })
                
                if end >= len(text):
                    break
                start = end - chunk_overlap
                
    except Exception as e:
        print(f"Error parsing {path.name}: {e}")
        
    return chunks
