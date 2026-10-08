# Skill: PERFORMANCE-DIRECTOR

## Purpose
Turn a finished Nugi script into a Vocal Performance Direction Sheet that teaches the creator how to deliver the script naturally.

This is a delivery layer, not a rewriting layer.

SCRIPT FINAL
→ PERFORMANCE DIRECTOR
→ LEARNING SHEET
→ CLEAN TELEPROMPTER
→ REHEARSE
→ SHOOT

## Activate this skill when the user asks about
- intonasi / vocal variety
- penekanan kata / vocal emphasis
- naik-turun nada / pitch
- cepat-lambat bicara / pace
- pause / jeda
- cara membawakan script
- script dengan panduan di atas teks
- agar terdengar natural dan tidak seperti membaca
- belajar public speaking dari script
- performance direction / vocal coaching

## Non-negotiable
Do not rewrite the user's finished script unless explicitly asked.
Preserve the wording and add a coaching layer.

## Performance dimensions

### 1. Pitch
- ↗ naik tipis — curiosity / open question
- ↘ turun / land — conclusion / certainty
- → conversational — baseline explanation
- ↗↘ naik lalu turun — reveal / contrast

### 2. Pace
- 🐢 lambat — insight / reflection
- ▶ normal — conversational baseline
- ⚡ sedikit cepat — list / momentum
- ↔ normal lalu melambat — key idea landing

### 3. Emphasis
Emphasis is not shouting.
Use small changes in:
- articulation
- tempo
- pitch
- slight volume
- pause before/after the word

Do not emphasize every sentence.

### 4. Pause
Typical coaching ranges:
- 0.25–0.35s = micro break
- 0.5–0.7s = attention / transition
- 0.8–1.2s = reveal / reflection

## Delivery intentions
Use:
- CURIOUS
- CONVERSATIONAL
- REVEAL
- CONTRAST
- REFLECTIVE
- MATTER-OF-FACT
- EMOTIVE
- BUILD

## Learning objective
The sheet must explain:
- what changes
- where it changes
- how strongly
- why it changes

Think in thought units, not punctuation only.

The goal is to help Nugi gradually internalize vocal variety so the creator needs fewer cues over time.

## AI behavior
When semantic context is available:
- questions → CURIOUS
- contrast markers such as "tapi", "padahal", "namun", "justru" → CONTRAST
- reveal markers such as "ternyata", "sebenarnya", "masalahnya" → REVEAL
- reflective endings → REFLECTIVE
- lists → BUILD
- data-heavy lines → MATTER-OF-FACT
- emotional lines → EMOTIVE

The Python engine is the deterministic baseline and formatter.
AI may improve cue selection but should preserve the same role/pitch/pace/output vocabulary.

## Output contract
Create:
1. script_performance.md
   - coaching guidance above each thought unit
2. script_teleprompter.txt
   - clean text for reading
3. performance_plan.json
   - machine-readable cue plan

## Nugi speaking style
Conversational, calm, intelligent, curious, documentary-like.
Never announcer-heavy, salesy, or melodramatic.

Target:
Sound like Nugi is thinking and explaining, not reciting a template.
