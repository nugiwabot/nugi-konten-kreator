# Nugi Content Creator — architecture

The repository has one end-to-end production path. Focused research, media,
editorial, and diagnostic tools remain callable independently, but none owns a
second production state machine.

## Canonical call graph

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
       -> DynamicScriptSynthesizer: script.md + story_plan.json
       -> audit_script_with_dossier: fact_check_report.json
       -> VisualRequirementsGenerator: broll_plan.json
       -> MediaFinder: per-shot real search/download and media_manifest.json
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
