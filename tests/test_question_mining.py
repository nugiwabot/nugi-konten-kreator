"""
Tests for Question Mining Engine v1.
Verifies dataset loading, fingerprinting, caching, clustering, and story opportunities.

Important:
- Dataset is OPTIONAL and READ-ONLY
- Missing dataset must not crash the engine
- Cache invalidation via fingerprint
- Story opportunities use search queries as SIGNALS, not final titles
"""
import json
import tempfile
from pathlib import Path
import pytest

from engine.editorial.question_mining import (
    load_dataset,
    extract_queries,
    extract_documents,
    agglomerative_cluster,
    _generate_cluster_name,
    _reformulate_as_why_question,
    load_cache,
    save_cache,
    _compute_file_fingerprint
)


# ===========================================================================
# Dataset loading
# ===========================================================================

def _make_json_dataset(records: list, tmp_path: Path) -> Path:
    path = tmp_path / "test_dataset.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_load_valid_json_dataset(tmp_path):
    """Valid JSON dataset must load and return fingerprint."""
    records = [
        {"query": "kenapa harga rumah mahal", "title": "Harga Rumah 2026", "snippet": "..."},
        {"query": "AI dan remote work", "title": "Remote Work Masa Depan", "snippet": "..."}
    ]
    path = _make_json_dataset(records, tmp_path)
    loaded, fingerprint = load_dataset(path)
    assert len(loaded) == 2
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 16


