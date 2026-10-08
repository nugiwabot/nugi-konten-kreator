from engine.pipeline.media_finder import MediaFinder, MediaFinderItem
from engine.pipeline.visual_requirements import classify_future_intent, classify_visual_era
from engine.providers.media import MediaItem, MediaProvider


class OneImageProvider(MediaProvider):
    PROVIDER_NAME = "wikimedia"

    def __init__(self):
        self.calls = 0

    def search_media(self, query, media_type="any", max_results=20):
        self.calls += 1
        return [MediaItem(
            provider="wikimedia", id="image-1", title="D-Day Normandy 1944 archival photo",
            description="Historical photograph", media_type="image",
            source_url="https://commons.wikimedia.org/wiki/File:dday.jpg",
            download_url="https://upload.wikimedia.org/dday.jpg", thumbnail_url="",
            creator="", date="1944", license="CC BY-SA",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        )]

    def get_media_metadata(self, item_id):
        return None


class FakeRanker:
    def rank(self, original_request, candidates, top_n=10, **kwargs):
        for i, item in enumerate(candidates, 1):
            item.final_rank = i
            item.reranker_score = 0.9
            item.keyword_score = 0.9
        return candidates[:top_n], ""


class CountingVerifier:
    def __init__(self, status="VISUALLY_CONSISTENT"):
        self.calls = []
        self.status = status

    def verify(self, candidate, request, context):
        self.calls.append((candidate.title, request, context))
        from engine.pipeline.visual_verification import VisualVerification
        return VisualVerification(status=self.status, method="mock", reason="mocked check")


def test_visual_verifier_is_used_only_for_real_fact_shortlist():
    provider = OneImageProvider()
    verifier = CountingVerifier()
    finder = MediaFinder(providers=[provider], ranker=FakeRanker(), visual_verifier=verifier)

    result = finder.find("D-Day Normandy 1944", media="photo", era="historical", visual_requirement="REAL_REQUIRED", count=1)
    assert len(verifier.calls) == 1
    assert result.results[0].visual_verification_status == "VISUALLY_CONSISTENT"
    assert result.results[0].visual_verification_method == "mock"


def test_visual_mismatch_is_removed_from_real_required_results():
    finder = MediaFinder(providers=[OneImageProvider()], ranker=FakeRanker(), visual_verifier=CountingVerifier("VISUAL_MISMATCH"))
    result = finder.find("D-Day Normandy 1944", media="photo", era="historical", visual_requirement="REAL_REQUIRED", count=1)
    assert result.results == []
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_visual_mismatch_is_removed_from_real_preferred_results_too():
    finder = MediaFinder(providers=[OneImageProvider()], ranker=FakeRanker(), visual_verifier=CountingVerifier("VISUAL_MISMATCH"))
    result = finder.find("D-Day Normandy 1944", media="photo", era="historical", visual_requirement="REAL_PREFERRED", count=1)
    assert result.results == []


def test_default_visual_verification_is_explicitly_unknown():
    finder = MediaFinder(providers=[OneImageProvider()], ranker=FakeRanker())
    result = finder.find("D-Day Normandy 1944", media="photo", era="historical", visual_requirement="REAL_REQUIRED", count=1)
    assert result.results[0].visual_verification_status == "VISUAL_UNKNOWN"
    assert "No image/video verification model" in result.results[0].visual_verification_reason


def test_verifier_only_checks_top_five_results():
    finder = MediaFinder(providers=[], visual_verifier=CountingVerifier())
    items = [MediaFinderItem(
        rank=index + 1, title=f"candidate {index}", provider="test", media_type="image",
        score=1.0 - index / 10, source_url="https://example.org/item",
        download_url="https://example.org/image.jpg",
    ) for index in range(8)]
    verifier = finder.visual_verifier

    finder._verify_shortlist(items, "Specific historic event", "REAL_REQUIRED", "historical", "")

    assert len(verifier.calls) == 5


def test_future_classification_distinguishes_ai_present_from_future_concepts():
    assert classify_visual_era("AI is used in offices today") == "present"
    assert classify_visual_era("An AI-generated portrait today") == "present"
    assert classify_visual_era("A speculative Jakarta in 2050") == "future"
    assert classify_visual_era("research-backed housing projection") == "future"
    assert classify_visual_era("forecast for next year's housing market") == "future"
    assert classify_future_intent("research-backed housing projection") == "RESEARCH_BACKED"
    assert classify_future_intent("generated speculative city") == "SPECULATIVE"
