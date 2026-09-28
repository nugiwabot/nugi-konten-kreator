# Skill: GENERATE-SCRIPT v3 (Story-Type-Driven Script Generation)

## 1. Deskripsi & Tujuan
Mengubah ide atau Master Research Dossier menjadi naskah video orisinal yang terdengar 100% seperti manusia berbicara langsung: jujur, tenang, tajam, reflektif, membumi, dan bebas dari jargon robotik AI.

⚠️ **PRINSIP DASAR v3:**
- **Story Type adalah Source of Truth:** Struktur naskah ditentukan secara dinamis oleh kombinasi **Story Type** dan **Narrative Device**.
- **Contradiction bersifat OPSIONAL:** Tahap atau perangkat kontradiksi HANYA digunakan jika story type yang dipilih secara natural adalah `contradiction`. Sembilan story type lainnya (origin, transformation, hidden_system, human_dilemma, second_order, place, evolution, future, reframe) **TIDAK MEMAKSAKAN** tahap kontradiksi.
- **Human–Place Anchor:** Properti adalah salah satu benang merah penting di dalam domain PLACE, tetapi **BUKAN** syarat wajib di setiap naskah.

Skill ini mendukung **DUA MODE PRODUKSI**:
1. **SHORT FORM (60–90 Detik):** Untuk YouTube Shorts, TikTok, dan Instagram Reels.
2. **LONG FORM (6–12 Menit):** Untuk YouTube Video Esai Utama (Master Content yang menjadi sumber turunan).

---

## 2. Input Kontrak
```yaml
content_idea: object / string (Wajib: metadata ide dari generate-ideas v3 atau topik terpilih)
story_type: string (origin | transformation | hidden_system | contradiction | human_dilemma | second_order | place | evolution | future | reframe)
narrative_device: string (mystery_reveal | before_after | expose_mechanism | contradiction | trade_off | cascade_effect | spatial_mystery | timeline_progression | projection | assumption_challenge)
format_mode: short | long | master_plus_shorts (default: short)
platform: string (opsional: "YouTube Long-Form" | "YouTube Shorts / TikTok / Reels")
duration_target: string (opsional: "60-90 detik" untuk short, "6-12 menit" untuk long)
tone: string (default: "Conversational, tajam, membumi, reflektif, tenang, non-sales")
```

---

## 3. Struktur Dinamis Berdasarkan Story Type (Long Form 6–12 Menit)

Struktur babak video esai utama mengikuti alur kausalitas alami dari masing-masing dari 10 Story Types:

1. **ORIGIN** (*mystery_reveal*)
   `Observation` → `Question` → `Historical Context` → `Turning Point` → `Causal Chain` → `Revelation` → `Reflection`
2. **TRANSFORMATION** (*before_after*)
   `Observation` → `Before State` → `Forces of Change` → `Transformation` → `Human Consequence` → `Revelation` → `Reflection`
3. **HIDDEN_SYSTEM** (*expose_mechanism*)
   `Observation` → `Question` → `Surface` → `Hidden Mechanism` → `Evidence` → `Consequences` → `Revelation` → `Reflection`
4. **CONTRADICTION** (*contradiction*) — *Satu-satunya tipe dengan tahap kontradiksi eksplisit*
   `Assumption` → `Question` → `Reality` → `Why the Gap Exists` → `Evidence` → `Revelation` → `Reflection`
5. **HUMAN_DILEMMA** (*trade_off*)
   `Situation` → `Choice A` → `Choice B` → `Trade-off` → `Systemic Cause` → `Human Consequence` → `Revelation` → `Reflection`
6. **SECOND_ORDER** (*cascade_effect*)
   `Initial Change` → `First-Order Effect` → `Question` → `Second-Order Effect` → `Evidence` → `Revelation` → `Reflection`
7. **PLACE** (*spatial_mystery*)
   `Observation of Place` → `Question` → `Spatial Context` → `Historical/Structural Cause` → `Evidence` → `Revelation` → `Reflection`
8. **EVOLUTION** (*timeline_progression*)
   `Present State` → `Earlier State` → `Timeline` → `Forces of Change` → `Human Consequence` → `Revelation` → `Reflection`
9. **FUTURE** (*projection*)
   `Current Condition` → `Emerging Change` → `Scenario` → `Second-Order Consequences` → `Evidence/Assumptions` → `Revelation` → `Reflection`
10. **REFRAME** (*assumption_challenge*)
    `Common Assumption` → `Question` → `Evidence` → `Alternative Interpretation` → `Deeper WHY` → `Revelation` → `Reflection`

---

## 4. Struktur Dinamis Berdasarkan Story Type (Short Form 60–90 Detik)

