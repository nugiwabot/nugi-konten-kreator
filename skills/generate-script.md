# Skill: GENERATE-SCRIPT v3 (Story-Type-Driven Script Generation)

## 1. Deskripsi & Tujuan
Mengubah ide atau Master Research Dossier menjadi naskah video orisinal yang terdengar 100% seperti manusia berbicara langsung: jujur, tenang, tajam, reflektif, membumi, dan bebas dari jargon robotik AI.

⚠️ **PRINSIP DASAR v3:**
- **Story Type adalah Source of Truth:** Struktur naskah ditentukan secara dinamis oleh kombinasi **Story Type** dan **Narrative Device**.
- **Contradiction bersifat OPSIONAL:** Tahap atau perangkat kontradiksi HANYA digunakan jika story type yang dipilih secara natural adalah `contradiction`. Sembilan story type lainnya (origin, transformation, hidden_system, human_dilemma, second_order, place, evolution, future, reframe) **TIDAK MEMAKSAKAN** tahap kontradiksi.
- **Human–Place Anchor:** Properti adalah salah satu benang merah penting di dalam domain PLACE, tetapi **BUKAN** syarat wajib di setiap naskah.
- **YouTube Production Layer:** Untuk video YouTube, format channel dan packaging mengikuti `core/youtube-format.md` sebagai lapisan produksi di atas Story Engine. Lapisan ini **TIDAK** menggantikan Story Type atau Narrative Device.

Skill ini mendukung **DUA MODE PRODUKSI**:
1. **SHORT FORM (60–90 Detik):** Untuk YouTube Shorts, TikTok, dan Instagram Reels.
2. **LONG FORM (working profile saat ini: 16–20 Menit):** Untuk YouTube Video Esai Utama. Durasi adalah target produksi saat ini, **bukan aturan wajib** untuk semua video masa depan.

> **Aturan durasi:** Jangan memperpanjang cerita hanya untuk mencapai angka target. Kekuatan cerita tetap menjadi penentu utama.

---

## 2. Input Kontrak
```yaml
content_idea: object / string (Wajib: metadata ide dari generate-ideas v3 atau topik terpilih)
story_type: string (origin | transformation | hidden_system | contradiction | human_dilemma | second_order | place | evolution | future | reframe)
narrative_device: string (mystery_reveal | before_after | expose_mechanism | contradiction | trade_off | cascade_effect | spatial_mystery | timeline_progression | projection | assumption_challenge)
format_mode: short | long | master_plus_shorts (default: short)
platform: string (opsional: "YouTube Long-Form" | "YouTube Shorts / TikTok / Reels")
duration_target: string (opsional: "60-90 detik" untuk short, "16-20 menit" sebagai working profile long-form saat ini)
tone: string (default: "Conversational, tajam, membumi, reflektif, tenang, non-sales")
youtube_layer: boolean (opsional: menerapkan production layer dari core/youtube-format.md; default untuk YouTube long-form = true)
```

### Aturan YouTube Production Layer

Jika targetnya YouTube Long-Form:

- Story Type tetap menjadi source of truth.
- Terapkan `core/youtube-format.md` sebagai **production wrapper**, bukan sebagai story template universal.
- Channel identity harus singkat dan tidak mengganggu cold open atau cerita.
- Re-hook boleh digunakan bila membantu alur; **jangan** memaksakan interval tetap.
- Chapters dan source/on-screen evidence cues boleh disiapkan di bagian packaging.
- Bedakan **FACT**, **INTERPRETATION**, dan **SCENARIO** bila konteksnya membutuhkan.
- CTA bersifat **opsional dan soft**; tidak boleh menjadi forced CTA.
- Penutup editorial tetap berakhir pada reflection/open question sebelum closing identity dan packaging.
- Jangan membuat atau mengubah struktur folder repository untuk menerapkan format YouTube.

Jika targetnya Short Form, gunakan struktur Short Form pada Section 4 dan gunakan elemen YouTube packaging hanya bila relevan dengan platform.

---

## 3. Struktur Dinamis Berdasarkan Story Type (Long Form)

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

### Catatan struktur YouTube

Untuk YouTube Long-Form, elemen berikut dapat membungkus struktur di atas tanpa mengubahnya:

```
COLD OPEN
↓
CENTRAL QUESTION / PROMISE
↓
MICRO BUMPER
↓
STORY TYPE-DRIVEN NARRATIVE
↓
RE-HOOK (bila berguna)
↓
REVELATION
↓
REFLECTION / OPEN QUESTION
↓
CLOSING IDENTITY
↓
OPTIONAL SOFT CTA
↓
END SCREEN
```

Ini adalah **production wrapper**, bukan pengganti struktur Story Type.

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

### 5.1 Metadata + Story

```markdown
# NASKAH KONTEN NUGI: [Judul Naskah]
**Format:** [SHORT-FORM (60–90s) / LONG-FORM (working profile 16–20m)] | **Story Type:** [origin | hidden_system | ...] | **Narrative Device:** [...]

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
```

### 5.2 YouTube Production Layer (untuk YouTube Long-Form)

Untuk YouTube Long-Form, tambahkan bagian produksi berikut **setelah naskah utama**. Jangan memaksa semua item bila tidak relevan.

