# Editorial Workflow Redesign Blueprint

Status: specification for staged implementation  
Repository: `nugiwabot/nugi-konten-kreator`  
Prerequisite: `docs/BASELINE_AUDIT.md`  
Scope of this document: define intended editorial behavior and acceptance criteria. This document does not implement Stage 02 or change production code.

## 1. Why this redesign exists

Nugi Content Creator already has discovery, taxonomy, story-type classification, Human–Place reasoning, Editorial Fit Score, topic deduplication, research dossier generation, script synthesis, fact-checking, visual planning, media sourcing, CapCut generation, and Final QA.

The objective is not to replace those systems. It is to make the editorial decisions before production more explicit and dependable, so an interesting headline is not automatically treated as a suitable video idea.

The target outcome is a workflow that finds specific real-world phenomena, explains why they matter to people, chooses a researchable angle, and checks early whether evidence and relevant visuals are realistically available.

## 2. Channel identity and editorial promise

### Core editorial territory

**Manusia, tempat, dan sistem yang membentuk kehidupan.**

The channel explores how human behavior, history, geography, economics, technology, culture, institutions, and designed systems shape ordinary life and the places where people live.

Property is a useful lens, not the whole channel.

### Guiding question

**“Kenapa dunia kita dibuat seperti ini?”**

A topic should help answer that question through a concrete case, phenomenon, person, place, object, decision, event, or system. The question is an editorial compass, not a requirement that every title use the same wording.

### Editorial principles

1. **Start from something concrete.** Prefer a specific observation, case, location, object, event, person, policy, dataset, or documented change over an abstract subject.
2. **Explain a mechanism.** Go beyond describing what happened. Investigate incentives, constraints, historical decisions, behavior, design, or systems that explain why it happened.
3. **Connect to human consequences.** Establish who experiences the effect and how it changes daily life, choices, time, money, access, safety, identity, opportunity, or relationships.
4. **Make claims earn their place.** Separate sourced facts from hypotheses, interpretation, uncertainty, and narrative framing.
5. **Prefer specific, relevant visuals.** Footage, archives, documents, maps, places, objects, and images should illuminate the actual story rather than merely decorate narration.
6. **Allow multiple disciplines.** History, technology, business, psychology, urban life, culture, and current affairs can qualify when a meaningful connection to the channel promise is demonstrated.
7. **Do not force a connection.** Adding the word “human”, “city”, or “system” to an unrelated topic does not make it a fit.
8. **Do not optimize for novelty alone.** A viral or recent topic still needs an appropriate angle, adequate evidence, and a reason for this channel to tell it.

## 3. Editorial workflow: from signal to production

This workflow describes editorial decisions. It must be implemented by extending the current components, not by adding a second production orchestrator.

### Stage A — Discover a real-world signal

Inputs may include RSS/Atom feeds, search leads, evergreen prompts, a user-provided question, an observable everyday phenomenon, a location, an object, a person, a policy, a study, or a documented event.

For each signal, preserve what is actually known:
- original title or description;
- origin and source URL where available;
- publisher/source name and publication date where available;
- the concrete phenomenon or case suggested;
- initial uncertainty and missing context.

A headline or search snippet is a discovery lead, not verified evidence. Discovery must not fabricate a case, a source, a statistic, or a visual asset to make a candidate look complete.

### Stage B — Establish niche alignment

Ask whether the candidate naturally connects to the channel's editorial territory. The connection must be stated in plain language, not inferred only from keyword matches.

A useful candidate should identify:
- the human, place, or system involved;
- the connection to ordinary life or a consequential human decision;
- the mechanism or relationship worth investigating;
- why this channel's perspective adds something beyond a generic news recap.

A weak candidate should be rejected or reframed rather than carried forward merely because it is trending.

### Stage C — Scope the story

Turn the broad subject into a bounded question. Identify:
- the concrete case or phenomenon;
- the central question;
- relevant geography, time period, population, or system boundaries;
- plausible alternative explanations;
- the most useful angle or a short list of competing angles;
- what evidence would be needed to answer the question.

A broad subject such as “the global economy” is not production-ready. It may be reframed as a specific mechanism in a specific place or case.

