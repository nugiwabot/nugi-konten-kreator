# Nugi Content Creator — architecture

The repository has one end-to-end production path. Focused research, media,
editorial, and diagnostic tools remain callable independently, but none owns a
second production state machine.

## Canonical call graph
## Request understanding layer

MCP natural-language requests are first resolved by a deterministic request
intent layer. This is a planning layer only; it does not create a second
executor or state store.

```text
USER REQUEST
  -> RequestIntentResolver
  -> resolved execution contract
  -> ProductionOrchestrator
```

The resolved request plan is persisted as manifest metadata so a resumed run
retains the original autonomous decision context.


```text
MCP nugi_content_create
  -> mcp.server.content_create
  -> ProductionOrchestrator.run
       -> ExecutiveProducer: production_plan.json
       -> editorial quality qualification
       -> DossierGenerator: research_dossier.json/.md
            -> BPS adapter (fail-closed until live retrieval exists)
            -> OpenAlex abstracts / Crossref metadata / GDELT discovery
            -> web retrieval with recency passed through
            -> RSS/Atom discovery leads + bounded primary-source follow-up queries
       -> DynamicScriptSynthesizer: script.md + story_plan.json
       -> audit_script_with_dossier: fact_check_report.json
       -> VisualRequirementsGenerator: broll_plan.json
       -> MediaFinder: capability-routed per-shot search, rank, rights gate, and provenance
       -> SRTGenerator: subtitles.srt
       -> TimelineData + CapCutDraftGenerator: timeline + draft package
       -> CapCutValidator: capcut_validation.json
       -> FinalQAEngine: final_qa.json
       -> ProductionManifest: run status, completed stages, artifact links
```

`mcp/workflows.py` preserves legacy workflow tool names as thin compatibility
wrappers. They delegate to `ProductionOrchestrator` and read the same
`ProductionManifest`; they do not define another executor or state store.

## Production state and reuse

`ProductionManifest` at `output/<run>/manifest.json` is the authoritative
record for a run. Resume checks the completed stage, manifest-linked artifact,
topic/run identity, requested input contract, and stage-specific validity before
reuse. Invalidating an upstream stage clears downstream completion and artifact
claims. A file merely existing on disk is not sufficient evidence of a
completed stage.

External research and media results can vary with provider availability and
recency. The pipeline records those results and fails closed; it does not claim
that external calls are deterministic.

RSS/Atom headlines and their attachments are discovery metadata only. They do
not enter dossier evidence_items, support claims, or download as B-roll. The
dossier stores them separately with a DISCOVERY_ONLY status, plus bounded
follow-up search leads for source escalation. RSS is optional, cached in-process,
limited to configured feeds and response sizes, and can use an explicitly
configured self-hosted RSSHub endpoint.

## Evidence and publishability

- `exact_quote` is reserved for source text actually retrieved verbatim.
  Search-result snippets and bibliographic metadata remain separate.
- Citation counts are source metadata, not topical statistics.
- One source alone supports at most `PROBABLE`; `VERIFIED` requires independent
  corroboration. Evidence-strength numbers are explicitly heuristic.
- The script auditor evaluates spoken narration, not headings, timecodes, or
  production metadata.
- Final QA requires a verified dossier and fact-check pass, valid run-linked
  artifacts, real media mapped to each required shot, and matching topic
  relevance. Dry-run placeholders never count as coverage.
- `ContentQualityEvaluator` supplies editorial scores; it cannot override a
  failed fact-check or Final QA gate.

Media providers are ordered by engine/data/media_provider_capabilities.json and
filtered by era and media capability. REAL_REQUIRED excludes providers
classified as stock discovery. Media search can display assets with unknown
rights as discovery candidates, but automatic downloads require an explicit
reusable rights classification. sources.json records the license statement and
URL, rights status, retrieval query, provider capabilities, score breakdown,
and selection reason.

The default media adapters are Wikimedia Commons, Internet Archive, Library of
Congress, Openverse, DPLA, Europeana, NASA Images, and DVIDS; Pexafy is an
optional stock adapter. The RSS registry is committed and labels every feed as
discovery-only. RSSHub is self-hosted and opt-in. Openverse and NASA are keyless;
DPLA, Europeana, and DVIDS are inactive without their optional API keys.

PubMed and Europe PMC are available through `DossierGenerator`. Their
bibliographic records and abstracts go into `research_intelligence` as
`DISCOVERY_ONLY`, with exact quotes empty and full text clearly marked as not
fetched. RSS escalation queries call those structured providers as well as the
web search path; search snippets remain leads and do not back factual claims.
Repeated normalized news headlines share a conservative lineage key when
claims are evaluated, while event clusters expose outlet count, estimated
lineage diversity, locations, dates, and headline conflicts.

`visual_verification.py` defines an injectable interface for a shortlist of at
most five fact-specific results. It is only called for `REAL_REQUIRED` and
entity-specific `REAL_PREFERRED` requests. No vision endpoint is configured;
the default records `VISUAL_UNKNOWN`, and only an injected verifier can report
`VISUALLY_CONSISTENT` or `VISUAL_MISMATCH`. Future visuals carry explicit
forecast/research-backed/projection/concept/speculative/generated intent and a
flag that the image is illustrative rather than evidence of a future event.

## CapCut

`capcut_engine.py` is the single native draft generator. `capcut_validator.py`
is the structural validator. `VALIDATED` records a deterministic file/schema
check; `APP_VERIFIED` requires an explicit record that CapCut Desktop opened,
the timeline was checked, and the project was saved. Installation or
registration alone does not prove application-level verification.

## Removed duplicate paths

The legacy `VideoPipeline`, raw-footage auto-edit/SmartCut path, separate
workflow executor/registry/state store, and faster-whisper subtitle script
were removed. The supported production entry point is `nugi_content_create`.
