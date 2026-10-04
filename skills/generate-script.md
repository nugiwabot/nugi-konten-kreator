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

## 4.1 Audience Psychology Layer (MANDATORY PRE-SCRIPT AUDIT)

Sebelum menulis teleprompter, AI **WAJIB** menjalankan audit psikologi audiens berdasarkan:
`knowledge/human-psychology/audience-drivers.md`.

Lapisan ini **tidak menggantikan Story Type, Narrative Device, atau 8-step Story Architecture**. Fungsinya adalah memastikan cerita memiliki alasan psikologis yang kuat untuk diperhatikan dan diingat.

### A. Human Relatability Mapping — MANDATORY

Identifikasi rantai berikut **sebelum menulis naskah**:

```text
HUMAN BASIC NEED
        ↓
HEALTH / WEALTH / RELATIONSHIP
        ↓
KEHIDUPAN SEHARI-HARI
        ↓
EMOSI / KONFLIK
        ↓
WHY
        ↓
REVELATION
```

Uraikan secara eksplisit:

1. **Primary Human Basic Need** — pilih 1 kebutuhan utama yang benar-benar dipertaruhkan.
2. **Secondary Driver** — maksimal 1–2 hanya bila hubungan kausalnya nyata.
3. **Life Lens** — tentukan **HEALTH, WEALTH, atau RELATIONSHIP** yang paling relevan. Gunakan lebih dari satu hanya bila konsekuensinya benar-benar berbeda dan terbukti.
4. **Everyday Life Scene** — sebutkan minimal 1 situasi konkret yang mungkin dialami target audiens. Hindari jawaban teoritis seperti "ini menyentuh autonomy".
5. **Emotional / Conflict Tension** — jelaskan perasaan atau trade-off yang muncul dari situasi nyata tersebut.
6. **Deeper WHY** — telusuri mengapa situasi itu terbentuk, setelah pengalaman manusianya jelas.
7. **Revelation** — rumuskan perubahan cara pandang yang spesifik dan kembali ke kehidupan audiens.
8. **Shareability Reason** — jelaskan alasan natural seseorang mengirimkan cerita ini ke orang lain.

**Aturan inti:**
> **Human Basic Need adalah akar. Health / Wealth / Relationship adalah lensa. Everyday Life adalah bukti relatability. WHY adalah investigasi. Revelation adalah perubahan cara pandang.**

AI **tidak boleh** mengklaim script relatable hanya karena sudah memiliki Human Driver. Harus ada **Everyday Life Scene** yang spesifik.

### B. Relatability & Angle Gate

Sebelum draft, uji dengan kalimat:

> **"Siapa target audiensnya, pada momen apa mereka mengalami ini, kebutuhan apa yang sedang dipertaruhkan, dan apa konsekuensinya pada Health, Wealth, atau Relationship?"**

Jika jawaban belum konkret, **JANGAN langsung menulis script**.

Perbaiki angle sampai rantai ini lengkap:

```text
HUMAN BASIC NEED
→ HEALTH / WEALTH / RELATIONSHIP
→ KEHIDUPAN SEHARI-HARI
→ EMOSI / KONFLIK
→ WHY
→ REVELATION
```

Topik boleh tetap sama; yang harus berubah adalah **sudut pandangnya**.

Red flags:
- Human Driver ada, tetapi tidak ada scene kehidupan nyata.
- Data kuat, tetapi audiens tidak tahu "ini berpengaruh ke hidup saya bagaimana?"
- Hook kuat, tetapi tidak ada konsekuensi manusia.
- Konten hanya terasa viral karena kontroversi.
- Revelation hanya mengulang fakta tanpa mengubah cara pandang.

### C. Ethical Virality Rules

Gunakan konflik dan ketegangan secara bertanggung jawab:
- boleh membongkar asumsi, trade-off, insentif, desain sistem, atau konsekuensi tersembunyi;
- **jangan** menjadikan kelompok manusia tertentu sebagai enemy untuk memicu kemarahan;
- jangan mengarang motif;
- jangan memakai fear/rage sebagai substitusi untuk evidence;
- jangan membuat judul lebih ekstrem daripada isi.

Target Nugi:
> **membuat orang berpikir lebih dalam, bukan membuat orang marah secara buta.**

---

## 4.2 Mandatory Draft → Audit → Revision → Re-Audit Loop

Naskah **tidak boleh disebut FINAL pada draft pertama**.

Workflow wajib:

```text
IDE / RESEARCH
↓
PSYCHOLOGICAL AUDIT
↓
STORY TYPE + ANGLE
↓
DRAFT SCRIPT
↓
SELF-AUDIT
↓
TARGETED REVISION
↓
RE-AUDIT
↓
FINAL SCRIPT
```

### Self-Audit Score — 50 Poin

Nilai draft **0–10** untuk masing-masing:

