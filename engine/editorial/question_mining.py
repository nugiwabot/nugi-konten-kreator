"""
Question Mining Engine v1
Transforms search queries from an external dataset into structured editorial opportunities.

Pipeline:
1. Load dataset (optional, read-only, configurable path)
2. Detect fingerprint/hash for cache invalidation
3. Parse & normalize queries
4. Intent classification
5. Human–Place anchor evaluation
6. Semantic clustering (local embedding + cosine + agglomerative + reranker validation)
7. Generate story opportunities per cluster
8. Cache results to output file

Engine runs WITHOUT the dataset — uses knowledge store + web search when dataset is absent.
Changing dataset triggers cluster rebuild.
"""
import hashlib
import json
import logging
import math
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading and normalization
# ---------------------------------------------------------------------------

def _compute_file_fingerprint(path: Path) -> str:
    """SHA-256 fingerprint of a file for cache invalidation."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_dataset(dataset_path: Path) -> Tuple[List[Dict[str, Any]], str]:
    """
    Load a search results dataset (JSON or JSONL).
    
    Returns:
        (records, fingerprint) — records list and file fingerprint
        
    Raises:
        FileNotFoundError: if dataset_path does not exist
        ValueError: if dataset is empty or unreadable
    """
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {dataset_path}\n"
            f"Use --dataset <PATH> to specify the dataset location.\n"
            f"Engine will continue without dataset using knowledge store."
        )

    fingerprint = _compute_file_fingerprint(dataset_path)

    with open(dataset_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        raise ValueError(f"Dataset at {dataset_path} is empty.")

    # Try JSON array first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data, fingerprint
        if isinstance(data, dict):
            # Try common wrapper keys
            for key in ("results", "data", "items", "documents"):
                if key in data and isinstance(data[key], list):
                    return data[key], fingerprint
            return [data], fingerprint
    except json.JSONDecodeError:
        pass

    # Try JSONL
    records = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if records:
        return records, fingerprint

    raise ValueError(f"Could not parse dataset at {dataset_path} as JSON or JSONL.")


def extract_queries(records: List[Dict[str, Any]]) -> List[str]:
    """
    Extract unique search queries from dataset records.
    Looks for query fields in common locations.
    """
    query_fields = ["query", "keyword", "search_query", "q", "term", "title"]
    queries = set()

    for record in records:
        for field in query_fields:
            val = record.get(field, "")
            if val and isinstance(val, str) and len(val.strip()) > 3:
                queries.add(val.strip())
                break

    return sorted(list(queries))


def extract_documents(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract title + snippet documents from dataset records.
    Used for understanding the content landscape per query.
    """
    docs = []
    for record in records:
        title = str(record.get("title", record.get("name", ""))).strip()
        snippet = str(record.get("snippet", record.get("description", record.get("content", "")))).strip()
        query = str(record.get("query", record.get("keyword", ""))).strip()
        url = str(record.get("url", record.get("link", ""))).strip()

        if title or snippet:
            docs.append({
                "title": title,
                "snippet": snippet,
                "query": query,
                "url": url
            })
    return docs


# ---------------------------------------------------------------------------
# Semantic clustering (local embedding + agglomerative)
# ---------------------------------------------------------------------------

def _cosine_distance(v1: List[float], v2: List[float]) -> float:
    """Cosine distance = 1 - cosine_similarity."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 1.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))


def _get_embeddings_batch(
    texts: List[str],
    embedding_provider: Any,
    batch_size: int = 5
) -> List[List[float]]:
    """Embed texts in batches to balance speed and stability."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            embs = embedding_provider.get_embeddings(batch)
            all_embeddings.extend(embs)
        except Exception as e:
            logger.warning(f"Embedding batch {i // batch_size} failed: {e}. Using zero vectors.")
            all_embeddings.extend([[]] * len(batch))
    return all_embeddings


