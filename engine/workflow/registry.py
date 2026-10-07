"""
engine/workflow/registry.py
===========================
Workflow Registry for Nugi Konten Kreator.
Defines blueprints for 10 core content production workflows.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from engine.workflow.models import (
    RiskLevel,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTier,
)


class WorkflowRegistry:
    """Registry maintaining all supported Nugi workflows."""

    def __init__(self) -> None:
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._register_default_workflows()

    def register(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Retrieve workflow definition by ID."""
        return self._workflows.get(workflow_id)

    def list_all(self) -> List[WorkflowDefinition]:
        """Return all registered workflow definitions."""
        return list(self._workflows.values())

    def _register_default_workflows(self) -> None:
        # =====================================================================
        # 1. CONTENT_IDEA (Tier 1)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="content_idea",
                name="Content Idea Formulation & Editorial Qualification",
                description="Evaluate topic resonance, Human–Place anchor, Nugi Property brand fit, narrative archetype, and causal WHY angle.",
                tier=WorkflowTier.TIER_1,
                required_inputs=["topic"],
                optional_inputs=["question", "angle_preference"],
                side_effects="none",
                risk_level=RiskLevel.LOW,
                dependencies=[],
                tools_used=[
                    "nugi_editorial_classify_topic",
                    "nugi_editorial_human_place",
                    "nugi_editorial_brand_fit",
                    "nugi_editorial_story_type",
                    "nugi_thinking_why",
                    "nugi_thinking_curiosity",
                ],
                validation_steps=["brand_fit_threshold", "human_place_validation"],
                steps=[
                    WorkflowStep(
                        step_id="editorial_classify",
                        name="Editorial Classification",
                        description="Classify topic into primary domains, anchors, and lenses.",
                        tool_name="nugi_editorial_classify_topic",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="human_place",
                        name="Human–Place Connection",
                        description="Evaluate how topic connects living humans with physical spaces.",
                        tool_name="nugi_editorial_human_place",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="property_brand_fit",
                        name="Nugi Property Brand Fit",
                        description="Measure 0-20 score on Property as the lens of the story.",
                        tool_name="nugi_editorial_brand_fit",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="story_type",
                        name="Narrative Archetype Selection",
                        description="Identify narrative archetype (Hidden System, Contradiction, Origin, Reframe, etc.).",
                        tool_name="nugi_editorial_story_type",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="why_angle",
                        name="Causal WHY & Curiosity Gap",
                        description="Deconstruct underlying causal system and epistemic hook gap.",
                        tool_name="nugi_thinking_why",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="recommendation",
                        name="Editorial Synthesis",
                        description="Synthesize scores into actionable topic recommendation.",
                        tool_name="editorial_synthesis",
                        required_inputs=["topic"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 2. RESEARCH_ONLY (Tier 1)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="research_only",
                name="Evidence-First Topic Research",
                description="Execute multi-source research, source quality evaluation, fact/claim separation, and uncertainty extraction.",
                tier=WorkflowTier.TIER_1,
                required_inputs=["topic"],
                optional_inputs=["deep_mode", "sources_filter"],
                side_effects="none",
                risk_level=RiskLevel.LOW,
                dependencies=[],
                tools_used=[
                    "nugi_research_run",
                    "nugi_research_evaluate_source",
                    "nugi_research_fact_claim_split",
                    "nugi_knowledge_retrieve",
                ],
                validation_steps=["source_credibility_check", "epistemic_separation"],
                steps=[
                    WorkflowStep(
                        step_id="knowledge_retrieve",
                        name="Local Knowledge Retrieval",
                        description="Search local curated vector index for empirical books and papers.",
                        tool_name="nugi_knowledge_retrieve",
                        required_inputs=["topic"],
                        is_critical=False,
                    ),
                    WorkflowStep(
                        step_id="research_run",
                        name="Web & Archival Research",
                        description="Run multi-query search across web and academic archives.",
                        tool_name="nugi_research_run",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="source_quality",
                        name="Source Quality Classification",
                        description="Evaluate credibility tier of discovered sources (Peer-Reviewed, Official, Media).",
                        tool_name="nugi_research_evaluate_source",
                        required_inputs=["sources"],
                    ),
                    WorkflowStep(
                        step_id="fact_claim_split",
                        name="Fact / Claim / Opinion Split",
                        description="Separate empirical verifiable facts from claims and subjective opinions.",
                        tool_name="nugi_research_fact_claim_split",
                        required_inputs=["research_data"],
                    ),
                    WorkflowStep(
                        step_id="research_report",
                        name="Synthesize Research Dossier",
                        description="Assemble facts, claims, uncertainties, and evidence cards.",
                        tool_name="research_dossier_assembler",
                        required_inputs=["topic"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 3. SCRIPT_ONLY (Tier 1)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="script_only",
                name="Evidence-First Script Generation & Validation",
                description="Draft and calibrate script with factual verification, property brand fit, and quality gates.",
                tier=WorkflowTier.TIER_1,
                required_inputs=["topic"],
                optional_inputs=["draft_text", "target_word_count", "story_type"],
                side_effects="optional_file_creation",
                risk_level=RiskLevel.LOW,
                dependencies=["content_idea", "research_only"],
                tools_used=[
                    "nugi_script_parse",
                    "nugi_editorial_script_audit",
                    "nugi_editorial_fit_score",
                    "nugi_editorial_quality_gate",
                    "nugi_script_validate",
                ],
                validation_steps=["fact_audit_pass", "brand_fit_check", "word_count_check", "quality_gate_pass"],
                steps=[
                    WorkflowStep(
                        step_id="idea_qualification",
                        name="Idea Qualification",
                        description="Check topic viability and Property lens.",
                        tool_name="nugi_editorial_brand_fit",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="research_backing",
                        name="Research Dossier Gathering",
                        description="Obtain factual backing and primary citations.",
                        tool_name="nugi_research_run",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="script_generation",
                        name="Generate Script Draft",
                        description="Compose 3-layer narrative: Spoken Script, Evidence Cards, Research Notes.",
                        tool_name="nugi_script_draft",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="script_parse",
                        name="Parse Script Structure",
                        description="Extract sections, word count, and pacing continuity.",
                        tool_name="nugi_script_parse",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="fact_audit",
                        name="Fact & Epistemic Audit",
                        description="Verify claim support, overclaim, causal claims, and brand fit.",
                        tool_name="nugi_editorial_script_audit",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="editorial_fit",
                        name="Editorial Fit Score",
                        description="Calculate 100-point editorial fit score across 4 dimensions.",
                        tool_name="nugi_editorial_fit_score",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="quality_gate",
                        name="Hard Quality Gate",
                        description="Enforce hard quality gates (no hard selling, no hype CTA).",
                        tool_name="nugi_editorial_quality_gate",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="final_validation",
                        name="Script Final Validation",
                        description="Final gate check before production handoff.",
                        tool_name="nugi_script_validate",
                        required_inputs=["script_text"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 4. FACT_CHECK (Tier 1)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="fact_check",
                name="Script Fact & Narrative Verification",
                description="Audit script claims against evidence, detect causal overclaims, scope mismatches, and calculate Nugi Property brand fit.",
                tier=WorkflowTier.TIER_1,
                required_inputs=["script_text"],
                optional_inputs=["title", "evidence_items"],
                side_effects="none",
                risk_level=RiskLevel.LOW,
                dependencies=[],
                tools_used=[
                    "nugi_editorial_script_audit",
                    "nugi_research_evaluate_source",
                ],
                validation_steps=["claim_entailment_check", "brand_fit_evaluation", "overall_status_determination"],
                steps=[
                    WorkflowStep(
                        step_id="audit_engine",
                        name="Script Fact & Narrative Audit",
                        description="Full execution of ScriptAuditor: claims extraction, epistemic calibration, and brand fit.",
                        tool_name="nugi_editorial_script_audit",
                        required_inputs=["script_text"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 5. BROLL (Tier 2)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="broll",
                name="B-roll Discovery & Media Retrieval Pipeline",
                description="Parse script into visual shots, expand search queries, rank authentic media, and record provenance.",
                tier=WorkflowTier.TIER_2,
                required_inputs=["script"],
                optional_inputs=["workspace", "download_media", "count_per_shot"],
                side_effects="creates_media_files_in_output",
                risk_level=RiskLevel.MEDIUM,
                dependencies=["script_only"],
                tools_used=[
                    "nugi_script_parse",
                    "nugi_visual_analyze_script",
                    "nugi_visual_generate_shots",
                    "nugi_media_expand_query",
                    "nugi_media_find",
                    "nugi_media_download",
                    "nugi_media_provenance",
                ],
                validation_steps=["shot_coverage_check", "media_authenticity_check"],
                steps=[
                    WorkflowStep(
                        step_id="script_parse",
                        name="Parse Script Sections",
                        description="Extract script sentences and narrative blocks.",
                        tool_name="nugi_script_parse",
                        required_inputs=["script"],
                    ),
                    WorkflowStep(
                        step_id="shot_generation",
                        name="Generate Visual Shots",
                        description="Build shot requirements with Human Relatability & authenticity scores.",
                        tool_name="nugi_visual_generate_shots",
                        required_inputs=["script"],
                    ),
                    WorkflowStep(
                        step_id="query_expansion",
                        name="Expand Entity-Preserved Queries",
                        description="Generate search queries with strict entity preservation.",
                        tool_name="nugi_media_expand_query",
                        required_inputs=["shots"],
                    ),
                    WorkflowStep(
                        step_id="media_search",
                        name="Multi-Provider Search & Reranking",
                        description="Search Wikimedia, Internet Archive, and Pexafy with 2-stage reranker.",
                        tool_name="nugi_media_find",
                        required_inputs=["queries"],
                    ),
                    WorkflowStep(
                        step_id="media_download",
                        name="Download & Provenance Record",
                        description="Download approved footage and generate sources.json / broll_plan.json.",
                        tool_name="nugi_media_download",
                        required_inputs=["media_results"],
                        optional_inputs=["workspace"],
                    ),
                    WorkflowStep(
                        step_id="broll_validation",
                        name="Validate B-roll Coverage",
                        description="Verify shot coverage and minimum resolution standards.",
                        tool_name="broll_coverage_validator",
                        required_inputs=["workspace"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 6. SUBTITLE (Tier 2)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="subtitle",
                name="SRT Subtitle Generation & Validation",
                description="Generate synchronized .srt subtitles from script narrative timecodes, validate format, and preview.",
                tier=WorkflowTier.TIER_2,
                required_inputs=["script_path"],
                optional_inputs=["output_path", "wpm"],
                side_effects="creates_srt_file_in_output",
                risk_level=RiskLevel.LOW,
                dependencies=["script_only"],
                tools_used=[
                    "nugi_script_parse",
                    "nugi_subtitle_generate",
                    "nugi_subtitle_validate",
                    "nugi_subtitle_preview",
                ],
                validation_steps=["srt_syntax_check", "timecode_continuity_check"],
                steps=[
                    WorkflowStep(
                        step_id="script_parse",
                        name="Parse Script Timecodes",
                        description="Extract sections and timecodes from script.",
                        tool_name="nugi_script_parse",
                        required_inputs=["script_path"],
                    ),
                    WorkflowStep(
                        step_id="subtitle_generate",
                        name="Generate SRT Subtitle",
                        description="Write synchronized .srt file to output.",
                        tool_name="nugi_subtitle_generate",
                        required_inputs=["script_path"],
                        optional_inputs=["output_path"],
                    ),
                    WorkflowStep(
                        step_id="subtitle_validate",
                        name="Validate Subtitle Syntax",
                        description="Validate timing, character length per line, and block continuity.",
                        tool_name="nugi_subtitle_validate",
                        required_inputs=["srt_path"],
                    ),
                    WorkflowStep(
                        step_id="subtitle_preview",
                        name="Preview Subtitle",
                        description="Generate preview of first subtitle blocks.",
                        tool_name="nugi_subtitle_preview",
                        required_inputs=["srt_path"],
                        is_critical=False,
                    ),
                ],
            )
        )

        # =====================================================================
        # 7. CAPCUT_DRAFT (Tier 2)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="capcut_draft",
                name="CapCut Desktop Draft Assembly",
                description="Assemble CapCut Desktop draft project from raw footage, B-roll, and subtitles with strict preflight checking.",
                tier=WorkflowTier.TIER_2,
                required_inputs=["workspace"],
                optional_inputs=["whisper_model", "force_whisper", "install_draft"],
                side_effects="creates_capcut_draft_project",
                risk_level=RiskLevel.MEDIUM,
                dependencies=["broll", "subtitle"],
                tools_used=[
                    "nugi_capcut_generate",
                    "nugi_capcut_inspect",
                    "nugi_capcut_validate",
                    "nugi_autoedit_analyze",
                    "nugi_autoedit_validate",
                ],
                validation_steps=["workspace_preflight", "draft_schema_validation", "timeline_validation"],
                steps=[
                    WorkflowStep(
                        step_id="workspace_preflight",
                        name="Workspace Preflight Inspection",
                        description="Verify script, main footage, B-roll, and subtitle files exist before generation.",
                        tool_name="capcut_workspace_preflight",
                        required_inputs=["workspace"],
                    ),
                    WorkflowStep(
                        step_id="footage_analysis",
                        name="Analyze Raw Footage",
                        description="Inspect resolution, duration, FPS, and audio streams of main video.",
                        tool_name="nugi_autoedit_analyze",
                        required_inputs=["raw_video_path"],
                    ),
                    WorkflowStep(
                        step_id="capcut_generate",
                        name="Generate CapCut Draft Package",
                        description="Assemble tracks, audio, text, and B-roll cut points into draft_content.json.",
                        tool_name="nugi_capcut_generate",
                        required_inputs=["workspace"],
                    ),
                    WorkflowStep(
                        step_id="capcut_inspect",
                        name="Inspect CapCut Draft",
                        description="Inspect generated timeline tracks and duration.",
                        tool_name="nugi_capcut_inspect",
                        required_inputs=["draft_content_json"],
                    ),
                    WorkflowStep(
                        step_id="capcut_validate",
                        name="Validate Assembly Integrity",
                        description="Confirm valid CapCut Desktop draft structure and asset linkages.",
                        tool_name="nugi_autoedit_validate",
                        required_inputs=["workspace"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 8. SHORT_VIDEO (Tier 3 - Master Workflow)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="short_video",
                name="End-to-End Shorts Video Production",
                description="Master 11-step orchestration for Shorts (65-80s): Idea -> Research -> Script -> Fact Audit -> Editorial Audit -> Visual Plan -> B-roll -> Subtitles -> CapCut Draft -> Validation.",
                tier=WorkflowTier.TIER_3,
                required_inputs=["topic"],
                optional_inputs=["workspace", "raw_footage_path"],
                side_effects="full_project_generation",
                risk_level=RiskLevel.HIGH,
                dependencies=["content_idea", "research_only", "script_only", "fact_check", "broll", "subtitle", "capcut_draft"],
                tools_used=[
                    "nugi_editorial_classify_topic",
                    "nugi_editorial_brand_fit",
                    "nugi_research_run",
                    "nugi_script_parse",
                    "nugi_editorial_script_audit",
                    "nugi_editorial_fit_score",
                    "nugi_editorial_quality_gate",
                    "nugi_visual_generate_shots",
                    "nugi_media_find",
                    "nugi_subtitle_generate",
                    "nugi_capcut_generate",
                    "nugi_autoedit_validate",
                ],
                validation_steps=[
                    "editorial_preflight",
                    "fact_audit_pass",
                    "visual_coverage_pass",
                    "capcut_draft_pass",
                ],
                steps=[
                    WorkflowStep(
                        step_id="1_content_idea",
                        name="1. Editorial Analysis & Brand Fit",
                        description="Validate topic resonance and Nugi Property lens.",
                        tool_name="nugi_editorial_brand_fit",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="2_research",
                        name="2. Research Dossier",
                        description="Gather empirical sources, facts, and citations.",
                        tool_name="nugi_research_run",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="3_script",
                        name="3. Script Drafting",
                        description="Draft 160-185 word spoken narrative with Layer B & C.",
                        tool_name="nugi_script_draft",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="4_fact_audit",
                        name="4. Fact & Epistemic Audit",
                        description="Run ScriptAuditor verification on drafted script.",
                        tool_name="nugi_editorial_script_audit",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="5_editorial_audit",
                        name="5. Editorial Fit & Quality Gate",
                        description="Evaluate 100-point fit score and hard anti-pattern gates.",
                        tool_name="nugi_editorial_quality_gate",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="6_script_validation",
                        name="6. Script Duration & Format Check",
                        description="Check word count (160-185 words) and section pacing.",
                        tool_name="nugi_script_validate",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="7_visual_plan",
                        name="7. Visual Plan & Shot Blueprint",
                        description="Generate shot breakdown with Human Relatability metadata.",
                        tool_name="nugi_visual_generate_shots",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="8_broll",
                        name="8. B-roll Discovery & Media Matching",
                        description="Search and rank authentic archival and stock footage.",
                        tool_name="nugi_media_find",
                        required_inputs=["shots"],
                    ),
                    WorkflowStep(
                        step_id="9_subtitle",
                        name="9. Synchronized Subtitles",
                        description="Generate synchronized .srt file.",
                        tool_name="nugi_subtitle_generate",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="10_capcut_draft",
                        name="10. CapCut Draft Generation",
                        description="Generate CapCut Desktop draft project.",
                        tool_name="nugi_capcut_generate",
                        required_inputs=["workspace"],
                    ),
                    WorkflowStep(
                        step_id="11_final_validation",
                        name="11. Final End-to-End Validation",
                        description="Validate completeness of all produced assets.",
                        tool_name="nugi_autoedit_validate",
                        required_inputs=["workspace"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 9. FULL_VIDEO (Tier 3 - Longform Documentary)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="full_video",
                name="Longform Documentary Video Production",
                description="Comprehensive orchestration for documentary essays (8-15 min) with fail-fast recovery at each step.",
                tier=WorkflowTier.TIER_3,
                required_inputs=["topic"],
                optional_inputs=["workspace", "chapters_count"],
                side_effects="full_project_generation",
                risk_level=RiskLevel.HIGH,
                dependencies=["research_only", "script_only", "fact_check", "broll", "subtitle", "capcut_draft"],
                tools_used=[
                    "nugi_research_run",
                    "nugi_editorial_script_audit",
                    "nugi_editorial_quality_gate",
                    "nugi_visual_generate_shots",
                    "nugi_media_find",
                    "nugi_subtitle_generate",
                    "nugi_capcut_generate",
                    "nugi_autoedit_validate",
                ],
                validation_steps=["chapter_validation", "fact_audit_pass", "capcut_draft_pass"],
                steps=[
                    WorkflowStep(
                        step_id="1_research",
                        name="1. Comprehensive Research",
                        description="Deep multi-source research across history, urbanism, and economics.",
                        tool_name="nugi_research_run",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="2_script",
                        name="2. Longform Script & Chapters",
                        description="Generate structured chapters (Cold Open, Chapters 1-N, Synthesis).",
                        tool_name="nugi_script_draft",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="3_fact_audit",
                        name="3. Fact & Evidence Verification",
                        description="Audit all factual claims across all chapters.",
                        tool_name="nugi_editorial_script_audit",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="4_editorial_audit",
                        name="4. Editorial Quality Gate",
                        description="Enforce narrative depth and anti-pattern checks.",
                        tool_name="nugi_editorial_quality_gate",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="5_visual_plan",
                        name="5. Visual Shot Planning",
                        description="Generate chapter-by-chapter visual shot list.",
                        tool_name="nugi_visual_generate_shots",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="6_broll",
                        name="6. Archival & Historical B-roll",
                        description="Search and retrieve authentic archival footage and imagery.",
                        tool_name="nugi_media_find",
                        required_inputs=["shots"],
                    ),
                    WorkflowStep(
                        step_id="7_subtitle",
                        name="7. Subtitle Generation",
                        description="Generate synchronized .srt subtitles.",
                        tool_name="nugi_subtitle_generate",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="8_capcut_draft",
                        name="8. CapCut Desktop Assembly",
                        description="Assemble CapCut timeline with chapters and B-roll cut points.",
                        tool_name="nugi_capcut_generate",
                        required_inputs=["workspace"],
                    ),
                    WorkflowStep(
                        step_id="9_final_validation",
                        name="9. Final Project Validation",
                        description="Validate end-to-end documentary project package.",
                        tool_name="nugi_autoedit_validate",
                        required_inputs=["workspace"],
                    ),
                ],
            )
        )

        # =====================================================================
        # 10. CONTENT_AUDIT (Tier 1)
        # =====================================================================
        self.register(
            WorkflowDefinition(
                workflow_id="content_audit",
                name="Complete Multi-Dimensional Content Audit",
                description="Holistic evaluation: Fact Audit + Nugi Property Brand Fit + Human-Place + Fit Score + Quality Gate + Story Type + Revelation + Word Count -> PASS / REVISE / BLOCK.",
                tier=WorkflowTier.TIER_1,
                required_inputs=["script_text"],
                optional_inputs=["topic", "title", "target_word_count"],
                side_effects="none",
                risk_level=RiskLevel.LOW,
                dependencies=["fact_check"],
                tools_used=[
                    "nugi_editorial_script_audit",
                    "nugi_editorial_human_place",
                    "nugi_editorial_fit_score",
                    "nugi_editorial_quality_gate",
                    "nugi_editorial_story_type",
                    "nugi_editorial_revelation",
                ],
                validation_steps=["fact_pass", "brand_fit_pass", "quality_gate_pass"],
                steps=[
                    WorkflowStep(
                        step_id="fact_audit",
                        name="Fact Verification & Claims Check",
                        description="Verify claim support, overclaims, causal overstatements, and conflicting data.",
                        tool_name="nugi_editorial_script_audit",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="brand_fit",
                        name="Nugi Property Brand Fit",
                        description="Evaluate Property as the strategic lens (0-20 score).",
                        tool_name="nugi_editorial_brand_fit",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="human_place",
                        name="Human–Place Anchor Evaluation",
                        description="Check 10 Human-Place criteria and spatial resonance.",
                        tool_name="nugi_editorial_human_place",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="fit_score",
                        name="Editorial Fit Score",
                        description="Calculate 100-point editorial fit score across 4 dimensions.",
                        tool_name="nugi_editorial_fit_score",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="quality_gate",
                        name="Hard Quality Gate",
                        description="Detect promotional wording, fake urgency, and forbidden anti-patterns.",
                        tool_name="nugi_editorial_quality_gate",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="story_type",
                        name="Story Type Consistency",
                        description="Check archetype match (Hidden System, Contradiction, Transformation, etc.).",
                        tool_name="nugi_editorial_story_type",
                        required_inputs=["topic"],
                    ),
                    WorkflowStep(
                        step_id="revelation",
                        name="Revelation Quality & Epistemic Depth",
                        description="Evaluate punchline revelation and causal depth.",
                        tool_name="nugi_editorial_revelation",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="word_count",
                        name="Pacing & Word Count Audit",
                        description="Audit spoken word count and estimated natural speaking duration.",
                        tool_name="script_pacing_audit",
                        required_inputs=["script_text"],
                    ),
                    WorkflowStep(
                        step_id="final_decision",
                        name="Audit Synthesis & Decision",
                        description="Synthesize into PASS, REVISE, or BLOCK with specific guidance.",
                        tool_name="audit_synthesis_engine",
                        required_inputs=["script_text"],
                    ),
                ],
            )
        )


# Singleton instance
registry = WorkflowRegistry()
