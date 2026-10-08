"""Shared offline seams for tests that exercise research orchestration."""

import pytest


@pytest.fixture
def research_offline(monkeypatch):
    """Make research tests deterministic without replacing real evidence with fixtures."""
    from engine.pipeline.research_dossier import ResilientWebResearchProvider
    from engine.providers.crossref_provider import CrossrefProvider
    from engine.providers.gdelt_provider import GDELTProvider
    from engine.providers.openalex_provider import OpenAlexProvider

    monkeypatch.setattr(OpenAlexProvider, "search_evidence", lambda self, query, max_results=5: [])
    monkeypatch.setattr(CrossrefProvider, "search_evidence", lambda self, query, max_results=5: [])
    monkeypatch.setattr(GDELTProvider, "search_evidence", lambda self, query, max_results=5: [])
    monkeypatch.setattr(ResilientWebResearchProvider, "search", lambda self, query, recency=None, max_results=5: [])
    monkeypatch.setattr("engine.pipeline.research_dossier.RSS_DISCOVERY_ENABLED", False)
    return None


def pytest_configure(config):
    config.addinivalue_line("markers", "network: requires live internet or external services")