### Stage D — Assess story potential separately from niche fit

Do not collapse these into a single unexplained number.

- **Niche alignment:** Is this a natural fit for the channel?
- **Story potential:** Is there a compelling question, tension, surprise, consequence, or change to explain?
- **Researchability:** Can the key question be answered with credible evidence?
- **Human relevance:** Is there a clear consequence or recognizable stake?
- **Visual feasibility:** Is there a realistic route to relevant, authentic or clearly labelled illustrative visuals?
- **Novelty:** Is the angle meaningfully different from prior content?
- **Audience relevance:** Is there a clear reason the intended audience would care?

Any numerical weighting introduced later is provisional until tested against a representative set of previously accepted and rejected topics. Scores must not conceal hard failures or pretend to be statistically calibrated.

### Stage E — Check initial evidence leads

Identify credible places where evidence may be found: primary records, official data, original documents, academic work, first-hand testimony, reputable reporting, archives, or other relevant sources.

At discovery stage, these are leads and a feasibility signal only. They do not establish that a claim is true. If a central question appears unanswerable with available evidence, hold or re-scope the candidate.

The existing `DossierGenerator` and fact-checking path remain responsible for deeper research and claim-level verification.

### Stage F — Run a visual feasibility preflight

Before committing to a full script, look for likely access to visuals that are specific to the proposed story:
- identifiable locations and real objects;
- authentic event footage or historical archives;
- documents, photographs, maps, diagrams, or datasets;
- relevant interviews or first-hand material;
- credible sources for any visual that would be used as evidence.

Record initial visual leads and gaps. Do not claim that media is available, relevant, verified, or reusable until the existing media pipeline confirms the corresponding status and provenance.

Visual difficulty is a risk to expose, not an automatic rejection. A story can proceed with a realistic plan for maps, documents, diagrams, or clearly labelled illustrations when that approach genuinely serves the explanation.

### Stage G — Deep research and evidence dossier

Use the existing research system to build a dossier with claim-level provenance, source quality, corroboration, contradictions, dates, and uncertainty.

Maintain the existing epistemic rules:
- RSS/Atom and search snippets remain discovery-only.
- Exact quotations are reserved for text actually retrieved verbatim.
- One source alone cannot establish `VERIFIED`; independent corroboration is required.
- Heuristic evidence-strength scores are not statistical confidence.
- Missing or contradictory evidence must remain visible.

### Stage H — Story plan and script

Build the story around the central question and the evidence, not around a prewritten conclusion.

The story plan should make clear:
1. what question the audience is following;
2. what context is necessary;
3. what is discovered or explained in sequence;
4. what evidence supports each important turn;
5. which uncertainty or alternative explanation remains;
6. why the explanation matters to human life;
7. what the audience can reasonably conclude.

The script should be specific, natural to speak, and faithful to the dossier. Do not invent scenes, dialogue, quotes, motives, or causal links. Narrative tension must come from the actual question and evidence.

### Stage I — Fact-check, visual plan, and media acquisition

Keep the existing production order and gates:
- audit spoken narration against the research dossier;
- create a shot-level visual plan tied to narration and story evidence;
- source media using the existing capability, rights, relevance, and provenance controls;
- distinguish real downloaded/local-reused media from placeholders, missing media, and media not required;
- do not count placeholders as real B-roll coverage.

A visual plan should explain what a shot contributes. A generic city or person shot is not equivalent to evidence of a specific event or claim.

### Stage J — Production and final QA

Continue through the existing canonical production path:

`nugi_content_create → ProductionOrchestrator → PLAN → QUALIFY → RESEARCH → SCRIPT → FACT_CHECK → VISUAL_PLAN → MEDIA → SUBTITLE → CAPCUT → FINAL_QA`

`ProductionManifest` remains the single authoritative run state. Existing CapCut generation and validation remain the only supported implementations.

Final QA remains a hard gate. Editorial scores, a strong hook, or a high opportunity score cannot override failed fact-checking, missing required artifacts, irrelevant/missing required media, invalid manifest lineage, or failed structural validation. `VALIDATED` must not be described as `APP_VERIFIED` without the explicit desktop verification record.

