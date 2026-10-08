"""Deterministic tests for source metadata versus retrieved source text."""

import io
import json
from unittest.mock import patch

from engine.providers.crossref_provider import CrossrefProvider
from engine.providers.gdelt_provider import GDELTProvider


def _response(data):
    return io.BytesIO(json.dumps(data).encode("utf-8"))


def test_crossref_metadata_is_not_mislabeled_as_verbatim_evidence():
    payload = {
        "message": {
            "items": [{
                "title": ["Housing markets and household mobility"],
                "DOI": "10.1234/example",
                "author": [{"given": "Ari", "family": "Author"}],
                "container-title": ["Journal of Example Studies"],
                "is-referenced-by-count": 12,
            }]
        }
    }
    with patch("urllib.request.urlopen", return_value=_response(payload)):
        items = CrossrefProvider().search_evidence("housing", max_results=1)

    assert len(items) == 1
    item = items[0]
    assert item.exact_quote == ""
    assert item.is_supporting is False
    assert item.source.published_at == ""  # No invented fallback publication year.
    assert item.data_points == []  # Citation count is source metadata, not a topical statistic.
    assert item.source.metadata["citations"] == 12


def test_gdelt_article_list_is_discovery_metadata_only():
    payload = {
        "articles": [{
            "url": "https://example.org/article",
            "domain": "example.org",
            "title": "A report about urban transit",
            "seendate": "20261008093000",
        }]
    }
    with patch("urllib.request.urlopen", return_value=_response(payload)):
        items = GDELTProvider().search_evidence("urban transit", max_results=1)

    assert len(items) == 1
    assert items[0].exact_quote == ""
    assert items[0].is_supporting is False
    assert items[0].summary == "A report about urban transit"
