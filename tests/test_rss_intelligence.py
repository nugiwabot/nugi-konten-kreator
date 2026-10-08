from engine.intelligence.research import build_research_intelligence
from engine.intelligence.rss import (
    FeedItem,
    FeedRegistry,
    FeedSource,
    DirectRSSAdapter,
    RSSDiscoveryService,
    RSSHTTPClient,
    RSSHubAdapter,
    parse_feed,
    cluster_feed_items,
)
from engine.pipeline.media_finder import MediaFinder
from engine.providers.capabilities import route_provider_names
from engine.providers.rights import classify_rights, is_reusable_rights_status


RSS_XML = b"""<?xml version='1.0'?>
<rss version='2.0' xmlns:media='http://search.yahoo.com/mrss/'>
  <channel><title>Example</title>
    <item>
      <title>Jakarta flood response expands</title>
      <link>https://news.example/story-1</link>
      <description>Officials describe a new response plan.</description>
      <pubDate>Wed, 07 Oct 2026 10:00:00 GMT</pubDate>
      <media:thumbnail url='https://news.example/image.jpg'/>
    </item>
  </channel>
</rss>"""


def test_parse_rss_keeps_feed_content_discovery_only():
    source = FeedSource(id="wire", name="Wire", feed_url="https://news.example/rss")
    items = parse_feed(RSS_XML, source)
    assert len(items) == 1
    assert items[0].title == "Jakarta flood response expands"
    assert items[0].image_urls == ["https://news.example/image.jpg"]
    assert items[0].evidence_status == "DISCOVERY_ONLY"
    assert items[0].rights_policy == "editorial_discovery_only"


def test_feed_parser_rejects_entity_declarations():
    payload = b"<!DOCTYPE x [<!ENTITY boom 'boom'>]><rss><channel/></rss>"
    assert parse_feed(payload, FeedSource(id="x", name="X")) == []


