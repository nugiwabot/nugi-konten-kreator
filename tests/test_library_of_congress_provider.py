import time
import urllib.error
from unittest.mock import patch

from engine.providers.library_of_congress_provider import LibraryOfCongressProvider
from engine.providers.rights import item_rights_status


def test_loc_adapter_preserves_item_rights_advisory_as_discovery_only():
    provider = LibraryOfCongressProvider()
    item = provider._to_media_item({
        "id": "https://www.loc.gov/item/123/",
        "title": "Historic street scene",
        "image_url": ["https://tile.loc.gov/storage-services/123.jpg"],
        "rights_advisory": ["Rights status not evaluated; consult item record."],
        "contributor": ["Photographer A"],
    })

    assert item is not None
    assert item.provider == "loc"
    assert item.media_type == "image"
    assert item.metadata["rights_advisory"].startswith("Rights status")
    assert item_rights_status(item) == "UNKNOWN"
    assert item.metadata["rights_policy"] == "discovery_only_unless_explicit_license_is_reusable"


def test_loc_adapter_obeys_retry_after_cooldown_on_429():
    provider = LibraryOfCongressProvider()
    error = urllib.error.HTTPError(
        "https://www.loc.gov/search/", 429, "Too Many Requests",
        {"Retry-After": "120"}, None,
    )
    with patch("urllib.request.urlopen", side_effect=error) as urlopen:
        assert provider.search_media("historic city", media_type="image") == []
        assert provider._cooldown_until >= time.monotonic() + 100
        assert provider.search_media("historic city", media_type="image") == []
    assert urlopen.call_count == 1
