import re
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from engine.providers.evidence_model import classify_source_tier, SourceTier, SourceType

logger = logging.getLogger(__name__)


class WebResearchProvider:
    """
    Abstract interface for web research.
    Model-agnostic and provider-agnostic.
    """
    
    def search(
        self,
        query: str,
        recency: Optional[str] = None,
        domains: Optional[List[str]] = None,
        language: str = "id-id",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


def classify_source_quality(url: str, publisher: str) -> Dict[str, Any]:
    """
    Classifies source quality according to the normalized S0-S7 hierarchy.
    Maintains full backward compatibility with integer 'tier' (1-7).
    Legacy mapping:
      S0, S1, S2 -> tier: 1 (Primary / Academic)
      S3, S4     -> tier: 4 (Reputable Journalism)
      S5         -> tier: 5 (Industry Publication)
      S6         -> tier: 6 (Secondary Commentary)
      S7         -> tier: 7 (Social Media / Weak)
    """
    res = classify_source_tier(url, publisher)
    tier_enum: SourceTier = res["tier"]
    
    # Map to legacy integer tier for test compatibility
    if tier_enum in (SourceTier.S0, SourceTier.S1, SourceTier.S2):
        legacy_tier = 1
    elif tier_enum in (SourceTier.S3, SourceTier.S4):
        legacy_tier = 4
    elif tier_enum == SourceTier.S5:
        legacy_tier = 5
    elif tier_enum == SourceTier.S6:
        legacy_tier = 7  # Legacy tier 7 was Social Media
    else:
        legacy_tier = 6  # Legacy tier 6 was Secondary Commentary / Web default

    return {
        "tier": legacy_tier,
        "source_tier": tier_enum.value,
        "source_tier_rank": tier_enum.rank,
        "tier_code": tier_enum.value,
        "tier_name": res["tier_name"],
        "source_type": res["source_type"].value,
        "reliability": res["reliability"],
        "is_primary": res["is_primary"],
    }


class DDGSWebResearchProvider(WebResearchProvider):
    """
    DuckDuckGo search provider via ddgs.
    Extracts structured results with source evaluation tiers.
    """
    
    def search(
        self,
        query: str,
        recency: Optional[str] = None,
        domains: Optional[List[str]] = None,
        language: str = "id-id",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        structured_results = []
        try:
            from ddgs import DDGS
            ddgs = DDGS()
            
            # Formulate query with site filters if domains specified
            enhanced_query = query
            if domains:
                site_filter = " OR ".join([f"site:{d}" for d in domains])
                enhanced_query = f"{query} ({site_filter})"
                
            raw_results = list(ddgs.text(
                enhanced_query,
                timelimit=recency, # 'd' for day, 'w' for week, 'm' for month, 'y' for year
                max_results=max_results
            ))
            
            for r in raw_results:
                url = r.get("href", "")
                title = r.get("title", "")
                body = r.get("body", "")
                domain = urlparse(url).netloc
                
                classification = classify_source_quality(url, domain)
                
                structured_results.append({
                    "source": domain,
                    "title": title,
                    "date": r.get("date", "Recent"),
                    "url": url,
                    "content": body,
                    "publisher": domain,
                    "relevance": "HIGH" if any(w in title.lower() for w in query.lower().split()[:2]) else "MEDIUM",
                    "source_tier": classification["tier"],
                    "source_tier_code": classification["tier_code"],
                    "source_tier_name": classification["tier_name"],
                    "reliability": classification["reliability"],
                    "is_primary": classification["is_primary"]
                })
                
        except Exception as e:
            logger.warning(f"DDGS web search failed: {e}. Returning mock/empty fallback.")
            
        return structured_results


class SearXNGWebResearchProvider(WebResearchProvider):
    """
    SearXNG metasearch provider.
    Connects to private LAN or public SearXNG instance if configured.
    """
    def __init__(self, endpoint_url: Optional[str] = None):
        import os
        self.endpoint_url = endpoint_url or os.getenv("SEARXNG_URL", "http://localhost:8080")

    def search(
        self,
        query: str,
        recency: Optional[str] = None,
        domains: Optional[List[str]] = None,
        language: str = "id-id",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        results = []
        try:
            params = {
                "q": query,
                "format": "json",
                "language": language,
            }
            if recency:
                params["time_range"] = "month" if recency == "m" else ("day" if recency == "d" else "year")
            url = f"{self.endpoint_url}/search?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "NugiContentIntelligence/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_results = data.get("results", [])[:max_results]
                for r in raw_results:
                    r_url = r.get("url", "")
                    domain = urlparse(r_url).netloc
                    classification = classify_source_quality(r_url, domain)
                    results.append({
                        "source": domain,
                        "title": r.get("title", ""),
                        "date": r.get("publishedDate", "Recent"),
                        "url": r_url,
                        "content": r.get("content", ""),
                        "publisher": domain,
                        "relevance": "HIGH",
                        "source_tier": classification["tier"],
                        "source_tier_code": classification["tier_code"],
                        "source_tier_name": classification["tier_name"],
                        "reliability": classification["reliability"],
                        "is_primary": classification["is_primary"]
                    })
        except Exception as e:
            logger.warning(f"SearXNG query failed: {e}. Returning empty list.")
        return results


class ResilientWebResearchProvider(WebResearchProvider):
    """
    Hybrid resilient web search provider:
    Attempts SearXNG first if SEARXNG_URL is configured in environment,
    and seamlessly falls back to DuckDuckGo (DDGS) if SearXNG is unavailable or not configured.
    """
    def __init__(self, searxng_url: Optional[str] = None):
        import os
        self.searxng_url = searxng_url or os.getenv("SEARXNG_URL")
        self.searxng = SearXNGWebResearchProvider(self.searxng_url) if self.searxng_url else None
        self.ddgs = DDGSWebResearchProvider()

    def search(
        self,
        query: str,
        recency: Optional[str] = None,
        domains: Optional[List[str]] = None,
        language: str = "id-id",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        if self.searxng:
            try:
                results = self.searxng.search(query, recency=recency, domains=domains, language=language, max_results=max_results)
                if results:
                    return results
            except Exception as e:
                logger.info(f"SearXNG search unavailable ({e}), falling back to DDGS.")

        return self.ddgs.search(query, recency=recency, domains=domains, language=language, max_results=max_results)

