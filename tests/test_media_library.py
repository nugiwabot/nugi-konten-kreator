"""
Tests for Persistent Local Media Library Catalog.
"""
import pytest
from pathlib import Path
from engine.pipeline.media_library import MediaLibrary, MediaLibraryEntry


def test_media_library_registration_and_search(tmp_path):
    catalog_path = tmp_path / "test_catalog.json"
    library = MediaLibrary(catalog_path=catalog_path)
    
    # Create a dummy physical file
    dummy_img = tmp_path / "station_commuter.jpg"
    dummy_img.write_bytes(b"dummy image bytes for testing sha256 checksum")

    entry = library.register_asset(
        local_path=str(dummy_img),
        provider="wikimedia",
        source_url="https://commons.wikimedia.org/wiki/File:Station.jpg",
        download_url="https://upload.wikimedia.org/File:Station.jpg",
        title="Suasana Stasiun Kereta Manggarai Pagi Hari",
        description="Kerumunan komuter menaiki KRL Jabodetabek",
        media_type="image",
        entities=["Manggarai", "KRL", "Komuter"],
        query="stasiun manggarai komuter",
        visual_requirement="REAL_PREFERRED"
    )

    assert entry is not None
    assert library.total_entries == 1
    assert len(entry.sha256) == 64

    # Search local
    hits = library.search_local(
        query="suasana komuter stasiun",
        media_type="image",
        entities=["Manggarai"],
        visual_requirement="REAL_PREFERRED"
    )

    assert len(hits) == 1
    assert hits[0]["title"] == "Suasana Stasiun Kereta Manggarai Pagi Hari"
    assert hits[0]["is_local_reuse"] is True
    assert hits[0]["score"] >= 0.5


def test_media_library_ignores_missing_physical_files(tmp_path):
    catalog_path = tmp_path / "test_catalog2.json"
    library = MediaLibrary(catalog_path=catalog_path)
    
    # Register an entry with non-existent file
    res = library.register_asset(
        local_path=str(tmp_path / "ghost_file.mp4"),
        provider="archive",
        source_url="http://archive.org",
        download_url="http://archive.org/video.mp4",
        title="Ghost Video",
        description="Non-existent video",
    )
    assert res is None
    assert library.total_entries == 0