Dirancang untuk retensi tinggi dan memantik perenungan cepat tanpa forced CTA:

- **ORIGIN:** `HOOK (Observation)` → `QUESTION` → `HISTORICAL CONTEXT` → `TURNING POINT` → `REVELATION` → `REFLECTION`
- **TRANSFORMATION:** `HOOK (After State)` → `BEFORE STATE` → `FORCES OF CHANGE` → `TRANSFORMATION` → `REVELATION` → `REFLECTION`
- **HIDDEN_SYSTEM:** `HOOK (Surface)` → `QUESTION` → `HIDDEN MECHANISM` → `CONSEQUENCES` → `REVELATION` → `REFLECTION`
- **CONTRADICTION:** `HOOK (Assumption)` → `CONTRADICTION (Reality)` → `WHY GAP EXISTS` → `REVELATION` → `REFLECTION`
- **HUMAN_DILEMMA:** `HOOK (Situation)` → `TRADE-OFF` → `SYSTEMIC CAUSE` → `REVELATION` → `REFLECTION`
- **SECOND_ORDER:** `HOOK (Initial Change)` → `FIRST-ORDER EFFECT` → `SECOND-ORDER EFFECT` → `REVELATION` → `REFLECTION`
- **PLACE:** `HOOK (Observation of Place)` → `QUESTION` → `SPATIAL CONTEXT / CAUSE` → `REVELATION` → `REFLECTION`
- **EVOLUTION:** `HOOK (Present State)` → `TIMELINE` → `FORCES OF CHANGE` → `REVELATION` → `REFLECTION`
- **FUTURE:** `HOOK (Current Condition)` → `SCENARIO` → `SECOND-ORDER CONSEQUENCE` → `REVELATION` → `REFLECTION`
- **REFRAME:** `HOOK (Common Assumption)` → `ALTERNATIVE INTERPRETATION` → `DEEPER WHY` → `REVELATION` → `REFLECTION`

---

## 5. Format Output Script Standar

```markdown
# NASKAH KONTEN NUGI: [Judul Naskah]
**Format:** [SHORT-FORM (60–90s) / LONG-FORM (6–12m)] | **Story Type:** [origin | hidden_system | ...] | **Narrative Device:** [...]

---

### METADATA EDITORIAL & EVIDENCE
- **Primary Domain:** [property | city | ai | work | human | history | ...]
- **Human–Place Anchor:** [Koneksi ke tempat/cara hidup manusia; benang merah properti jika relevan]
- **Rujukan Sumber (Evidence Base):** [Nama institusi & rujukan resmi Tier 1–5]
- **Target Emosi Audiens:** [Rasa ingin tahu mendalam, validasi keresahan, ketenangan reflektif]

---

### NASKAH TELEPROMPTER / VOICE-OVER
*(Catatan: Babak di bawah mengikuti alur dinamis sesuai Story Type yang dipilih di Section 3/4)*

**[STAGE 1: PEMBUKA SESUAI STORY TYPE]**
[Teks kalimat pembuka]

**[STAGE 2: EKSPLORASI / KONTEKS]**
[Teks eksplorasi fakta dan realitas lapangan]

**[STAGE 3: MEKANISME / PERUBAHAN / PENYEBAB]**
[Teks bedah struktural atau kausalitas]

**[STAGE 4: THE REVELATION]**
[Teks epifani pencerahan sudut pandang baru]

**[STAGE 5: REFLECTION / OPEN QUESTION]**
[Teks pertanyaan reflektif penutup yang tenang tanpa paksaan]

---

### ARAHAN VISUAL & SCENE REQUIREMENTS
| Scene | Fungsi Narasi | Subjek Visual | Rekomendasi Media | Sumber / Lisensi |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Opening Visual | Suasana kota / ruang tinggal | Video cinematic / arsip | Wikimedia / Internet Archive / Pexels |
| 2 | Data / Causal Context | Infografis data BPS / peta sejarah | Grafik animasi / dokumen | Data resmi / arsip publik |

---

### QUALITY CHECK PRE-FLIGHT
- [x] Lolos Human–Place Anchor Test (terbukti memiliki hubungan ke cara/tempat hidup manusia; properti adalah thread opsional).
- [x] Alur naskah taat pada Story Type & Narrative Device yang dipilih (kontradiksi HANYA hadir bila tipe cerita adalah Contradiction).
- [x] Bahasa 100% percakapan manusiawi (tidak kaku, tidak ada kata klise AI, tidak bernada sales/promosi).
- [x] Zero Forced-CTA (tidak ada *"jangan lupa follow"* atau *"klik link di bio"*).
- [x] Semua klaim data memiliki rujukan terverifikasi.
```
