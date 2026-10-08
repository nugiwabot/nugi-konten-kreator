"""Offline tests for discovery-only PubMed and Europe PMC adapters."""

import io
import json
from unittest.mock import patch

from engine.providers.scholarly_providers import EuropePMCProvider, PubMedProvider


class FakeNCBI:
    def __init__(self):
        self.calls = []

    def get(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "esearch.fcgi":
            return b"<eSearchResult><IdList><Id>123</Id></IdList></eSearchResult>"
        return b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
        <ArticleTitle>Housing and mobility study</ArticleTitle>
        <AuthorList><Author><ForeName>Ari</ForeName><LastName>Example</LastName></Author></AuthorList>
        <Journal><Title>Journal of Example Studies</Title></Journal>
        <Abstract><AbstractText Label='BACKGROUND'>An abstract about housing and mobility.</AbstractText></Abstract>
        <ELocationID EIdType='doi'>10.1000/example</ELocationID><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
        </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""


def test_pubmed_returns_abstract_as_non_supporting_discovery_record():
    client = FakeNCBI()
    items = PubMedProvider(client=client).search_evidence("housing mobility", max_results=1)
    assert len(items) == 1
    item = items[0]
    assert item.source.url == "https://doi.org/10.1000/example"
    assert item.source.published_at == "2025"
    assert item.retrieved_snippet.startswith("An abstract")
    assert item.exact_quote == ""
    assert item.is_supporting is False
    assert item.source.metadata["evidence_role"] == "RESEARCH_DISCOVERY"
    assert [call[0] for call in client.calls] == ["esearch.fcgi", "efetch.fcgi"]


def test_europe_pmc_marks_open_access_metadata_without_fetching_full_text():
    payload = {"resultList": {"result": [{
        "id": "345", "pmid": "345", "pmcid": "PMC123", "doi": "10.1234/pmc",
        "title": "Study about urban heat", "abstractText": "<p>Abstract evidence discovery.</p>",
        "authorString": "A. Author", "journalTitle": "Urban Research", "firstPublicationDate": "2024-04-03",
        "isOpenAccess": "Y",
    }]}}

    with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode("utf-8"))):
        items = EuropePMCProvider().search_evidence("urban heat", max_results=1)

    assert len(items) == 1
    item = items[0]
    assert item.source.url == "https://doi.org/10.1234/pmc"
    assert item.source.metadata["is_open_access"] is True
    assert item.source.metadata["full_text_fetched"] is False
    assert item.is_supporting is False
    assert item.exact_quote == ""
    assert "Abstract evidence discovery" in item.retrieved_snippet
