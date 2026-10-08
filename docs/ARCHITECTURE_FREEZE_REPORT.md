# Architecture Freeze Report

## Status

Architecture freeze is a code-level constraint: do not add a second production
pipeline, state store, CapCut generator, or orchestration framework without a
demonstrated production requirement. This document does not certify runtime
production readiness, test counts, a real E2E result, or CapCut Desktop review;
those are established only by the current verification artifacts.

## Canonical architecture

```text
nugi_content_create -> mcp.server.content_create -> ProductionOrchestrator
  -> PLAN -> QUALIFY -> RESEARCH -> STORY/SCRIPT -> FACT_CHECK
  -> VISUAL_PLAN -> MEDIA -> SUBTITLE -> CAPCUT -> FINAL_QA -> COMPLETE
  -> ProductionManifest (persisted throughout at output/<run>/manifest.json)
```

- `ProductionOrchestrator` is the only end-to-end production orchestrator.
- `ProductionManifest` is the only state source for a production run.
- `capcut_engine.py` is the only CapCut package generator.
- `capcut_validator.py` is the only CapCut structural validator.
- Compatibility workflow MCP methods delegate to the canonical orchestrator and
  manifest; they do not own execution or state.

## Integrity rules frozen with this architecture

1. Per-shot media provenance uses `REAL_DOWNLOADED`, `LOCAL_REUSED`,
   `PLACEHOLDER`, `MISSING`, or `NOT_REQUIRED`. Only real/local files with
   provenance and topic-relevant metadata count as B-roll coverage; a file's
   presence alone is not enough.
2. A missing/irrelevant required shot, invalid manifest lineage, failed
   research/fact gate, missing artifact, or failed structural CapCut validation
   is a Final QA hard blocker.
3. `VALIDATED` is not `APP_VERIFIED`. Desktop verification requires an explicit
   `app_verification.json` record of opening, checking, and saving the draft.
4. Fact-check status derives from the report (`PASS`, `FAIL`, `NEEDS_REVIEW`,
   `UNKNOWN`); no default pass is allowed. A single source is not independent
   corroboration and cannot make a claim `VERIFIED`.
5. The fact checker reads spoken narration only. Headings, timecodes, and
   production metadata are not factual claims.
6. `exact_quote` is verbatim retrieved text only. Metadata, snippets, and
   generated summaries are separate fields. Citation counts are not topical
   statistics.
7. `evidence_strength` is a documented heuristic rather than statistical
   confidence. Editorial scoring cannot override failed hard gates.

## Removed duplicate paths

- Legacy `VideoPipeline`.
- Raw-footage automatic A-roll/auto-edit CapCut engine and its MCP surface.
- Separate workflow executor, registry, and `.workflow_runs` state store.
- Legacy faster-whisper subtitle/auto-edit script path.

## Verification boundary

A dry run can validate artifacts and package structure but intentionally uses
placeholders, so it cannot prove real media coverage. A real non-dry run must
be recorded from the actual generated `manifest.json`, `media_manifest.json`,
`final_qa.json`, and CapCut validation report. If CapCut Desktop is unavailable,
the highest honest CapCut status is `VALIDATED`.