### Stage K — Learn from editorial decisions

Where the existing storage contracts allow it, preserve decision rationale and evaluation outcomes so future discovery can avoid repeated failures and near-duplicates.

Learning should record:
- why an idea was selected, rejected, held, or reframed;
- whether evidence and visuals were actually found;
- whether the final script stayed within the intended scope;
- recurring errors in niche fit, sourcing, originality, and story clarity.

Do not automatically change scoring weights from one example or treat view counts alone as proof of editorial quality. Any learning mechanism should be transparent, reviewable, and tested.

## 4. Candidate decision contract

The following are **editorial decision states for a future discovery/qualification contract**. They are not claims about the current implementation, which currently returns discovery candidates with a general `DISCOVERY_ONLY` status.

| Decision | Meaning | Next action |
|---|---|---|
| `QUALIFIED` | Niche fit is clear, the question is sufficiently scoped, and there are plausible evidence leads. No known hard blocker prevents deeper research. | Eligible for deeper research. This is not approval to publish or a claim that facts are verified. |
| `NEEDS_SCOPING` | The subject may fit, but it is too broad, the human/system connection is unclear, or several competing angles remain. | Propose a narrower question or angle before deep research. |
| `ON_HOLD` | The idea may fit, but a critical evidence, access, timing, rights, or visual feasibility uncertainty remains unresolved. | Record the blocker and the information needed to reconsider. |
| `REJECTED` | The topic has no credible connection to the channel promise, duplicates existing coverage without a meaningful new angle, or has another explicit disqualifier. | Exclude from the active shortlist and preserve a concise reason when supported by existing storage. |

A candidate may also retain its source/evidence epistemic state independently. **Editorial qualification is not evidence verification.** Do not replace or overload the current `status` field without checking its callers and compatibility requirements.

### Minimum candidate information

The intended output contract should provide, where available:
- `suggested_title` and original `source_headline`;
- `source_url`, source names, and publication date when supplied;
- `primary_domain`, anchor, lens, and story type from existing classifiers;
- a concrete phenomenon/case and the human/place/system connection;
- `central_question` and proposed angle(s);
- a plain-language niche-fit explanation;
- separate niche-alignment and story-potential assessments;
- initial evidence leads and unknowns;
- visual leads and visual risks;
- overlap with prior topics and the reason for that judgment;
- decision state, decision rationale, and next action.

These are target semantics, not an instruction to add every field in one change. Later implementation stages must inspect the existing `ContentOpportunity` dataclass, MCP schemas, serialization, tests, and consumers first. Prefer additive, backward-compatible changes and derive fields where possible rather than duplicating sources of truth.

## 5. Scoring principles

If a score is exposed to help rank candidates, document the dimensions and evidence behind it. Keep at least these concepts separate:

1. Niche alignment.
2. Story potential.
3. Researchability/evidence leads.
4. Human relevance.
5. Visual feasibility.
6. Novelty relative to existing content.
7. Audience relevance.

The final decision must not be a weighted average alone. A candidate with a high curiosity score but no defensible niche connection should not pass the niche gate. A candidate with strong niche fit but no credible evidence route should be held or re-scoped, not presented as verified. A low visual score should expose a production risk rather than automatically override every other consideration.

Do not finalize numeric weights in this blueprint. Establish them in implementation only after writing test cases and evaluating a varied set of known-good, borderline, duplicate, too-broad, and off-niche examples. The existing constant `nugi_fit_score` is a known issue from the baseline audit; correcting it belongs to a later implementation stage, not this documentation-only stage.

## 6. Required separation of concerns

Keep these questions separate throughout the workflow:

- **Editorial fit:** Should this channel tell this story?
- **Scope:** What exactly are we trying to explain?
- **Evidence:** What can we responsibly claim?
- **Visuals:** What can viewers see that genuinely helps explain this case?
- **Production readiness:** Are artifacts, rights, media, and edit structure valid?
- **Publishability:** Have all required fact-check and Final QA gates passed?

No downstream stage should silently convert uncertainty from an upstream stage into certainty. If a provider is unavailable, retain an explicit unavailable/unknown state and a reason; do not synthesize a successful result.

## 7. Architecture and compatibility constraints

