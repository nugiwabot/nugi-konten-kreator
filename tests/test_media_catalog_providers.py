"""Mocked coverage for the public visual-media catalog adapters."""

from engine.providers.media_catalog_providers import (
    DPLAProvider, DVIDSMediaProvider, EuropeanaProvider, NASAMediaProvider, OpenverseProvider,
)


def test_openverse_preserves_asset_license_attribution_and_landing_page():
    provider = OpenverseProvider()
    provider._json = lambda *args, **kwargs: {"results": [{
        "id": "ov-1", "title": "Jakarta archive", "url": "https://cdn.example/image.jpg",
        "thumbnail": "https://cdn.example/thumb.jpg", "foreign_landing_url": "https://example.org/item/1",
        "license": "by-sa", "license_url": "http://creativecommons.org/licenses/by-sa/4.0/",
        "creator": "A. Photographer", "attribution": "A. Photographer / CC BY-SA",
    }]}

    items = provider.search_media("Jakarta archive", media_type="image", max_results=2)
    assert len(items) == 1
    item = items[0]
    assert item.source_url == "https://example.org/item/1"
    assert item.download_url == "https://cdn.example/image.jpg"
    assert item.rights_status == "CC_BY_SA"
    assert item.license_url == "http://creativecommons.org/licenses/by-sa/4.0/"
    assert item.metadata["attribution"] == "A. Photographer / CC BY-SA"


def test_dpla_uses_item_rights_and_does_not_assume_preview_is_reusable():
    provider = DPLAProvider(api_key="test-key")
    provider._json = lambda *args, **kwargs: {"docs": [{"doc": {
        "id": "dpla-1", "object": "https://cdn.example/preview.jpg",
        "isShownAt": "https://dp.la/item/1", "sourceResource": {
            "title": "Historic Jakarta", "creator": ["Archivist"],
            "rights": ["http://rightsstatements.org/vocab/InC/1.0/"],
        }, "provider": {"name": "Example Archive"},
    }}]}

    item = provider.search_media("Jakarta", media_type="image", max_results=1)[0]
    assert item.source_url == "https://dp.la/item/1"
    assert item.download_url == "https://cdn.example/preview.jpg"
    assert item.rights_status == "UNKNOWN"
    assert "InC" in item.metadata["rights_statement"]


def test_europeana_requires_key_and_maps_explicit_edm_rights():
    unavailable = EuropeanaProvider(api_key="")
    assert unavailable.search_media("archive") == []

    provider = EuropeanaProvider(api_key="test-key")
    provider._json = lambda *args, **kwargs: {"items": [{
        "id": "/en/1", "title": ["Museum photograph"], "edmIsShownAt": ["https://museum.example/item/1"],
        "edmIsShownBy": ["https://museum.example/files/1.jpg"], "edmPreview": ["https://api.europeana.eu/preview/1.jpg"],
        "edmRights": ["http://creativecommons.org/licenses/by/4.0/"], "dataProvider": ["Museum"],
    }]}
    item = provider.search_media("museum", media_type="image", max_results=1)[0]
    assert item.rights_status == "CC_BY"
    assert item.license_url == "http://creativecommons.org/licenses/by/4.0/"
    assert item.source_url == "https://museum.example/item/1"
    assert item.download_url == "https://museum.example/files/1.jpg"


def test_nasa_resolves_video_manifest_and_keeps_unstated_rights_unknown():
    provider = NASAMediaProvider()

    def response(url, **kwargs):
        if "/search?" in url:
            return {"collection": {"items": [{
                "data": [{"nasa_id": "N-1", "media_type": "video", "title": "Earth from orbit",
                          "description": "NASA video", "center": "NASA", "date_created": "2020-01-01"}],
                "links": [{"rel": "preview", "href": "https://images.example/thumb.jpg"}],
            }]}}
        return {"collection": {"items": [{"href": "https://images-assets.nasa.gov/video/N-1/N-1~orig.mp4"}]}}

    provider._json = response
    item = provider.search_media("Earth orbit", media_type="video", max_results=1)[0]
    assert item.download_url.endswith(".mp4")
    assert item.rights_status == "UNKNOWN"
    assert item.metadata["center"] == "NASA"
    assert item.metadata["rights_policy"].startswith("NASA_or_third_party")


def test_dvids_requires_key_and_retains_credit_terms_and_video_file():
    assert DVIDSMediaProvider(api_key="").search_media("ship") == []
    provider = DVIDSMediaProvider(api_key="test-key")

    def response(url, **kwargs):
        if "/search?" in url:
            return {"results": [{"id": "video:7", "type": "video", "title": "Ship at sea",
                                 "url": "https://www.dvidshub.net/video/7/ship", "thumbnail": "https://cdn.example/thumb.jpg"}]}
        return {"results": {
            "id": "video:7", "type": "video", "title": "Ship at sea",
            "url": "https://www.dvidshub.net/video/7/ship", "description": "Official footage",
            "date": "2024-01-02", "credit": [{"name": "Sgt Example"}],
            "location": {"country": "United States"}, "files": [{"src": "https://cdn.example/ship.mp4", "type": "video/mp4"}],
        }}

    provider._json = response
    item = provider.search_media("ship", media_type="video", max_results=1)[0]
    assert item.download_url == "https://cdn.example/ship.mp4"
    assert item.source_url.startswith("https://www.dvidshub.net/video/")
    assert item.creator == "Sgt Example"
    assert item.rights_status == "COMMERCIAL_ALLOWED"
    assert item.metadata["terms_url"].endswith("/tos")
