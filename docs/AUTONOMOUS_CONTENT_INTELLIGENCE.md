# Autonomous Content Intelligence

## Purpose

Nugi Content Creator accepts sparse natural-language instructions and resolves
missing production choices using the existing editorial, research, media and
production contracts.

The canonical production path remains unchanged:

USER -> nugi_content_create -> ProductionOrchestrator -> ProductionManifest.

## Request resolution

The request resolver classifies sparse instructions into intents such as:

- CREATE_CONTENT
- DISCOVER_CONTENT
- RESEARCH_TOPIC
- FACT_CHECK
- BROLL_RESEARCH
- REPURPOSE_CONTENT

Explicit values win. Missing values are filled with safe project defaults.

For example:

"Buat long-form YouTube tentang sejarah KPR"

is resolved to:

- intent: CREATE_CONTENT
- format: longform
- duration: 600 seconds unless the user supplied another duration
- research depth: deep
- fact-check: enabled
- visual research: enabled
- B-roll: enabled
- CapCut production: enabled

## Idea discovery

IdeaDiscoveryEngine is an additive discovery layer. It uses the existing RSS
intelligence service plus:

- Nugi editorial taxonomy
- story type classification
- Human-Place reasoning
- Editorial Fit Score
- existing output topic memory
- evergreen fallback seeds

Feed headlines remain discovery-only. They never become verified evidence
automatically.

The engine returns an opportunity score, editorial fit score, novelty signal,
source provenance, human question, deeper-why direction and selection reasons.

For the MCP discovery path, the top two or three candidates also receive a
bounded evidence pass through the existing DossierGenerator. This pass is a
ranking signal only; final claims still require the normal deep research and
fact-check gates in production.

## Safety rules

1. Discovery never bypasses deep research.
2. RSS and search results remain discovery leads.
3. Production state remains owned by ProductionManifest.
4. Request plans are persisted in the production manifest as metadata.
5. Existing MCP parameters remain supported.
6. Provider failure must degrade gracefully rather than invalidate the entire
   production pipeline.

## Minimal MCP usage

The preferred user experience is:

- "Buat video tentang X"
- "Buat long-form YouTube tentang X"
- "Cari 5 topik terbaik minggu ini"
- "Riset X secara mendalam"
- "Carikan B-roll untuk script ini"

Advanced callers may still provide explicit format, duration, depth, recency,
output folder, B-roll limit and CapCut options.
