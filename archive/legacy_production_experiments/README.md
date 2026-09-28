# Archive: Legacy Production Experiments & One-Off Media Scripts

This directory preserves historical, one-off scripts originally written to test batch asset retrieval and microbeat generation for specific video narratives (`narasi-01` through `narasi-15`):

- `fetch_pexafy_assets.py` (Part 1 asset fetcher with hardcoded narasi plans)
- `fetch_pexafy_assets_part2.py` (Part 2 asset fetcher with hardcoded narasi plans)
- `generate_all_microbeats.py` (Microbeat generator with hardcoded narrative scenes)
- `generate_all_microbeats_part2.py`
- `generate_all_microbeats_part3.py`
- `generate_all_microbeats_part4.py`
- `generate_all_microbeats_part5.py`
- `expand_narasi_microbeats.py`

### Why They Were Archived
1. **Hardcoded Narrative Specifics**: These scripts contained fixed narrative lists and scene cues rather than generic, reusable media retrieval logic.
2. **Duplicate MCP Protocol Logic**: Each script reimplemented raw HTTP JSON-RPC initialization and calls to the Pexafy MCP endpoint.
3. **Replaced by Front-Door MediaFinder**: Media retrieval is now unified into `engine/pipeline/media_finder.py` (`MediaFinder`) which routes requests across Pexafy, Wikimedia Commons, and Internet Archive based on era, style, and media type.

### Canonical Replacements
- Python: `from engine.pipeline.media_finder import MediaFinder; finder = MediaFinder()`
- CLI: `python -m engine.pipeline.engine_cli media-find --query "..." --media photo|video|any --era historical|present|future|auto --style formal|documentary|auto`
