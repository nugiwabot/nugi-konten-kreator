import logging
from typing import List, Dict, Any, Optional

from engine.providers.search import WebResearchProvider, DDGSWebResearchProvider

logger = logging.getLogger(__name__)


class ResearchAnalysis:
    """
    Structured analytical extraction from current web research.
    Enforces the deeper reasoning pipeline beyond headlines.
    """
    
    def __init__(
        self,
        topic: str,
        sources: List[Dict[str, Any]],
        what_happened: str,
        what_changed: str,
        why_it_matters: str,
        who_is_affected: str,
        human_behavior: str,
        challenged_assumption: str,
        contradiction: str,
        deeper_why: str,
        what_people_suddenly_see: str,
        facts: List[str],
        claims: List[str],
        opinions_and_speculations: List[str],
        conflicts_or_uncertainties: List[str]
    ):
        self.topic = topic
        self.sources = sources
        self.what_happened = what_happened
        self.what_changed = what_changed
        self.why_it_matters = why_it_matters
        self.who_is_affected = who_is_affected
        self.human_behavior = human_behavior
        self.challenged_assumption = challenged_assumption
        self.contradiction = contradiction
        self.deeper_why = deeper_why
        self.what_people_suddenly_see = what_people_suddenly_see
        self.facts = facts
        self.claims = claims
        self.opinions_and_speculations = opinions_and_speculations
        self.conflicts_or_uncertainties = conflicts_or_uncertainties

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "sources": self.sources,
            "reasoning": {
                "what_happened": self.what_happened,
                "what_changed": self.what_changed,
                "why_it_matters": self.why_it_matters,
                "who_is_affected": self.who_is_affected,
                "human_behavior": self.human_behavior,
                "challenged_assumption": self.challenged_assumption,
                "contradiction": self.contradiction,
                "deeper_why": self.deeper_why,
                "what_people_suddenly_see": self.what_people_suddenly_see
            },
            "epistemic_separation": {
                "facts": self.facts,
                "claims": self.claims,
                "opinions_and_speculations": self.opinions_and_speculations,
                "conflicts_or_uncertainties": self.conflicts_or_uncertainties
            }
        }


class ResearchRunner:
    """
    Executes web research and formats it into the mandatory Nugi Content Intelligence schema.
    """
    
    def __init__(self, search_provider: Optional[WebResearchProvider] = None):
        self.search_provider = search_provider or DDGSWebResearchProvider()

    def run_research(
        self,
        topic: str,
        recency: Optional[str] = "m",
        domains: Optional[List[str]] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Executes runtime research for the topic, classifies sources,
        and builds the analytical scaffolding.
        """
        sources = self.search_provider.search(
            query=topic,
            recency=recency,
            domains=domains,
            max_results=max_results
        )
        
        # Categorize facts, claims, and opinions from source bodies
        facts = []
        claims = []
        opinions = []
        
        for s in sources:
            content = s.get("content", "")
            tier = s.get("source_tier", 6)
            
            # Simple heuristic classification based on source reliability and keywords
            if tier <= 3:
                facts.append(f"[{s['source']}] {content[:150]}...")
            elif any(w in content.lower() for w in ["menurut", "klaim", "mengatakan", "stated", "claims"]):
                claims.append(f"[{s['source']}] {content[:150]}...")
            else:
                opinions.append(f"[{s['source']}] {content[:150]}...")

        return {
            "query": topic,
            "total_sources_found": len(sources),
            "sources": sources,
            "preliminary_facts": facts,
            "preliminary_claims": claims,
            "preliminary_opinions": opinions
        }
