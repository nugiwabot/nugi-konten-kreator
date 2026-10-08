# Performance Director

The Performance Director is a delivery layer for finished Nugi scripts.

## Pipeline

SCRIPT
→ THOUGHT UNITS
→ PITCH
→ PACE
→ EMPHASIS
→ PAUSE
→ DELIVERY INTENTION
→ LEARNING EXPLANATION

A normal teleprompter helps with what to say.
This feature helps with how to say it and why the delivery changes.

## Local CLI

Run from repository root:

python -m engine.performance.performance_director "output/02-script/SCRIPT.md"

Or inline:

python -m engine.performance.performance_director --text "Kenapa kita masih tinggal di kota?"

Outputs:
- script_performance.md
- script_teleprompter.txt
- performance_plan.json

Use --output-dir for a custom output folder.

## MCP

The MCP server exposes:
nugi_performance_director

It accepts a repository-relative script path or inline script text and can save a performance package to output/.

## Design rule

The feature does not rewrite a finished script.
It overlays coaching instructions.

The engine is dependency-free and deterministic, so it can be used without an additional API/model. AI agents can add semantic refinement while keeping the same output contract.

## Learning philosophy

Do not mark every sentence dramatically.

The creator should learn a baseline:
natural conversational delivery → change only when the thought changes.

The long-term goal is to make the cues unnecessary because the patterns become internalized.