def test_feed_http_client_caches_bounded_payload():
    class Response:
        headers = {"content-type": "application/rss+xml"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            assert size > len(RSS_XML)
            return RSS_XML

    class Opener:
        calls = 0

        def open(self, request, timeout):
            self.calls += 1
            return Response()

    opener = Opener()
    client = RSSHTTPClient(opener=opener, cache_ttl_seconds=60, sleep_func=lambda _: None)
    assert client.fetch("https://8.8.8.8/feed")[0] == RSS_XML
    assert client.fetch("https://8.8.8.8/feed")[0] == RSS_XML
    assert opener.calls == 1


def test_rights_classifier_requires_explicit_reuse_terms():
    assert classify_rights(license_name="Public Domain") == "PUBLIC_DOMAIN"
    assert classify_rights(license_url="https://creativecommons.org/licenses/by/4.0/") == "CC_BY"
    assert classify_rights(license_name="CC BY-NC 4.0") == "RESTRICTED"
    assert classify_rights(rights_statement="No known restrictions") == "UNKNOWN"
    assert classify_rights(stated_status="UNKNOWN", license_name="CC0") == "CC0"
    assert not is_reusable_rights_status("UNKNOWN")


def test_capability_router_excludes_stock_for_required_real_media():
    route = route_provider_names(
        ["pexafy", "wikimedia", "internet_archive", "loc"],
        era="historical",
        media_type="video",
        visual_requirement="REAL_REQUIRED",
    )
    assert "pexafy" not in route
    assert "loc" not in route
    assert route[0] == "internet_archive"


def test_feed_intelligence_remains_separate_from_verified_evidence():
    feed_item = FeedItem(
        source_id="wire",
        source_name="Wire",
        feed_url="https://news.example/rss",
        title="Jakarta flood response expands",
        canonical_url="https://news.example/story-1",
    )
    intelligence = build_research_intelligence(
        "Jakarta flood response", [feed_item], evidence_entities=["Jakarta"]
    ).to_dict()
    assert intelligence["evidence_status"] == "DISCOVERY_ONLY"
    assert intelligence["rss_discoveries"][0]["evidence_status"] == "DISCOVERY_ONLY"
    assert intelligence["primary_source_queries"]
    assert not any("DISCOVERY_ONLY" == row.get("status") for row in intelligence.get("claims", []))


def test_research_broll_query_bridge_is_bounded_and_topic_related():
    result = MediaFinder._append_research_queries(
        ["Jakarta flood archival photo"],
        {"recommended_broll_queries": [
            "Jakarta flood evacuation documentary",
            "unrelated celebrity event image",
        ]},
        "Jakarta flood response",
    )
    assert "Jakarta flood evacuation documentary" in result
    assert "unrelated celebrity event image" not in result
    assert len(result) <= 10


def test_research_bridge_builds_event_place_date_queries_from_structured_fields():
    result = MediaFinder._append_research_queries(
        ["The operation began archival photo"],
        {"topic": "D-Day Normandy 1944", "recency": "historical_or_general",
         "visual_events": ["D-Day landing"], "visual_locations": ["Normandy"],
         "visual_time_periods": ["1944"]},
        "The operation began",
    )
    assert any("Normandy" in query and "1944" in query and "archival" in query for query in result)


def test_committed_registry_loads_curated_feeds_as_discovery_only():
    from pathlib import Path
    registry = FeedRegistry.from_file(Path("engine/data/feed_registry.json"))
    assert len(registry.sources) >= 8
    assert {source.id for source in registry.sources} >= {
        "brin_publications_rss", "usgs_earthquakes_hourly", "guardian_world_en", "nasa_photojournal_latest"
    }
    assert all(source.evidence_role == "discovery_only" for source in registry.sources)
    assert all(source.rights_policy == "editorial_discovery_only" or source.id == "nasa_photojournal_latest" for source in registry.sources)


def test_opml_import_to_file_persists_imported_feed_disabled(tmp_path):
    opml = b"""<opml version='2.0'><body><outline text='Local Wire' title='Local Wire' xmlUrl='https://wire.example/rss'/></body></opml>"""
    path = tmp_path / "feed_registry.json"
    registry = FeedRegistry()
    imported = registry.import_opml_to_file(opml, path=path)
    restored = FeedRegistry.from_file(path)
    assert len(imported) == 1
    assert imported[0].enabled is False
    assert restored.sources[0].feed_url == "https://wire.example/rss"
    assert restored.sources[0].evidence_role == "discovery_only"


def test_near_duplicate_headlines_share_lineage_and_expose_conflicting_numbers():
    first = FeedItem(
        source_id="publisher_a", source_name="Publisher A", feed_url="https://a.example/rss",
        title="Flood damage in Jakarta rises 20 percent", canonical_url="https://a.example/story",
    )
    second = FeedItem(
        source_id="publisher_b", source_name="Publisher B", feed_url="https://b.example/rss",
        title="Flood damage in Jakarta rises 10 percent", canonical_url="https://b.example/story",
    )
    clusters = cluster_feed_items([first, second])
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.source_count == 2
    assert cluster.source_diversity == 2
    assert cluster.locations == ["Jakarta"]
    assert cluster.corroboration == "DISCOVERY_ONLY"
    assert any("numeric" in conflict.lower() for conflict in cluster.conflicting_claims)

    copied = FeedItem(
        source_id="publisher_c", source_name="Publisher C", feed_url="https://c.example/rss",
        title=first.title, canonical_url="https://c.example/syndicated",
    )
    assert cluster_feed_items([first, copied])[0].source_diversity == 1


def test_rsshub_uses_only_explicit_self_hosted_routes_and_falls_back(monkeypatch):
    import engine.intelligence.rss as rss_module
    monkeypatch.setattr(rss_module, "RSS_DISCOVERY_ENABLED", True)
    source = FeedSource(
        id="custom_hub", name="Custom Hub", feed_url="", route_type="rsshub",
        rsshub_route="custom/source", tags=["test"],
    )

    class EmptyDirect:
        def fetch(self, source, max_items=50):
            return []

    class EmptyHub:
        def __init__(self):
            self.calls = []

        def fetch(self, source, max_items=50):
            self.calls.append(source)
            return []

    class FallbackHub:
        def __init__(self):
            self.calls = []

        def fetch(self, source, max_items=50):
            self.calls.append(source)
            return [FeedItem(source_id=source.id, source_name=source.name, feed_url=source.feed_url,
                             title="Test event lead", canonical_url="https://news.example/test")]

    hub, fallback = EmptyHub(), FallbackHub()
    service = RSSDiscoveryService(
        registry=FeedRegistry([source]), direct_adapter=EmptyDirect(), rsshub_adapter=hub,
        dynamic_base_url="https://news.example/rss", max_sources=2,
    )
    service.rsshub_fallback = fallback
    items = service.discover("test event")
    assert len(hub.calls) == 1
    assert len(fallback.calls) == 1
    assert fallback.calls[0].evidence_role == "discovery_only"
    assert items[0].evidence_status == "DISCOVERY_ONLY"


def test_rsshub_adapter_builds_route_only_from_configured_base():
    class FakeClient:
        def __init__(self):
            self.urls = []

        def fetch(self, url):
            self.urls.append(url)
            return RSS_XML, {}

    client = FakeClient()
    adapter = RSSHubAdapter("https://rsshub.internal.example", client)
    source = FeedSource(id="hub", name="Hub", route_type="rsshub", rsshub_route="route/topic")
    items = adapter.fetch(source)
    assert client.urls == ["https://rsshub.internal.example/route/topic"]
    assert len(items) == 1
    assert items[0].evidence_status == "DISCOVERY_ONLY"


def test_dynamic_rss_query_url_is_encoded_with_locale():
    service = RSSDiscoveryService(registry=FeedRegistry(), direct_adapter=DirectRSSAdapter())
    url = service._dynamic_url("Jakarta flood response", "id", "ID")
    assert "q=Jakarta+flood+response" in url
    assert "ceid=ID%3Aid" in url


def test_default_capability_matrix_routes_new_sources_and_excludes_stock_from_real_required():
    finder = MediaFinder()
    routed = [provider.PROVIDER_NAME for provider in finder._route_providers(
        "historical", "photo", visual_requirement="REAL_REQUIRED"
    )]
    assert "pexafy" not in routed
    assert {"wikimedia", "internet_archive", "loc", "openverse", "dpla", "europeana", "nasa", "dvids"} <= set(routed)