```markdown
---

### YOUTUBE PRODUCTION LAYER

#### COLD OPEN
[Versi pembuka singkat yang menciptakan curiosity gap / human tension.]

#### MICRO BUMPER
[Catatan visual/audio singkat; tidak perlu ditulis sebagai dialog panjang.]

#### RE-HOOKS
- [Opsional: titik transisi / kalimat re-anchor]
- [Opsional: titik transisi / kalimat re-anchor]

#### CHAPTER CANDIDATES
| Timestamp | Public Chapter Title |
| :-: | :--- |
| 00:00 | [Judul] |
| ... | ... |

#### SOURCE / ON-SCREEN EVIDENCE CUES
| Cue | Klaim / Fungsi | Visual On-Screen | Source |
| :-: | :--- | :--- | :--- |
| 1 | [Klaim] | [Chart/map/document/etc.] | [Source] |

#### CLOSING IDENTITY
[Penutup channel singkat setelah reflection/open question.]

#### OPTIONAL SOFT CTA
[Opsional. Satu CTA singkat dan relevan; boleh kosong.]

#### END SCREEN
[Video terkait / subscription / next question.]

#### DESCRIPTION PACKAGE
- **Synopsis:** [...]
- **Key Topics:** [...]
- **Primary Sources:** [...]
- **Related Video:** [...]

#### THUMBNAIL CONCEPT
- **Dominant Idea:** [...]
- **Visual Tension:** [...]
- **Text:** [...]
```

### 5.3 Evidence Classification

Bila naskah mengandung klaim yang membutuhkan pembedaan tingkat kepastian, gunakan penanda internal berikut:

```
[FACT]
Apa yang langsung didukung evidence.

[INTERPRETATION]
Penjelasan/sintesis kausal yang dibuat dari evidence.

[SCENARIO]
Kemungkinan atau proyeksi berdasarkan asumsi yang disebutkan.
```

Penanda ini bersifat **editorial/internal** dan tidak harus dibaca oleh narator.

---

## 6. Production Rules

1. **Story Type remains source of truth.**
2. `core/youtube-format.md` adalah source of truth untuk wrapper YouTube.
3. Jangan membuat struktur cerita universal hanya demi memenuhi format YouTube.
4. Cold open harus datang dari inti cerita, bukan dari intro channel generik.
5. Micro bumper harus singkat.
6. Re-hook boleh ada, tetapi tidak memakai interval waktu tetap.
7. Revelation tetap menjadi puncak intelektual.
8. Reflection/open question tetap menjadi penutup editorial.
9. Closing identity datang setelah reflection.
10. CTA tetap opsional dan soft.
11. Chapters harus mencerminkan isi nyata video.
12. Source/on-screen cues diprioritaskan untuk klaim penting, bukan setiap kalimat.
13. FACT, INTERPRETATION, dan SCENARIO tidak boleh dicampur sebagai satu tingkat kepastian.
14. Jangan memaksa recurring phrase di setiap video.
15. Jangan membuat long intro, self-introduction panjang, atau generic YouTube greeting.
16. Jangan memaksa contradiction kecuali Story Type = `CONTRADICTION`.
17. Jangan mengubah Python engine atau repository architecture untuk menerapkan format ini.
18. Output packaging harus berada di script/output layer, bukan menjadi alasan untuk membuat folder baru di repository.

---

## 7. ARAHAN VISUAL & SCENE REQUIREMENTS

| Scene | Fungsi Narasi | Subjek Visual | Rekomendasi Media | Sumber / Lisensi |
| :-: | :--- | :--- | :--- | :--- |
| 1 | Opening Visual | Suasana kota / ruang tinggal | Video cinematic / arsip | Wikimedia / Internet Archive / Pexels |
| 2 | Data / Causal Context | Infografis data BPS / peta sejarah | Grafik animasi / dokumen | Data resmi / arsip publik |

Untuk YouTube Long-Form, scene requirements dapat mengacu pada:

- Cold Open
- Story progression
- Re-hook
- Evidence
- Revelation
- Reflection
- End Screen

Tetap gunakan sistem visual yang sudah ada; jangan membuat pipeline media baru.

---

## 8. QUALITY CHECK PRE-FLIGHT

- [x] Lolos Human–Place Anchor Test (terbukti memiliki hubungan ke cara/tempat hidup manusia; properti adalah thread opsional).
- [x] Alur naskah taat pada Story Type & Narrative Device yang dipilih (kontradiksi HANYA hadir bila tipe cerita adalah Contradiction).
- [x] Bahasa 100% percakapan manusiawi (tidak kaku, tidak ada kata klise AI, tidak bernada sales/promosi).
- [x] Tidak ada forced CTA; soft CTA hanya bila relevan dan opsional.
- [x] Semua klaim data memiliki rujukan terverifikasi.
- [x] Untuk YouTube Long-Form, production wrapper mengikuti `core/youtube-format.md`.
- [x] Cold open berasal dari inti cerita, bukan intro generik.
- [x] Re-hook digunakan hanya bila membantu alur.
- [x] Revelation tetap menjadi puncak intelektual.
- [x] Reflection/open question tetap memberi ruang berpikir mandiri.
- [x] FACT / INTERPRETATION / SCENARIO dibedakan bila relevan.
- [x] Tidak ada perubahan pada Python engine atau repository architecture yang hanya dilakukan demi format YouTube.
