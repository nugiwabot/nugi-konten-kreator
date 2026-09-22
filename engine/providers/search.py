import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

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
    Classifies source quality according to the 7-tier hierarchy:
    1. Primary Source / Official Gov / Academic
    2. Official Announcement
    3. Original Research
    4. Reputable Journalism
    5. Industry Publication
    6. Secondary Commentary / Blog
    7. Social Media
    """
    domain = urlparse(url).netloc.lower()
    
    # Tier 1: Primary Gov, Edu, Academic
    if any(d in domain for d in [".gov", ".go.id", ".edu", ".ac.id", "arxiv.org", "nature.com", "science.org"]):
        return {"tier": 1, "tier_name": "Primary Source / Official", "reliability": "HIGH"}
    
    # Tier 4: Reputable Journalism
    if any(d in domain for d in ["reuters.com", "bloomberg.com", "kompas.com", "tempo.co", "bisnis.com", "nytimes.com", "wsj.com", "bbc.com", "theverge.com"]):
        return {"tier": 4, "tier_name": "Reputable Journalism", "reliability": "HIGH"}
        
    # Tier 5: Industry Publication
    if any(d in domain for d in ["techcrunch.com", "inman.com", "venturebeat.com", "rumah123.com", "lamudi.co.id", "housecanary.com"]):
        return {"tier": 5, "tier_name": "Industry Publication", "reliability": "MEDIUM_HIGH"}

    # Tier 7: Social Media
    if any(d in domain for d in ["twitter.com", "x.com", "reddit.com", "tiktok.com", "instagram.com"]):
        return {"tier": 7, "tier_name": "Social Media", "reliability": "LOW_NEEDS_VERIFICATION"}
        
    # Default: Tier 6: Secondary commentary
    return {"tier": 6, "tier_name": "Secondary Commentary / Web", "reliability": "MEDIUM"}


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
                    "source_tier_name": classification["tier_name"],
                    "reliability": classification["reliability"]
                })
                
        except Exception as e:
            logger.warning(f"DDGS web search failed: {e}. Returning mock/empty fallback.")
            
        return structured_results
