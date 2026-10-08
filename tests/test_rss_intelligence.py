from engine.intelligence.research import build_research_intelligence
from engine.intelligence.rss import (
    FeedItem,
    FeedSource,
    RSSHTTPClient,
    parse_feed,
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