def test_load_missing_dataset_raises():
    """Missing dataset must raise FileNotFoundError, not crash silently."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_dataset(Path("/nonexistent/path/data.json"))
    assert "not found" in str(exc_info.value).lower()
    assert "--dataset" in str(exc_info.value)


def test_load_empty_dataset_raises(tmp_path):
    """Empty dataset file must raise ValueError."""
    path = tmp_path / "empty.json"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataset(path)


def test_load_jsonl_dataset(tmp_path):
    """JSONL format must load correctly."""
    path = tmp_path / "data.jsonl"
    records = [
        {"query": "harga tanah Jakarta", "title": "T1", "snippet": "S1"},
        {"query": "kemacetan kota", "title": "T2", "snippet": "S2"}
    ]
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    loaded, fingerprint = load_dataset(path)
    assert len(loaded) == 2


def test_load_wrapped_json_dataset(tmp_path):
    """JSON wrapped in 'results' key must load correctly."""
    records = [{"query": "urbanisasi", "title": "T", "snippet": "S"}]
    path = tmp_path / "wrapped.json"
    path.write_text(json.dumps({"results": records, "meta": {"count": 1}}), encoding="utf-8")
    loaded, _ = load_dataset(path)
    assert len(loaded) == 1


# ===========================================================================
# Query extraction
# ===========================================================================

def test_extract_queries_from_records():
    """Queries must be extracted from multiple field names."""
    records = [
        {"query": "harga rumah 2026"},
        {"keyword": "kemacetan Jakarta"},
        {"search_query": "remote work Indonesia"},
        {"title": "ini bukan query"}  # fallback to title
    ]
    queries = extract_queries(records)
    assert len(queries) >= 3
    assert "harga rumah 2026" in queries


def test_extract_queries_deduplication():
    """Duplicate queries must be deduplicated."""
    records = [
        {"query": "harga rumah mahal"},
        {"query": "harga rumah mahal"},  # duplicate
        {"query": "AI agent masa depan"}
    ]
    queries = extract_queries(records)
    assert len(queries) == 2


def test_extract_queries_minimum_length():
    """Very short queries (< 3 chars) must be ignored."""
    records = [
        {"query": "ai"},  # too short
        {"query": "rumah"},  # acceptable
        {"query": "harga tanah"}  # acceptable
    ]
    queries = extract_queries(records)
    assert all(len(q) > 3 for q in queries)


# ===========================================================================
# Clustering
# ===========================================================================

def test_agglomerative_cluster_empty_input():
    """Clustering with empty input must return empty list."""
    result = agglomerative_cluster([], [], threshold=0.35)
    assert result == []


def test_agglomerative_cluster_single_item():
    """Single item clustering must return one cluster with one member."""
    result = agglomerative_cluster(["item1"], [[1.0, 0.0, 0.0]], threshold=0.35)
    assert len(result) == 1
    assert result[0] == [0]


def test_agglomerative_cluster_similar_items():
    """Similar items (identical vectors) must cluster together."""
    vec = [1.0, 0.0, 0.0, 0.0]
    items = ["query about house", "query about homes", "completely different topic"]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],   # house
        [0.95, 0.1, 0.0, 0.0],   # homes (similar to house)
        [0.0, 0.0, 0.0, 1.0]     # different
    ]
    clusters = agglomerative_cluster(items, embeddings, threshold=0.35)
    # house and homes should be in the same cluster
    cluster_for_house = None
    cluster_for_different = None
    for cluster in clusters:
        if 0 in cluster:
            cluster_for_house = cluster
        if 2 in cluster:
            cluster_for_different = cluster
    assert cluster_for_house is not None
    assert 1 in cluster_for_house  # homes is close to house
    assert cluster_for_different != cluster_for_house  # different should be separate


def test_agglomerative_cluster_empty_embeddings():
    """Clustering with all-empty embeddings must not crash."""
    items = ["q1", "q2", "q3"]
    embeddings = [[], [], []]  # all empty
    clusters = agglomerative_cluster(items, embeddings, threshold=0.35)
    # Should return n single-item clusters (can't merge with empty vecs)
    assert len(clusters) >= 1


# ===========================================================================
# Cluster naming
# ===========================================================================

def test_cluster_name_generated_from_items():
    """Cluster name must be generated from content, not hardcoded."""
    items = ["harga tanah kota Jakarta", "lahan perkotaan mahal", "tanah Jakarta"]
    name = _generate_cluster_name(items)
    # Should contain significant words from the items
    assert len(name) > 3
    assert "×" in name or name.isupper()


def test_cluster_name_excludes_stop_words():
    """Cluster name must not be dominated by stop words."""
    items = ["yang di dari", "dan dengan untuk", "ini itu pada"]
    name = _generate_cluster_name(items)
    # Stop words should be filtered
    stop_words = {"yang", "dan", "di", "dari", "dengan", "untuk", "ini", "itu", "pada"}
    name_words = {w.lower() for w in name.split()}
    # No stop words in cluster name
    assert len(name_words.intersection(stop_words)) == 0 or name == "CLUSTER"


# ===========================================================================
# WHY reformulation
# ===========================================================================

def test_reformulate_how_to_as_why():
    """How-to queries must be reformulated into WHY questions."""
    result = _reformulate_as_why_question("cara membeli rumah pertama")
    assert "kenapa" in result.lower() or "mengapa" in result.lower()


def test_reformulate_preserves_why_questions():
    """Already-WHY questions must not be double-wrapped."""
    result = _reformulate_as_why_question("Kenapa harga rumah di Jakarta selalu naik?")
    assert result.startswith("Kenapa") or result.startswith("kenapa")
    # Should not double-wrap
    assert result.lower().count("kenapa") <= 1


def test_reformulate_general_query():
    """General queries must be wrapped as WHY question."""
    result = _reformulate_as_why_question("AI dan properti masa depan")
    assert "?" in result


# ===========================================================================
# Cache management
# ===========================================================================

def test_cache_save_and_load(tmp_path):
    """Cache must save and reload correctly."""
    cache_path = tmp_path / "test_cache.json"
    data = {"fingerprint": "abc123", "queries": ["q1", "q2"], "clusters": []}
    save_cache(cache_path, data)
    loaded = load_cache(cache_path)
    assert loaded is not None
    assert loaded["fingerprint"] == "abc123"
    assert loaded["queries"] == ["q1", "q2"]


def test_cache_missing_returns_none(tmp_path):
    """Missing cache must return None without error."""
    result = load_cache(tmp_path / "nonexistent_cache.json")
    assert result is None


def test_fingerprint_changes_when_file_changes(tmp_path):
    """File fingerprint must change when file content changes."""
    path = tmp_path / "data.json"
    path.write_text(json.dumps([{"query": "harga rumah"}]), encoding="utf-8")
    fp1 = _compute_file_fingerprint(path)

    path.write_text(json.dumps([{"query": "harga tanah"}]), encoding="utf-8")
    fp2 = _compute_file_fingerprint(path)

    assert fp1 != fp2


def test_fingerprint_stable_for_same_content(tmp_path):
    """File fingerprint must be stable (same result for same content)."""
    path = tmp_path / "data.json"
    content = json.dumps([{"query": "AI properti Indonesia"}])
    path.write_text(content, encoding="utf-8")
    fp1 = _compute_file_fingerprint(path)
    fp2 = _compute_file_fingerprint(path)
    assert fp1 == fp2


# ===========================================================================
# Dataset does not affect engine core
# ===========================================================================

def test_dataset_read_only(tmp_path):
    """Loading dataset must not modify the file."""
    records = [{"query": "original query"}]
    path = _make_json_dataset(records, tmp_path)
    original_fingerprint = _compute_file_fingerprint(path)

    load_dataset(path)  # Load it

    new_fingerprint = _compute_file_fingerprint(path)
    assert original_fingerprint == new_fingerprint, "Dataset file was modified!"
