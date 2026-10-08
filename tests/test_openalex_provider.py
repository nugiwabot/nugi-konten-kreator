"""Deterministic OpenAlex retrieval tests; no network dependency or fake corpus."""

import io
import json
from unittest.mock import patch

from engine.providers.openalex_provider import OpenAlexProvider


def _response(data):
    return io.BytesIO(json.dumps(data).encode("utf-8"))


def test_openalex_abstract_is_a_retrieved_snippet_not_a_quote():
    payload = {
        "results": [{
            "id": "https://openalex.org/W123",
            "title": "Urban housing and commuting",
            "publication_year": 2025,
            "doi": "https://doi.org/10.1234/example",
            "abstract_inverted_index": {"Rental": [0], "housing": [1], "affects": [2], "mobility.": [3]},
        }]
    }
    with patch("urllib.request.urlopen", return_value=_response(payload)):
        items = OpenAlexProvider().search_evidence("urban commuting", max_results=1)

    assert len(items) == 1
    assert items[0].exact_quote == ""
    assert items[0].retrieved_snippet == "Rental housing affects mobility."
    assert items[0].is_supporting is True


def test_openalex_metadata_without_abstract_is_not_supporting_evidence():
    payload = {"results": [{"id": "https://openalex.org/W456", "title": "A title only"}]}
    with patch("urllib.request.urlopen", return_value=_response(payload)):
        items = OpenAlexProvider().search_evidence("topic", max_results=1)

    assert len(items) == 1
    assert items[0].retrieved_snippet == ""
    assert items[0].exact_quote == ""
    assert items[0].is_supporting is False


def test_provider_fails_closed_when_network_fails():
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert OpenAlexProvider().search_evidence("topic", max_results=1) == []
