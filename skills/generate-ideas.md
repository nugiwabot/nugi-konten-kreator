# Skill: GENERATE-CONTENT-IDEAS v3 (HUMAN × PLACE × CHANGE × WHY × RELATABILITY)

## 1. Deskripsi & Tujuan
Menghasilkan ide konten editorial yang bernas, orisinal, dan mendalam untuk media personal Nugi, dengan **relatability manusia sebagai quality gate sebelum ide masuk ke story engine**. Skill ini menerapkan **Topic Taxonomy v3**, **Human–Place Anchor Test** (10 kriteria), **4 Mode Riset**, **10 Story Types**, dan **Editorial Fit Score v3**.

⚠️ **PRINSIP DASAR v3:**
- Properti adalah thread penting, BUKAN syarat wajib di setiap cerita.
- CONTRADICTION adalah narrative device opsional, bukan tahap wajib.
- Engine dilarang menghasilkan ide langsung menjadi script tanpa melalui proses riset, penapisan anchor, dan gerbang kualitas.

---

## 2. Input Kontrak (Input Contract)
```yaml
topic: string (opsional, bisa berupa pertanyaan, keyword, fenomena, atau kosong untuk ideasi otomatis)
research_mode: auto | evergreen | current | historical | data_driven (default: auto)
number_of_ideas: integer (default: 3, rentang: 3-5)
platform: string (opsional, default: "Master Content / YouTube & Multi-Platform Derivatives")
audience: string (opsional, default: "Profesional muda, keluarga muda, dan pengambil keputusan 24-42 tahun")
story_type: optional string (origin | transformation | hidden_system | contradiction | human_dilemma | second_order | place | evolution | future | reframe)
```

---

## 3. Pipeline Eksekusi v3 (11 Tahap)

```text
1. RESEARCH
   Jalankan riset sumber terpercaya sesuai mode (Evergreen, Current, Historical, Data-Driven).
   ↓
2. INTENT CLASSIFICATION
   Tentukan intent utama topik (historical, origin, explanatory, psychological, economic, urban, future, dll).
   ↓
3. TOPIC CLASSIFICATION (TAXONOMY)
   Tentukan primary_domain, anchor, lens, dan DNA_matrix.
   ↓
4. HUMAN–PLACE ANCHOR TEST (10 Kriteria)
   Uji apakah ide memiliki koneksi ke 1 dari 10 kriteria Human–Place.
   Jika tidak ada → REJECT. Property adalah salah satu kriteria, bukan satu-satunya.
   ↓
5. HUMAN QUESTION FORMULATION
   Rumuskan pertanyaan mendasar yang dirasakan manusia dalam kesehariannya.
   ↓
6. STORY TYPE SELECTION
   Pilih salah satu dari 10 story types yang paling natural untuk topik ini.
   JANGAN paksa "contradiction" jika topik lebih cocok sebagai "origin" atau "place".
   ↓
7. NARRATIVE DEVICE SELECTION
   Pilih narrative device yang sesuai dengan story type terpilih.
   (contradiction, mystery_reveal, trade_off, cascade_effect, dll.)
   ↓
8. DEEPER WHY & CAUSAL BRIDGE
   Telusuri penyebab struktural hingga Level 3–5 WHY dan petakan rantai kausal Human–Place.
   ↓
9. EDITORIAL ANGLE & CORE REVELATION
   Pilih sudut pandang editorial dan rumuskan REVELATION yang spesifik dan human-connected.
   JANGAN buat revelation yang generik ("teknologi mengubah segalanya").
   ↓
10. EVIDENCE & STORY STRUCTURE
    Rancang kebutuhan riset, struktur narasi, dan arahan visual.
    ↓
11. FIT SCORE v3 & QUALITY GATE
    Hitung skor fit (skala 100, min 75) menggunakan model v3:
    Human Relevance (25) + Human-Place Anchor (20) + WHY Depth (20) +
    Evidence (15) + Story Type Fit (10) + Novelty (5) + Editorial Coherence (5) = 100
    Validasi terhadap 12 Hard Rejection Rules.
```

---

## 3.1 HUMAN RELATABILITY GATE — WAJIB

Sebelum memilih Story Type atau merumuskan WHY, AI wajib memetakan:

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

### Cara menjalankan gate

**1. HUMAN BASIC NEED**
Pilih 1 kebutuhan manusia utama yang benar-benar dipertaruhkan:
Safety, Shelter, Health, Wealth/Resources, Belonging, Status, Autonomy, Family Formation, Meaning, atau Curiosity.

**2. HEALTH / WEALTH / RELATIONSHIP**
Tentukan lensa hidup yang paling nyata:
- HEALTH: tubuh, tidur, energi, kenyamanan, stres, recovery.
- WEALTH: uang, waktu, biaya tersembunyi, aset, opportunity cost.
- RELATIONSHIP: pasangan, anak, keluarga, tetangga, komunitas, privasi/kedekatan.

Jangan memaksakan ketiganya.

**3. KEHIDUPAN SEHARI-HARI**
Tuliskan minimal satu adegan yang target audiens mungkin alami.

Contoh lulus:
> "Pekerja yang setiap pagi berangkat sebelum matahari terbit karena rumah yang mampu dibeli berada jauh dari kantor."

Contoh belum lulus:
> "Topik ini relevan karena menyentuh autonomy dan resources."

**4. EMOSI / KONFLIK**
Tentukan apa yang benar-benar terasa atau dipertaruhkan:
murah vs waktu, aman vs privasi, dekat vs ruang pribadi, nyaman vs biaya, efisien vs kualitas hidup.

**5. WHY**
Setelah pengalaman manusianya jelas, telusuri penyebab:
sejarah, desain, ekonomi, insentif, kebijakan, teknologi, geografi, atau perilaku manusia.