def calculate_adaptive_threshold(
    embeddings: List[List[float]],
    min_clamp: float = 0.12,
    max_clamp: float = 0.65,
    fallback: float = 0.30
) -> float:
    """
    Derives an adaptive cosine distance clustering threshold from embedding distributions.
    
    Strategy:
    - Analyzes pairwise cosine distances among valid vectors.
    - Small datasets (< 3 items) or missing vectors fallback to safe baseline.
    - Analyzes distance percentiles and variance: detects natural elbow/gap separating
      dense intra-cluster pairs from sparse inter-cluster pairs.
    - Clamps output within [min_clamp, max_clamp] to guarantee stable clustering.
    """
    valid = [e for e in embeddings if e and any(x != 0.0 for x in e)]
    if len(valid) < 3:
        return fallback

    distances = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            d = _cosine_distance(valid[i], valid[j])
            distances.append(d)

    if not distances:
        return fallback

    distances.sort()
    n = len(distances)

    # Statistical properties
    mean_d = sum(distances) / n
    variance = sum((d - mean_d) ** 2 for d in distances) / n
    std_d = math.sqrt(variance)

    # Look for elbow / gap in the lower-to-middle range (15th to 60th percentile)
    start_idx = max(0, int(0.15 * n))
    end_idx = min(n - 1, int(0.60 * n))

    best_jump = 0.0
    jump_threshold = None

    for k in range(start_idx, end_idx):
        jump = distances[k + 1] - distances[k]
        if jump > best_jump and jump > 0.03:
            best_jump = jump
            jump_threshold = distances[k] + (jump / 2.0)

    if jump_threshold is not None:
        derived = jump_threshold
    else:
        # Statistical fallback: weighted average between 30th percentile and mean - 0.5 * std
        p30 = distances[int(0.30 * n)]
        stat_target = max(0.12, mean_d - 0.5 * std_d)
        derived = (p30 + stat_target) / 2.0

    derived_clamped = max(min_clamp, min(max_clamp, derived))
    return round(derived_clamped, 4)


def agglomerative_cluster(
    items: List[str],
    embeddings: List[List[float]],
    threshold: Optional[float] = None,
    adaptive: bool = True
) -> List[List[int]]:
    """
    Agglomerative (average-linkage) clustering by cosine distance.
    
    Args:
        items: Text items being clustered
        embeddings: Pre-computed embedding vectors
        threshold: Distance threshold for cluster membership (overrides adaptive when provided)
        adaptive: If True and threshold is None, dynamically derives threshold from embeddings
        
    Returns:
        List of clusters, each cluster is a list of indices into items
    """
    n = len(items)
    if n == 0:
        return []
    if n == 1:
        return [[0]]

    # Determine effective threshold
    if threshold is not None:
        effective_threshold = float(threshold)
    elif adaptive:
        effective_threshold = calculate_adaptive_threshold(embeddings)
    else:
        effective_threshold = 0.30

    clusters: List[List[int]] = [[i] for i in range(n)]

    def cluster_representative(cluster_indices: List[int]) -> List[float]:
        """Average embedding of cluster members."""
        vecs = [embeddings[i] for i in cluster_indices if i < len(embeddings) and embeddings[i]]
        if not vecs:
            return []
        dim = len(vecs[0])
        avg = [sum(v[d] for v in vecs) / len(vecs) for d in range(dim)]
        return avg

    merged = True
    while merged:
        merged = False
        best_pair = None
        best_dist = effective_threshold

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                rep_i = cluster_representative(clusters[i])
                rep_j = cluster_representative(clusters[j])
                if rep_i and rep_j:
                    dist = _cosine_distance(rep_i, rep_j)
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (i, j)

        if best_pair:
            i, j = best_pair
            clusters[i] = clusters[i] + clusters[j]
            clusters.pop(j)
            merged = True

    return clusters


def _generate_cluster_name(items: List[str]) -> str:
    """Generate a cluster name from the most common significant words."""
    # Stop words in Indonesian + English
    stop_words = {
        "yang", "dan", "di", "ke", "dari", "dengan", "untuk", "ini", "itu",
        "pada", "dalam", "adalah", "akan", "tidak", "bisa", "cara", "apa",
        "kenapa", "mengapa", "bagaimana", "kapan", "siapa", "dimana", "the",
        "of", "in", "is", "to", "a", "an", "and", "or", "for", "with"
    }

    word_counts: Dict[str, int] = {}
    for item in items:
        words = re.findall(r"\b[a-z]{4,}\b", item.lower())
        for word in words:
            if word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1

    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    if top_words:
        return " × ".join(w.upper() for w, _ in top_words)
    return "CLUSTER"


