# Nugi Research + B-roll Intelligence Gap Analysis

## Audit basis

- Audited main at commit b922991dee19afcf9620c5386dfef3f4f9167143 before feature edits.
- The initial worktree was clean.
- The RSS and capability JSON files exist in this local workspace and load at runtime, but git ls-files engine/data lists only .gitkeep. The broad engine/data/*.json ignore rule excludes both files, so a clean clone receives neither.
- The local feed registry loads six entries; the local capability matrix profiles only Wikimedia, Internet Archive, LOC, and Pexafy.
- MediaFinder defaults include LOC and its output is a valid MediaItem; the canonical orchestrator passes dossier research_intelligence into each per-shot search.
- Existing normal tests cover RSS parsing, LOC mapping/rate cooldown, rights gating, ranking, dossier serialization, and B-roll query forwarding. There are no tests or provider implementations for Openverse, DPLA, Europeana, NASA media, DVIDS, PubMed, or Europe PMC.

## Requirement matrix

| Family | Verified current state | Remaining gap |
|---|---|---|
| Free/open media | Wikimedia, Internet Archive, and LOC are wired into MediaFinder; optional Pexafy is also present. | Openverse, DPLA, Europeana, NASA, and DVIDS adapters are absent. The local capability matrix is not committed; on a clean checkout the empty-matrix fallback preserves constructor order and cannot exclude Pexafy for REAL_REQUIRED. |
| Research discovery | OpenAlex, Crossref, GDELT, web retrieval, and a BPS adapter are present. README explicitly says BPS currently returns no evidence. | PubMed and Europe PMC are absent. Crossref remains metadata, while web snippets stay discovery-only; current-event escalation searches do not yet hand results into appropriate structured research providers. |
| RSS source ecosystem | RSS/Atom parsing, dynamic Google News RSS, custom feed fetching, optional direct/RSSHub adapters, caching, URL safety, clustering, and OPML parsing exist. | The feed registry is ignored/untracked and contains only six feeds. OPML import returns disabled feed objects but is not an import-to-registry workflow. Current seed coverage lacks a wider international, government/disaster, and research-institution mix. |
| News/event intelligence | Headlines cluster by title similarity and source domain; feeds are marked DISCOVERY_ONLY; escalation query strings are generated. | Cluster source counts do not identify syndicated wire lineage; locations/conflicts are often empty; escalation results remain web-search leads and do not trigger targeted scholarly/official retrieval or a source-role-aware evidence pass. |
| Research → B-roll | Dossier intelligence reaches production MediaFinder; its recommended queries are appended when token overlap exists. | Event/entity/location/date fields are not independently assembled into strong query variants. Search depends on up to five prebuilt strings and does not report matched event/location/era comprehensively. |
| Historical/present/future | Existing era detection and archives support historical/present searches. | Capability data is untracked and has four providers; no DPLA/Europeana/open-source current specialist routing. Future content has no explicit forecast/projection/concept/speculative/generated mode. |
| Visual verification | Ranker uses text metadata; there is no visual model endpoint or visual-verification interface. | Add a selective, injectable verifier for a shortlist, with deterministic VISUAL_UNKNOWN fallback and no unsupported entity/location assertions. |
| Rights/provenance | Conservative shared classifier and download gate exist; LOC returns unknown rights; downloader writes query/provider/right status. | Each new provider needs explicit per-asset license URL, rights statement, attribution, and conservative mapping. Matched event/location/era and verification outcome need to reach the media manifest. |
| Rate limits/cache/fallback | RSS has bounded cache/retries and LOC has timeout, throttling, and 429 cooldown; MediaLibrary and ranker cache local assets/embeddings. Provider failures are caught while gathering. | New adapters need shared bounded response handling, search cache, backoff/cooldown, and consistent result limits; there is no shared provider health/availability record. |
| Canonical pipeline/docs/tests | One production orchestrator, MediaFinder, MediaLibrary, CapCut path, and offline suite are present. | README does not describe the RSS/provider matrix or rights/fallback flow. Required per-provider mocked coverage and cross-stage event/historical/future/visual integration tests are missing. |

## Current implementation status

| Family | Status after implementation |
|---|---|
| Free/open media | Wikimedia, Internet Archive, LOC, Openverse, DPLA, Europeana, NASA Images, and DVIDS have bounded adapters and capability profiles. Optional Pexafy remains excluded from `REAL_REQUIRED`. The capability matrix is tracked. |
| Research discovery | PubMed E-utilities and Europe PMC are wired to dossiers and event escalation. Abstracts and records remain `DISCOVERY_ONLY`, are not treated as verbatim quotes, and do not enter claim-support evidence. BPS remains an explicit empty adapter; Semantic Scholar is deferred pending applicable use terms. |
| RSS source ecosystem | Tracked registry seeds Indonesian, international, science, and public-agency feeds. OPML import atomically writes new entries disabled for review. RSSHub remains explicit self-hosted opt-in. |
| News/event intelligence | Event clusters preserve headline/byline lineage estimates, dates, locations, and headline conflicts. Feed and web-search items stay discovery-only; escalation also queries structured scholarly providers. Lineage is estimated from metadata, not proof that outlets share a wire source. |
| Research to B-roll | Dossier queries can incorporate request/topic, events, places, and dates. Candidate output and `sources.json` retain matched context, retrieval query, era, score breakdown, and selection reason. |
| Historical/present/future | Tracked capabilities include specialist catalog routing. Future intent distinguishes forecast, research-backed, projection, concept, speculative, and generated visuals; future search results are explicitly illustrative. |
| Visual verification | Injectable verifier checks at most five ranked results for `REAL_REQUIRED` and entity-specific `REAL_PREFERRED`. Default is `VISUAL_UNKNOWN`; mismatches are removed from final results. No vision endpoint is configured, so pixel verification requires a future integration. |
| Rights/provenance | Adapters preserve item-level rights URLs/statements, attribution, creator, landing/source URLs, and provider rights policy. HTTP(S) license URIs are retained; asset URLs still require HTTPS. Unknown or restrictive rights block downloads. `sources.json` stores matched context, rights, scores, attribution, and visual-review outcome. |
| Rate limits/cache/fallback | Catalog adapters bound JSON responses, cache results, respect retry hints, and cool down on rate limits. MediaFinder adds a query cache and provider cooldown; absent credentials or provider failures leave other providers available. There is no shared provider-health dashboard. |
| Canonical pipeline/docs/tests | Canonical MediaFinder/Dossier paths and docs describe providers and evidence boundaries. Mocked provider, feed, dossier, ranking, downloader-manifest, rights, and verifier regression coverage is in place. Full suite: 403 passed, 1 skipped; Python compile check passed. |

## API feasibility findings

- Openverse: Anonymous search is supported with restricted page/depth limits; API records expose license URL, attribution, source, and landing URL. Implement without a key by default, request one bounded page, and still classify rights from each result. Do not scrape or paginate deeply.
- DPLA: Search API is available without payment but requires a free, emailed API key. Keep it optional and preserve per-record rights/landing metadata.
- Europeana: Search API requires a free registered API key. Keep it optional and map each record's EDM rights URI conservatively; previews are not automatically reusable merely because they are accessible.
- NASA Images and Video Library: Search API supports image/video and does not use the NASA Open APIs key portal. Use per-item metadata and mark third-party/unclear rights unknown; NASA usage rules also restrict endorsement and identifiable-person use in promotions.
- DVIDS: Search API requires an issued access key. Its API terms say media accessible through the API is free for commercial use; keep the provider optional and preserve item credit, source, and rights exceptions.
- PubMed: NCBI E-utilities supports public query access; standard guidance is at most 3 requests/second without an API key. Include tool/email identification when configured and treat abstracts as research discovery text, not verbatim source quotations.
- Europe PMC: Public REST search and open-access metadata/full-text discovery are available. Use bounded requests and keep publication metadata/abstracts distinct from retrieved full text.
- Semantic Scholar: Not a required integration. Its API has a separate dataset license and expanded/commercial usage terms; leave it explicitly optional/deferred unless the applicable use terms are confirmed for deployment.

Official API/rights references checked during the audit:

- Openverse API: https://api.openverse.org/v1/
- DPLA API policies and field reference: https://pro.dp.la/developers/policies and https://pro.dp.la/developers/field-reference
- Europeana free-key and rights documentation: https://pro.europeana.eu/page/get-api and https://pro.europeana.eu/index.php/page/available-rights-statements
- NASA Images API and media guidelines: https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf and https://www.nasa.gov/nasa-brand-center/images-and-media/
- DVIDS Search API and terms: https://api.dvidshub.net/docs/search_api and https://api.dvidshub.net/docs/tos
- NCBI E-utilities policy: https://www.ncbi.nlm.nih.gov/home/about/policies/
- Europe PMC REST API: https://europepmc.org/RestfulWebService
- Semantic Scholar API terms: https://api.semanticscholar.org/license/

The first matrix preserves the pre-implementation audit. The current-status matrix above records the implemented behavior and remaining operational limits.
