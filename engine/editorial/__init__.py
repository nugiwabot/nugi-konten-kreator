"""
Nugi Content Creator — Editorial Intelligence Engine v2
Editorial taxonomy, property bridge evaluation, and quality gate modules.
"""

from engine.editorial.taxonomy import (
    PRIMARY_DOMAINS,
    ANCHORS,
    LENSES,
    RESEARCH_MODES,
    DNA_MATRICES,
    classify_topic
)
from engine.editorial.property_bridge import (
    evaluate_property_anchor,
    find_property_bridge
)
from engine.editorial.fit_score import (
    calculate_editorial_fit,
    DIMENSION_WEIGHTS,
    MIN_PASSING_SCORE
)
from engine.editorial.quality_gate import (
    check_quality_gates,
    check_anti_patterns,
    FORBIDDEN_ANTI_PATTERNS
)