| Dimensi | Pertanyaan |
| :--- | :--- |
| **1. Curiosity & Hook** | Apakah ada alasan kuat untuk berhenti dan terus menonton? |
| **2. Human Need & Relatability** | Apakah kebutuhan manusia diterjemahkan menjadi pengalaman yang bisa dikenali audiens? |
| **3. Life Consequence** | Apakah ada dampak konkret pada HEALTH / WEALTH / RELATIONSHIP yang terasa dalam kehidupan sehari-hari? |
| **4. Emotional Tension** | Apakah ada emosi/trade-off yang tumbuh secara natural dari situasi manusia? |
| **5. WHY, Revelation & Shareability** | Apakah penjelasan WHY mengubah cara pandang dan membuat insight layak diceritakan ulang? |

### Ambang

- **40–50:** dapat menuju FINAL setelah evidence, brand, dan language gates lolos.
- **35–39:** WAJIB REVISE lalu audit ulang.
- **<35:** jangan dipoles kosmetik; **perbaiki angle atau struktur** terlebih dahulu.
- **Tidak boleh ada dimensi <7** pada versi FINAL.

### Aturan Revisi

Setelah penilaian:
1. Sebutkan **3 kelemahan terbesar**.
2. Prioritaskan perbaikan **relatability** bila Human Need, Life Consequence, atau Everyday Life Scene lemah.
3. Revisi **bagian yang lemah**, bukan menulis ulang seluruh script secara otomatis.
4. Pastikan revisi membuat penonton mengenali **situasi hidupnya**, bukan sekadar menambah kata-kata emosional.
5. Nilai ulang dengan rubric yang sama.
6. Hanya setelah ambang terpenuhi, evidence/brand/language gates lolos, dan Relatability Gate = PASS, tandai **FINAL SCRIPT**.

**Jangan memalsukan skor.** Bila script memang belum kuat, statusnya tetap REVISE.

---

## 5. Format Output Script Standar

### 5.1 Metadata + Story

```markdown
# NASKAH KONTEN NUGI: [Judul Naskah]
**Format:** [SHORT-FORM (60–90s) / LONG-FORM (working profile 16–20m)] | **Story Type:** [origin | hidden_system | ...] | **Narrative Device:** [...]

---

### METADATA EDITORIAL & EVIDENCE
- **Primary Domain:** [property | city | ai | work | human | history | ...]
- **Human Psychology Map:** [Human Basic Need → Health/Wealth/Relationship → Everyday Life Scene → Emotion/Conflict → WHY → Revelation]
- **Relatability Sentence:** [Siapa audiens + situasi nyata + kebutuhan yang dipertaruhkan + konsekuensi hidup]
- **Human–Place Anchor:** [Koneksi ke tempat/cara hidup manusia; benang merah properti jika relevan]
- **Rujukan Sumber (Evidence Base):** [Nama institusi & rujukan resmi Tier 1–5]
- **Target Emosi Audiens:** [Curiosity / awe / constructive anxiety / amusement — pilih sesuai cerita, bukan dipaksakan]

---

### NASKAH TELEPROMPTER / VOICE-OVER
*(Catatan: Babak di bawah **harus mengikuti alur dinamis sesuai Story Type & Narrative Device** yang dipilih di Section 3/4. Jumlah stage tidak fixed.)*

**[STORY-TYPE-DRIVEN STAGES]**

Gunakan stage sesuai struktur Story Type yang dipilih. Jangan memaksa semua naskah menjadi lima stage atau menggunakan nama stage yang sama untuk semua tipe cerita.

Contoh:
- HUMAN_DILEMMA → Situation → Choice A → Choice B → Trade-off → Systemic Cause → Human Consequence → Revelation → Reflection
- HIDDEN_SYSTEM → Observation → Question → Surface → Hidden Mechanism → Evidence → Consequences → Revelation → Reflection
- SECOND_ORDER → Initial Change → First-Order Effect → Question → Second-Order Effect → Evidence → Revelation → Reflection

Setiap stage harus memiliki fungsi naratif yang jelas dan dapat memiliki panjang yang berbeda sesuai kebutuhan cerita.

**[REVELATION]**
[Titik epifani utama yang muncul sesuai struktur Story Type.]

**[REFLECTION / OPEN QUESTION]**
[Penutup reflektif yang tenang dan memberi ruang berpikir mandiri.]

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
- [x] **Relatability Gate PASS:** Human Basic Need → Health/Wealth/Relationship → Everyday Life Scene → Emotion/Conflict → WHY → Revelation.
- [x] **Everyday Life Scene konkret:** ada minimal satu momen yang dapat dikenali target audiens; bukan hanya istilah psikologi.
- [x] **Life consequence jelas:** penonton dapat melihat dampaknya terhadap Health, Wealth, Relationship, waktu, uang, energi, privasi, atau kualitas hubungan.
- [x] **Emosi berasal dari situasi:** tidak ada penambahan fear/rage/bahasa emosional hanya untuk retention.
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