1. Preserve `IdeaDiscoveryEngine` as the current discovery entry point unless the audit of a concrete limitation proves a targeted change is insufficient.
2. Preserve the single `ProductionOrchestrator`, `ProductionManifest`, CapCut generator, and CapCut validator.
3. Do not introduce a parallel editorial pipeline or duplicate state store.
4. Keep compatibility MCP methods as thin wrappers over existing canonical paths.
5. Inspect every consumer before changing `ContentOpportunity`, serialized keys, decision states, or request contracts.
6. Keep RSS and search as discovery-only sources.
7. Keep rights and provenance controls; do not bypass them to increase apparent B-roll coverage.
8. Avoid new external services or dependencies unless an actual requirement cannot be met by existing components.
9. Keep changes staged, tested, and reversible. One requested stage should produce one focused commit.
10. Do not delete historical output, user-created files, or existing topic memory as part of editorial refactoring.

## 8. Evaluation plan

Before changing ranking or decisions, create a small, version-controlled set of representative discovery examples. Include at least:

- a clear niche fit with a specific human consequence;
- a potentially strong story with a weak or forced niche connection;
- a broad subject that needs scoping;
- an off-niche trending/celebrity item without a meaningful systems angle;
- a relevant evergreen topic with no recent news hook;
- a duplicate or near-duplicate of existing output;
- a relevant story whose visuals are difficult to obtain;
- a topical claim for which only a headline or one source is available.

For each case, document the expected editorial decision and why. Use deterministic unit tests for decision logic wherever possible; isolate external RSS, web, research, and media providers behind the existing seams. Tests must ensure that discovery leads are not upgraded to verified evidence and that a high score cannot bypass a hard gate.

Use the repository's existing commands as appropriate:
- `python -m compileall -q engine mcp tests/test_autonomous_intelligence.py`
- `python -m unittest discover -s tests -p "test_autonomous_intelligence.py" -v`
- `python -m pytest -q`

Report exactly which commands were run and their results. An unrun test is not a passing test. Live network/media tests remain separate from offline regression tests and must not be claimed as passed unless actually run.

## 9. Staged implementation roadmap

This blueprint intentionally does not implement the following stages:

- **Stage 02 — Niche qualification:** inspect current classifier/scoring call sites; define explicit niche assessment, hard gates, and decision reasons; remove constant niche scoring only with tests.
- **Stage 03 — Discovery and topic memory:** improve candidate provenance, deduplication visibility, and memory coverage after mapping all existing consumers and data sources.
- **Stage 04 — Scoping and angle:** make broad-topic narrowing and central-question selection explicit.
- **Stage 05 — Research dossier:** improve researchability and evidence gaps without duplicating `DossierGenerator`.
- **Stage 06 — Visual preflight:** make early visual feasibility visible without duplicating `MediaFinder` or its provenance/rights logic.
- **Stage 07–08 — Story plan, script, and fact-check:** strengthen evidence-to-narration traceability while retaining current production contracts.
- **Stage 09–10 — Visual acquisition and final QA:** improve shot relevance and verification within existing media and QA components.
- **Stage 11 — Editorial learning:** use recorded decisions and outcomes to calibrate future selection transparently.

Stages should be executed one at a time. If a stage uncovers a dependency that would materially expand its scope, stop and propose a smaller follow-up stage rather than bundling unrelated changes.

## 10. Acceptance criteria for this blueprint

This document is ready to guide implementation when:
- the channel promise and editorial principles are explicit;
- the editorial sequence distinguishes discovery, niche fit, scoping, evidence, visuals, scripting, fact-check, and production QA;
- candidate decision states and minimum information are defined;
- editorial fit, story potential, evidence quality, and production readiness are not conflated;
- architecture constraints and compatibility risks are recorded;
- an evaluation plan includes positive, negative, borderline, duplicate, and low-evidence cases;
- later stages have a clear boundary and this stage does not implement them.

## 11. Current-stage completion record

Stage 01 is documentation-only. Its deliverable is this blueprint. It does not modify production code, change serialized contracts, tune scoring weights, add tests, or begin Stage 02. Those changes require their own scoped stages and commits.
