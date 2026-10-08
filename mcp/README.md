# Nugi MCP

`nugi_content_create` is the primary production entry point. It calls the
canonical `ProductionOrchestrator`; each production run is represented only by
`ProductionManifest` at `output/<run>/manifest.json`.

## Production calls

```text
nugi_content_create
  -> ProductionOrchestrator
  -> production_plan.json, research dossier, script, fact-check report,
     broll plan, media manifest, subtitles, CapCut draft, final QA, manifest
```

`recency` is passed to the dossier's web retrieval provider. It is an actual
retrieval input, not an interface-only parameter.

`nugi_workflow_plan`, `nugi_workflow_preflight`, `nugi_workflow_execute`,
`nugi_workflow_status`, and `nugi_workflow_resume` remain solely for backward
compatibility. They are thin wrappers around `ProductionOrchestrator` and
`ProductionManifest`; they have no executor, workflow checkpoint directory, or
duplicate production logic.

## Media and QA semantics

The media manifest maps each planned shot to a status. `REAL_DOWNLOADED` and
`LOCAL_REUSED` count only when the file has provenance and topic-relevant
metadata. `PLACEHOLDER` occurs only for dry runs and `MISSING` blocks real
production publishability. Final QA also requires verified research and a
passed fact-check; editorial scores cannot override those hard gates.

One source alone is not independent corroboration and cannot produce a
`VERIFIED` claim. Citation counts and search snippets are not promoted to
topical statistics or verbatim quotes.

## CapCut semantics

`nugi_content_create` uses the one native CapCut engine and validator.

- `GENERATED` means the package exists.
- `VALIDATED` means structural Python validation passed.
- `APP_VERIFIED` requires a recorded CapCut Desktop open/check/save event.

An installed or registered project is not automatically `APP_VERIFIED`.

## Focused non-production tools

Research, editorial, visual, media, subtitle, repository, and diagnostic tools
may be called independently. They do not represent alternate end-to-end
production pipelines. Raw-footage auto-edit, `VideoPipeline`, and auto-edit
MCP tools were removed with their legacy workflow state path.