def validate_clusters_with_reranker(
    clusters: List[List[int]],
    items: List[str],
    reranker_provider: Any
) -> List[Dict[str, Any]]:
    """
    Validates and orders cluster members using the reranker.
    For each cluster, the most representative query is found by reranking
    all members against the cluster name as query.
    """
    enriched_clusters = []

    for cluster_indices in clusters:
        cluster_items = [items[i] for i in cluster_indices]
        cluster_name = _generate_cluster_name(cluster_items)

        try:
            reranked = reranker_provider.rerank(
                query=cluster_name,
                documents=cluster_items,
                top_n=len(cluster_items)
            )
            ordered_items = [r["document"] for r in reranked]
            coherence_score = reranked[0]["relevance_score"] if reranked else 0.0
            representative = ordered_items[0] if ordered_items else cluster_items[0]
        except Exception as e:
            logger.warning(f"Reranker failed for cluster validation: {e}. Using original order.")
            ordered_items = cluster_items
            coherence_score = 0.5
            representative = cluster_items[0]

        enriched_clusters.append({
            "cluster_id": f"cluster_{len(enriched_clusters):02d}",
            "cluster_name": cluster_name,
            "representative_query": representative,
            "member_queries": ordered_items,
            "member_count": len(ordered_items),
            "cluster_coherence_score": round(float(coherence_score), 4)
        })

    # Sort clusters by size (largest first)
    enriched_clusters.sort(key=lambda x: x["member_count"], reverse=True)
    for i, cluster in enumerate(enriched_clusters):
        cluster["cluster_id"] = f"cluster_{i:02d}"

    return enriched_clusters


# ---------------------------------------------------------------------------
# Story opportunity generation
# ---------------------------------------------------------------------------

