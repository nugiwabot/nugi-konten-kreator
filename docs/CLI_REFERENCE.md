# CLI reference

Run commands from the repository root:

```powershell
python -m engine.pipeline.engine_cli [COMMAND] [OPTIONS]
```

End-to-end production is exposed through the MCP tool `nugi_content_create`,
not through a second CLI pipeline. The CLI provides focused utilities:

## System and research

```powershell
python -m engine.pipeline.engine_cli doctor
python -m engine.pipeline.engine_cli research "Dampak transportasi publik pada komuter Jakarta"
python -m engine.pipeline.engine_cli retrieve "kelangkaan dan rasa takut kehilangan" --top-n 3
python -m engine.pipeline.engine_cli reindex --pages 30
```

`doctor` checks local configuration and available services. `research` performs
runtime web research. `retrieve` queries the local knowledge store and requires
its configured embedding/reranking services unless fallback is enabled.

## Question mining

The `question-mine` command (alias `mine`) reads an explicit JSON or JSONL
dataset:

```powershell
python -m engine.pipeline.engine_cli question-mine `
  --dataset "output/riset-keyword.json" `
  --output "output/question-opportunities.json" `
  --top-k 10 --max-queries 100 --json
```

Other options include `--min-results`, `--threshold`, `--no-adaptive`, and
`--force-rebuild`. `--dataset` is required.

## Media

The `media` command group supports search, download, script extraction, and
provider diagnostics:

```powershell
python -m engine.pipeline.engine_cli media search "Monumen Nasional Jakarta" --count 5 --media photo
python -m engine.pipeline.engine_cli media download "arsip transportasi Jakarta" --count 3 --folder "transportasi"
python -m engine.pipeline.engine_cli media from-script "output/script.md" --folder "script-assets" --count-per-scene 2
python -m engine.pipeline.engine_cli media doctor
```

`media find` (also available as top-level `media-find` / `find-media`) uses
MediaFinder and supports `--media`, `--era`, `--style`, `--visual-requirement`
(`--vr`), `--count`, optional `--download`, `--folder`, and `--output`:

```powershell
python -m engine.pipeline.engine_cli media-find `
  --query "kereta komuter Jakarta" `
  --media photo --era present --style documentary `
  --visual-requirement REAL_REQUIRED --count 5
```

The CLI does not provide the removed `create-video`, `VideoPipeline`, or
auto-edit/CapCut commands. See the [architecture freeze report](ARCHITECTURE_FREEZE_REPORT.md)
for the canonical MCP-to-orchestrator call graph.
