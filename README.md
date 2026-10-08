# Nugi Content Creator

Nugi Content Creator is a single-repository, filesystem-backed editorial and
production pipeline for Human × Place content.

## Canonical production path

`nugi_content_create` is the primary MCP entry point. It invokes exactly one
production orchestrator, `ProductionOrchestrator`, and persists each run in
`output/<run>/manifest.json` (`ProductionManifest` is the only production state
source of truth).

```text
USER / GEMINI / ANTIGRAVITY
  -> nugi_content_create
  -> ProductionOrchestrator
  -> PLAN -> QUALIFY -> RESEARCH -> SCRIPT -> FACT_CHECK
     -> VISUAL_PLAN -> MEDIA -> SUBTITLE -> CAPCUT -> FINAL_QA
  -> ProductionManifest + artifacts
```

The legacy workflow MCP tools are retained only as compatibility wrappers over
that same orchestrator and manifest. They do not maintain their own executor,
pipeline, or state store.

## Production truthfulness

- Media status is recorded per planned shot as `REAL_DOWNLOADED`,
  `LOCAL_REUSED`, `PLACEHOLDER`, `MISSING`, or `NOT_REQUIRED`.
- `PLACEHOLDER` is only created in `dry_run=True` and never counts toward
  production B-roll coverage.
- Final QA uses hard artifact gates and shot-to-media status mapping. A missing
  or mismatched manifest, required artifact, fact-check pass, structurally
  valid CapCut draft, or topic-relevant real media assignment blocks
  publishability. Merely downloading a file does not prove shot coverage.
- Fact-check output is reported as `PASS`, `FAIL`, `NEEDS_REVIEW`, or
  `UNKNOWN`; it is never assumed from a default.
- One source alone can support `PROBABLE`, not `VERIFIED`; factual publishability
  requires independent corroboration and a passed script audit.
- `exact_quote` is populated only from retrieved verbatim text. Provider
  metadata and summaries use separate fields.
- Research reports `evidence_strength`, explicitly documented as a heuristic,
  not statistical confidence.
- OpenAlex/Crossref citation counts remain source metadata, not topical data.
  The BPS adapter returns no evidence until live BPS retrieval is implemented.

## CapCut status

The only CapCut generator is `engine/pipeline/capcut_engine.py`; the only
structural validator is `engine/pipeline/capcut_validator.py`.

- `GENERATED`: package files were created.
- `VALIDATED`: deterministic structural validation passed.
- `APP_VERIFIED`: a completed `app_verification.json` records that the draft
  was opened, checked, and saved in CapCut Desktop.
- `INVALID`: structural validation failed.

Installing or registering a draft does not by itself produce `APP_VERIFIED`.

## Verification

Run the Python suite with:

```powershell
python -m pytest -q
```

`dry_run=True` is useful for structural testing only. A non-dry run still
requires real provider/network availability and must be judged from its
generated manifest and `final_qa.json`; the repository does not claim a result
that has not been observed in the current environment. The normal test suite
is offline; the live media-download test is opt-in with
`NUGI_RUN_REAL_E2E=1`.

## Deliberately excluded legacy paths

The duplicate `VideoPipeline`, raw-footage auto-edit/SmartCut path, its
faster-whisper dependency path, and the separate workflow state store have
been removed. No database, agent framework, GPU model, or service layer is
required for the canonical pipeline.