def generate_story_opportunities(
    cluster: Dict[str, Any],
    intent_results: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Generates story opportunities from a cluster of related queries.
    
    Returns up to 3 story opportunity seeds per cluster.
    """
    from engine.editorial.story_type import classify_story_type
    from engine.editorial.human_place_engine import find_human_place_bridge

    opportunities = []
    representative = cluster["representative_query"]
    members = cluster["member_queries"]

    # Find human–place bridge for cluster
    bridge = find_human_place_bridge(representative, " ".join(members[:5]))

    # Classify story types from member queries
    story_type_votes: Dict[str, int] = {}
    for query in members[:5]:  # Sample top 5
        st = classify_story_type(query)
        primary = st["primary_type"]
        story_type_votes[primary] = story_type_votes.get(primary, 0) + 1

    # Top story type
    top_story_type = max(story_type_votes, key=story_type_votes.get) if story_type_votes else "hidden_system"

    # Generate 1–3 opportunities from the cluster
    # Opportunity 1: Main query as editorial seed
    if representative:
        opportunities.append({
            "type": "editorial_seed",
            "cluster_id": cluster["cluster_id"],
            "source_query": representative,
            "cluster_name": cluster["cluster_name"],
            "suggested_title_direction": f"Pertanyaan Editorial: {representative}",
            "human_place_bridge": bridge.get("chain", []),
            "place_relation": bridge.get("place_relation"),
            "suggested_story_type": top_story_type,
            "supporting_queries": members[1:4],
            "note": "Use these as research signal, not as final title"
        })

    # Opportunity 2: WHY reformulation
    why_reformulation = _reformulate_as_why_question(representative)
    if why_reformulation and why_reformulation != representative:
        opportunities.append({
            "type": "why_reformulation",
            "cluster_id": cluster["cluster_id"],
            "source_query": representative,
            "cluster_name": cluster["cluster_name"],
            "suggested_title_direction": why_reformulation,
            "human_place_bridge": bridge.get("chain", []),
            "place_relation": bridge.get("place_relation"),
            "suggested_story_type": "hidden_system",
            "note": "WHY reformulation for deeper editorial angle"
        })

    # Opportunity 3: Future/implication angle (if cluster has future signals)
    future_members = [m for m in members if any(k in m.lower() for k in ["akan", "masa depan", "ke depan", "kalau"])]
    if future_members:
        opportunities.append({
            "type": "future_angle",
            "cluster_id": cluster["cluster_id"],
            "source_query": future_members[0],
            "cluster_name": cluster["cluster_name"],
            "suggested_title_direction": f"Jika {representative.rstrip('?')} terus berlanjut...",
            "human_place_bridge": bridge.get("chain", []),
            "place_relation": bridge.get("place_relation"),
            "suggested_story_type": "future",
            "note": "Projection angle based on future-signal queries in cluster"
        })

    return opportunities


def _reformulate_as_why_question(query: str) -> str:
    """Reformulates a search query into a WHY editorial question."""
    q = query.strip().rstrip("?")

    # Already a why question
    if q.lower().startswith(("kenapa", "mengapa", "bagaimana bisa")):
        return q + "?"

    # How-to → Why transformation
    how_to_patterns = [
        (r"^cara\s+", "Kenapa orang masih perlu "),
        (r"^tips\s+", "Kenapa "),
        (r"^panduan\s+", "Kenapa "),
    ]
    for pattern, prefix in how_to_patterns:
        if re.match(pattern, q, re.IGNORECASE):
            tail = re.sub(pattern, "", q, flags=re.IGNORECASE)
            return f"{prefix}{tail}?"

    # General → Why wrap
    return f"Kenapa {q.lower()}?"


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def load_cache(cache_path: Path) -> Optional[Dict[str, Any]]:
    """Load cached mining results if they exist."""
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(cache_path: Path, data: Dict[str, Any]) -> None:
    """Save mining results to cache file."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Main question mining pipeline
# ---------------------------------------------------------------------------

def mine_questions(
    dataset_path: Path,
    output_path: Optional[Path] = None,
    top_k: int = 10,
    min_cluster_size: int = 1,
    embedding_provider: Optional[Any] = None,
    reranker_provider: Optional[Any] = None,
    force_rebuild: bool = False,
    threshold: Optional[float] = None,
    adaptive: bool = True,
    max_queries: Optional[int] = None
) -> Dict[str, Any]:
    """
    Full question mining pipeline with adaptive and configurable clustering.
    
    Args:
        dataset_path: Path to search results dataset (JSON/JSONL)
        output_path: Optional path to save results
        top_k: Maximum number of story opportunities to return
        min_cluster_size: Minimum queries for a cluster to be kept
        embedding_provider: Optional pre-instantiated embedding provider
        reranker_provider: Optional pre-instantiated reranker provider
        force_rebuild: Force cluster rebuild even if cache is current
        threshold: Optional explicit cosine distance threshold (overrides adaptive)
        adaptive: Whether to derive threshold automatically when threshold is None
        max_queries: Optional cap on number of queries to cluster (useful for smoke tests)
        
    Returns:
        dict with: queries, clusters, story_opportunities, metadata
    """
    from engine.editorial.intent_classifier import classify_intent
    from engine.editorial.human_place_engine import evaluate_human_place_anchor

    # ── Step 1: Load dataset ──────────────────────────────────────────────
    records, fingerprint = load_dataset(dataset_path)
    queries = extract_queries(records)

    if not queries:
        logger.warning("No queries extracted from dataset.")
        return {
            "queries": [],
            "clusters": [],
            "story_opportunities": [],
            "metadata": {"error": "No queries found in dataset", "fingerprint": fingerprint}
        }

    # ── Step 2: Check cache ───────────────────────────────────────────────
    cache_path = (output_path.parent / f".cache_{output_path.stem}.json"
                  if output_path else dataset_path.parent / ".question_mining_cache.json")

    cached = load_cache(cache_path) if not force_rebuild else None
    if cached and cached.get("fingerprint") == fingerprint:
        # If user explicitly overrode threshold or max_queries, ensure cached settings match
        cached_meta = cached.get("metadata", {})
        cached_thresh = cached_meta.get("clustering_threshold")
        if (threshold is None or cached_thresh == threshold) and (max_queries is None):
            logger.info(f"Using cached results (fingerprint: {fingerprint})")
            return cached

    # ── Step 3: Initialize providers ─────────────────────────────────────
    if embedding_provider is None:
        from engine.providers.embedding import LocalEmbeddingProvider
        embedding_provider = LocalEmbeddingProvider()

    if reranker_provider is None:
        from engine.providers.reranker import LocalRerankerProvider
        reranker_provider = LocalRerankerProvider()

    # ── Step 4: Intent classification ────────────────────────────────────
    intent_results = []
    human_place_filtered = []

    for query in queries:
        intent_result = classify_intent(query)
        anchor_result = evaluate_human_place_anchor(query)

        intent_results.append({
            "query": query,
            "intents": intent_result["intents"],
            "primary_intent": intent_result["primary_intent"],
            "human_place_implied": intent_result["human_place_implied"],
            "is_procedural_only": intent_result["is_procedural_only"],
            "anchor_passed": anchor_result["passed"],
            "anchor_score": anchor_result["score"]
        })

        if anchor_result["passed"] or intent_result["human_place_implied"]:
            human_place_filtered.append(query)

    logger.info(f"Queries: {len(queries)} total, {len(human_place_filtered)} with Human–Place connection")

    # ── Step 5: Embed queries ─────────────────────────────────────────────
    if not human_place_filtered:
        # Fall back to all queries if none passed filter
        human_place_filtered = queries
        logger.warning("No queries passed Human–Place filter — using all queries for clustering")

    if max_queries is not None and max_queries > 0:
        human_place_filtered = human_place_filtered[:max_queries]

    try:
        embeddings = _get_embeddings_batch(human_place_filtered, embedding_provider)
        # Filter out empty embeddings
        valid_pairs = [(q, e) for q, e in zip(human_place_filtered, embeddings) if e]
        if valid_pairs:
            valid_queries, valid_embeddings = zip(*valid_pairs)
            valid_queries, valid_embeddings = list(valid_queries), list(valid_embeddings)
        else:
            valid_queries, valid_embeddings = human_place_filtered, [[]] * len(human_place_filtered)
            logger.warning("All embeddings are empty — clustering may be imprecise")
    except Exception as e:
        logger.warning(f"Embedding failed: {e}. Clustering will use fallback keyword similarity.")
        valid_queries = human_place_filtered
        valid_embeddings = [[]] * len(human_place_filtered)

    # ── Step 6: Cluster (Adaptive or Configured) ───────────────────────────
    if threshold is not None:
        effective_threshold = float(threshold)
        threshold_source = "manual_override"
    elif adaptive:
        effective_threshold = calculate_adaptive_threshold(valid_embeddings)
        threshold_source = "adaptive"
    else:
        effective_threshold = 0.30
        threshold_source = "default"

    raw_clusters = agglomerative_cluster(
        valid_queries,
        valid_embeddings,
        threshold=effective_threshold,
        adaptive=False
    )

    # Filter by minimum size
    raw_clusters = [c for c in raw_clusters if len(c) >= min_cluster_size]

    # ── Step 7: Validate with reranker ───────────────────────────────────
    enriched_clusters = validate_clusters_with_reranker(raw_clusters, valid_queries, reranker_provider)

    # ── Step 8: Generate story opportunities ─────────────────────────────
    all_opportunities = []
    for cluster in enriched_clusters:
        opps = generate_story_opportunities(cluster, intent_results)
        all_opportunities.extend(opps)

    # Deduplicate and take top_k
    seen_titles = set()
    unique_opportunities = []
    for opp in all_opportunities:
        key = opp["suggested_title_direction"][:60]
        if key not in seen_titles:
            seen_titles.add(key)
            unique_opportunities.append(opp)

    top_opportunities = unique_opportunities[:top_k]

    # ── Assemble result ───────────────────────────────────────────────────
    result = {
        "queries": queries,
        "human_place_queries": human_place_filtered,
        "intent_classifications": intent_results,
        "clusters": enriched_clusters,
        "story_opportunities": top_opportunities,
        "metadata": {
            "fingerprint": fingerprint,
            "dataset_path": str(dataset_path),
            "total_records": len(records),
            "total_queries": len(queries),
            "human_place_queries": len(human_place_filtered),
            "cluster_count": len(enriched_clusters),
            "opportunity_count": len(top_opportunities),
            "embedding_available": bool(valid_embeddings and valid_embeddings[0]),
            "clustering_method": "agglomerative_cosine",
            "adaptive_threshold": effective_threshold,
            "clustering_threshold": effective_threshold,
            "threshold_source": threshold_source,
            "query_count": len(queries),
            "embedding_model": getattr(embedding_provider, "model", "local-embedding")
        }
    }

    # ── Save cache ────────────────────────────────────────────────────────
    save_cache(cache_path, result)

    # ── Save output if requested ──────────────────────────────────────────
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {output_path}")

    return result
