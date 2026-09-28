# Skill: GENERATE-CONTENT-IDEAS v2

## 1. Deskripsi & Tujuan
Menghasilkan ide konten editorial yang bernas, orisinal, dan mendalam untuk media personal Nugi. Skill ini menerapkan **Topic Taxonomy**, **Property/Life Anchor Test**, **4 Mode Riset**, **The 8 DNA Matrices**, dan **Editorial Fit Score**.

⚠️ **PRINSIP DASAR:**  
Engine dilarang menghasilkan ide langsung menjadi script tanpa melalui proses riset, penapisan anchor, dan gerbang kualitas.

---

## 2. Input Kontrak (Input Contract)
```yaml
topic: string (opsional, contoh: "Harga Rumah di Bandung", "AI Agents di Kantor", atau kosong untuk ideasi otomatis)
research_mode: auto | evergreen | current | historical | data_driven (default: auto)
number_of_ideas: integer (default: 3, rentang: 3-5)
platform: string (opsional, default: "Master Content / YouTube & Multi-Platform Derivatives")
audience: string (opsional, default: "Profesional muda, keluarga muda, dan pengambil keputusan 24-42 tahun")
```

---

## 3. Pipeline Eksekusi (10 Tahap Wajib)

```text
1. RESEARCH
   Jalankan riset sumber terpercaya sesuai mode (Evergreen, Current, Historical, Data-Driven).
   ↓
2. TOPIC CLASSIFICATION
   Tentukan primary_domain (property, city, economy, ai, technology, work, human, history, future), anchor, dan lens.
   ↓
3. PROPERTY / LIFE ANCHOR TEST
   Uji apakah ide memiliki jembatan kausal ke ruang hidup, kota, tanah, atau hunian. Jika tidak ada → REJECT.
   ↓
4. HUMAN QUESTION FORMULATION
   Rumuskan pertanyaan mendasar yang dirasakan manusia dalam kesehariannya.
   ↓
5. COMMON ASSUMPTION & CONTRADICTION
   Identifikasi asumsi umum masyarakat lalu bongkar kejanggalan atau paradoksnya.
   ↓
6. DEEPER WHY & CAUSAL BRIDGE
   Telusuri penyebab struktural hingga Level 3–5 WHY dan petakan rantai kausal property_connection.
   ↓
7. EDITORIAL ANGLE & CORE REVELATION
   Pilih arketipe sudut pandang dan rumuskan epifani (sudut pandang pencerah baru).
   ↓
8. STORY POSSIBILITY & VISUAL DIRECTION
   Rancang struktur narasi pembuka hingga penutup beserta arahan visualnya.
   ↓
9. EDITORIAL FIT SCORE & QUALITY GATE
   Hitung skor editorial fit (skala 100, min 75) dan validasi terhadap 12 Hard Rejection Rules.
   ↓
10. OUTPUT GENERATION
    Sajikan ide dalam kontrak data standar v2.
```

---

## 4. Format Output Kontrak v2 (Standard Output Contract)

Untuk setiap ide yang dihasilkan, sistem wajib menyajikan metadata lengkap berikut:

```markdown
### IDE #[N]: [TITLE / JUDUL TAJAM & MEMBUKA PIKIRAN]

- **One-Line Premise:** [Satu kalimat ringkas penjelas premis narasi]
- **Primary Domain:** [property | city | economy | ai | technology | work | human | history | future]
- **Anchor:** [housing | land | city | space | work | ownership | mobility]
- **Lens:** [economics | psychology | sociology | history | technology | business | urbanism | philosophy]
- **Research Mode:** [evergreen | current | historical | data_driven]

#### Editorial Core & Causal Bridge
- **Human Question:** [Pertanyaan eksistensial/keseharian yang menggugah nalar]
- **Common Assumption:** [Asumsi populer yang selama ini dipercaya masyarakat]
- **Contradiction:** [Paradoks atau jurang antara asumsi vs realitas data lapangan]
- **Core Revelation:** [Momen epifani / pencerahan sudut pandang baru khas Nugi]
- **Deeper WHY:** [Akar sistemik/psikologis tersembunyi (Level 4–5 WHY)]
- **Property Connection:** [Rantai sebab-akibat kausal yang menghubungkan topik ke ruang/hunian]

#### Resonance & Social Currency
- **Why People Should Care:** [Relevansi langsung terhadap dompet, waktu, atau ketenangan hidup audiens]
- **Shareability Reason:** [Mengapa audiens ingin membagikan konten ini (Social Currency / Practical Value)]
- **Conversation Question:** [Pertanyaan reflektif pemantik diskusi di kolom komentar]

#### Evidence & Storytelling
- **Evidence Needed:** [Data spesifik, survei resmi, atau bukti empiris yang wajib disertakan]
- **Source Candidates:** [Daftar sumber kredibel (BPS, BI, jurnal akademik, jurnalisme terpercaya)]
- **Story Structure:** [Kerangka alur babak cerita dari pembuka hingga refleksi akhir]
- **Visual Direction:** [Arahan scene visual, footage representatif, dan mood estetika]
- **Editorial Risk:** [Potensi salah paham atau bias yang harus dimitigasi secara etis]

#### Scoring & Gate
- **Editorial Fit Score:** [Skor 0-100] (Human Relevance: X/25, Property Anchor: X/20, WHY Depth: X/20, Evidence: X/15, Novelty: X/10, Story: X/10)
- **Quality Gate:** [PASS / REVISE / REJECT]
```
