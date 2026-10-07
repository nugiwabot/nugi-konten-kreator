"""
Nugi Content Creator — Editorial Intelligence Engine v3
HUMAN × PLACE × CHANGE × WHY

Modules:
- human_place_engine: Human–Place Anchor Test (replaces property_bridge)
- taxonomy: Topic classification (domains, anchors, lenses)
- fit_score: 100-point editorial fit scoring (v3)
- quality_gate: Hard rejection rules and anti-pattern detection
- intent_classifier: Query intent classification (15 intent classes)
- story_type: Narrative archetype selection (10 story types)
- revelation_engine: Revelation quality evaluation
- question_mining: Search query → editorial opportunity pipeline

Backward compatibility:
- evaluate_property_anchor and find_property_bridge remain importable
  from engine.editorial (they now call human_place_engine under the hood)
"""

from engine.editorial.taxonomy import (
    PRIMARY_DOMAINS,
    ANCHORS,
    LENSES,
    RESEARCH_MODES,
    DNA_MATRICES,
    classify_topic
)
from engine.editorial.human_place_engine import (
    evaluate_human_place_anchor,
    find_human_place_bridge,
    evaluate_human_place_criteria,
    HUMAN_PLACE_CRITERIA,
    CANONICAL_HUMAN_PLACE_BRIDGES,
    # Backward-compat aliases
    evaluate_property_anchor,
    find_property_bridge
)
from engine.editorial.fit_score import (
    calculate_editorial_fit,
    DIMENSION_WEIGHTS,
    MIN_PASSING_SCORE,
    MIN_HUMAN_PLACE_ANCHOR
)
from engine.editorial.quality_gate import (
    check_quality_gates,
    check_anti_patterns,
    FORBIDDEN_ANTI_PATTERNS
)
from engine.editorial.intent_classifier import (
    classify_intent,
    classify_multiple_queries,
    INTENT_DEFINITIONS
)
from engine.editorial.story_type import (
    classify_story_type,
    get_narrative_device,
    is_contradiction_required,
    list_story_types,
    STORY_TYPES,
    NARRATIVE_DEVICES
)
from engine.editorial.revelation_engine import (
    check_revelation_quality,
    generate_revelation_template,
    evaluate_revelation
)
from engine.editorial.script_auditor import (
    ScriptAuditor,
    EvidenceResolver,
    EvidenceItem,
    ExtractedClaim,
    ClaimVerificationResult,
    ScriptAuditReport,
    ClaimType,
    VerificationStatus,
    Severity,
    OverallStatus,
    extract_claims_from_text,
    audit_script_file,
    evaluate_nugi_property_brand_fit,
    PROPERTY_DIMENSION_KEYWORDS
)

__all__ = [
    # Taxonomy
    "PRIMARY_DOMAINS", "ANCHORS", "LENSES", "RESEARCH_MODES", "DNA_MATRICES",
    "classify_topic",
    # Human–Place Engine (v3)
    "evaluate_human_place_anchor", "find_human_place_bridge",
    "evaluate_human_place_criteria",
    "HUMAN_PLACE_CRITERIA", "CANONICAL_HUMAN_PLACE_BRIDGES",
    # Backward compat
    "evaluate_property_anchor", "find_property_bridge",
    # Fit Score
    "calculate_editorial_fit", "DIMENSION_WEIGHTS",
    "MIN_PASSING_SCORE", "MIN_HUMAN_PLACE_ANCHOR",
    # Quality Gate
    "check_quality_gates", "check_anti_patterns", "FORBIDDEN_ANTI_PATTERNS",
    # Intent Classifier
    "classify_intent", "classify_multiple_queries", "INTENT_DEFINITIONS",
    # Story Type
    "classify_story_type", "get_narrative_device", "is_contradiction_required",
    "list_story_types", "STORY_TYPES", "NARRATIVE_DEVICES",
    # Revelation Engine
    "check_revelation_quality", "generate_revelation_template", "evaluate_revelation",
    # Script Auditor
    "ScriptAuditor", "EvidenceResolver", "EvidenceItem", "ExtractedClaim",
    "ClaimVerificationResult", "ScriptAuditReport", "ClaimType",
    "VerificationStatus", "Severity", "OverallStatus",
    "extract_claims_from_text", "audit_script_file",
    "evaluate_nugi_property_brand_fit", "PROPERTY_DIMENSION_KEYWORDS"
]