**6. REVELATION**
Rumuskan perubahan cara pandang yang kembali ke kehidupan audiens.

### PASS / REVISE

- **PASS:** semua enam lapisan dapat dijelaskan secara konkret.
- **REVISE:** ada Human Basic Need tetapi Everyday Life belum jelas.
- **REJECT / GANTI ANGLE:** topik hanya menarik karena tren/kontroversi tetapi tidak punya konsekuensi hidup yang nyata.

**Aturan kunci:**

> Human Basic Need = akar.  
> Health / Wealth / Relationship = lensa.  
> Everyday Life = bukti relatability.  
> Emotion / Conflict = gesekan manusia.  
> WHY = investigasi.  
> Revelation = perubahan cara pandang.

## 4. Format Output Kontrak v3 (Standard Output Contract)

```markdown
### IDE #[N]: [TITLE / JUDUL TAJAM & MEMBUKA PIKIRAN]

- **One-Line Premise:** [Satu kalimat ringkas penjelas premis narasi]
- **Primary Domain:** [property | city | economy | ai | technology | work | human | history | future]
- **Anchor:** [housing | land | city | space | work | ownership | mobility]
- **Lens:** [economics | psychology | sociology | history | technology | business | urbanism | philosophy]
- **Research Mode:** [evergreen | current | historical | data_driven]
- **Story Type:** [origin | transformation | hidden_system | contradiction | human_dilemma | second_order | place | evolution | future | reframe]
- **Narrative Device:** [mystery_reveal | before_after | expose_mechanism | contradiction | trade_off | cascade_effect | spatial_mystery | timeline_progression | projection | assumption_challenge]

#### Human Psychology & Relatability
- **Primary Human Basic Need:** [Safety | Shelter | Health | Wealth/Resources | Belonging | Status | Autonomy | Family Formation | Meaning | Curiosity]
- **Secondary Driver:** [Opsional, maksimal 1–2]
- **Life Lens:** [HEALTH | WEALTH | RELATIONSHIP]
- **Everyday Life Scene:** [Adegan/momen nyata yang kemungkinan besar dikenali audiens]
- **Emotional / Conflict Tension:** [Apa yang dirasakan atau dipertaruhkan]
- **Relatability Sentence:** [Siapa audiensnya + momen hidupnya + apa yang dipertaruhkan]
- **Relatability Gate:** [PASS / REVISE]

#### Human–Place Connection
- **Human Question:** [Pertanyaan eksistensial/keseharian yang menggugah nalar]
- **HP Anchor Criteria:** [ID dari 10 kriteria yang terpenuhi: A,B,C,D,E,F,G,H,I,J]
- **HP Anchor Justification:** [Penjelasan singkat mengapa topik ini memenuhi kriteria HP]

#### Editorial Core
- **Common Assumption:** [Asumsi populer yang selama ini dipercaya masyarakat — OPSIONAL jika contradiction]
- **Narrative Device Detail:** [Bagaimana narrative device digunakan dalam cerita ini]
- **Core Revelation:** [Momen epifani / pencerahan sudut pandang baru — HARUS SPESIFIK, bukan klise]
- **Deeper WHY:** [Akar sistemik/psikologis tersembunyi (Level 4–5 WHY)]
- **Causal Chain:** [Rantai sebab-akibat kausal: A → B → C → D]

#### Resonance & Social Currency
- **Why People Should Care:** [Relevansi langsung terhadap dompet, waktu, atau ketenangan hidup audiens]
- **Shareability Reason:** [Mengapa audiens ingin membagikan konten ini]
- **Conversation Question:** [Pertanyaan reflektif pemantik diskusi di kolom komentar]

#### Evidence & Storytelling
- **Evidence Needed:** [Data spesifik, survei resmi, atau bukti empiris yang wajib disertakan]
- **Source Candidates:** [Daftar sumber kredibel (BPS, BI, jurnal akademik, jurnalisme terpercaya)]
- **Story Structure:** [Kerangka alur babak cerita dari pembuka hingga refleksi akhir]
- **Visual Direction:** [Arahan scene visual, footage representatif, dan mood estetika]
- **Editorial Risk:** [Potensi salah paham atau bias yang harus dimitigasi]

#### Scoring & Gate (v3)
- **Editorial Fit Score:** [Total/100]
  - Human Relevance: [X/25 — jangan tinggi bila everyday-life connection tidak konkret]
  - Human–Place Anchor: [X/20]
  - WHY Depth: [X/20]
  - Evidence Potential: [X/15]
  - Story Type Fit: [X/10]
  - Novelty: [X/5]
  - Editorial Coherence: [X/5]
- **Quality Gate:** [APPROVED / REVISE / REJECTED]
```

---

## 5. Contoh Topik yang VALID tanpa keyword "properti" eksplisit

✅ **"Kapan manusia nomaden pertama kali memutuskan untuk menetap?"**
→ Kriteria HP: C (how homes are shaped), J (historical systems)
→ Story Type: ORIGIN

✅ **"Kenapa semua kota besar di Indonesia hampir selalu terbentuk di tepi sungai?"**
→ Kriteria HP: D (how cities are shaped), J (historical systems)
→ Story Type: PLACE / HIDDEN_SYSTEM

✅ **"Kenapa manusia yang tinggal di kota besar justru lebih sering merasa kesepian?"**
→ Kriteria HP: I (psychology and home), D (how cities are shaped)
→ Story Type: CONTRADICTION / HIDDEN_SYSTEM

✅ **"Jika AI membuat semua pekerjaan bisa dilakukan dari rumah, kota mana di Indonesia yang pertama berubah?"**
→ Kriteria HP: H (technology changes living space), F (home-work movement)
→ Story Type: FUTURE / SECOND_ORDER
