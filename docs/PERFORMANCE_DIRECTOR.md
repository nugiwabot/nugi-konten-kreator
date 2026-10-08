# Performance Director

Performance Director is the vocal-delivery layer for finished Nugi scripts.

## Primary output

The default output is now an **inline performance script**, designed to look like the script format used during recording practice.

Example:

**Pernah↗** merasa heran / beberapa tahun lalu / kamu menabung untuk uang muka rumah↘, / tapi saat **GAJIMU↗** kini meningkat / harga rumah incaranmu / justru melesat jauh lebih **TINGGI↘**?

Kita bekerja lebih keras↗ / dan menyisihkan tabungan lebih tekun↘, / namun **GARIS FINIS↗** kepemilikan hunian / seolah terus digeser / menjauh↘.

## Corpus-derived delivery vocabulary

The Performance Director learns its delivery vocabulary from the real Nugi script corpus:

output/short video/TELEPROMPTER_SHORT_21-40.md

The corpus is used only to learn how Nugi naturally frames thoughts, not to inject facts into a new script.

The main delivery families are:

- HOOK — “pernah nggak”, “pernah kepikiran”, “pernah heran”, “pernah perhatikan”, “bayangkan”
- CURIOSITY — “kenapa ya”, “kok”, question openings
- CONTRAST — “padahal”, “tapi”, “namun”, “justru”, “melainkan”, “bukan sekadar”, “bukan cuma”, “bukan karena”
- REVEAL — “ternyata”, “masalahnya”, “jawabannya”, “artinya”, “yang sebenarnya”, “tanpa disadari”, “sadar atau nggak”
- BUILD — “pertama”, “kedua”, “selain itu”, “ditambah lagi”, “di sisi lain”
- REFLECTIVE — “pada akhirnya”, “mungkin”, “hari ini”, “coba tengok”, “itulah”

These patterns affect pitch, pacing and pause placement. This makes the generated script closer to a spoken thought process rather than a marked-up written essay.

## Cue language

- **↗** = pitch naik sedikit.
- **↘** = pitch turun / landing.
- **↗↘** = naik lalu turun untuk reveal atau kontras.
- **↘↗** = perubahan arah yang lembut bila diperlukan.
- **BOLD** = kata yang perlu terasa lebih penting.
- **/** = batas frasa atau thought unit.
- **...** = jeda lebih panjang.
- Cue adalah panduan visual; jangan dibaca keras-keras.

Sistem sengaja tidak menandai setiap kata. Baseline-nya tetap conversational; cue hanya berubah ketika pikiran atau fungsi kalimat berubah.

## Pipeline

SCRIPT
→ THOUGHT UNITS
→ CLAUSES
→ PITCH CUES
→ EMPHASIS
→ PAUSE
→ TELEPROMPTER

## Local CLI

Run from repository root:

python -m engine.performance.performance_director "path/to/SCRIPT.md"

Or inline:

python -m engine.performance.performance_director --text "Kenapa kita masih tinggal di kota?"

Outputs:

- script_performance.md — inline coaching script
- script_teleprompter.txt — clean wording without cues
- performance_plan.json — structured cue metadata

## MCP

The MCP server exposes:

nugi_performance_director

After a finished script, ask the agent to use Performance Director. The returned script_performance field is the inline visual format.

Recommended instruction:

Gunakan Performance Director untuk script ini. Fokus hanya pada script dengan cue intonasi inline seperti ↗, ↘, bold emphasis, slash untuk frasa, dan ... untuk pause. Jangan tambahkan penjelasan.

## Design rules

1. Do not rewrite the finished script.
2. Preserve the original wording.
3. Add visual delivery cues directly beside words or thought boundaries.
4. Do not over-emphasize every sentence.
5. Keep the clean teleprompter output unchanged.
