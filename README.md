# 🧠 Nugi Content Intelligence & Influence Engine

> *"Store the thinking. Fetch the current world at runtime."*

Repositori ini adalah sistem kecerdasan konten (*content intelligence engine*) dan nalar pengaruh jangka panjang untuk personal brand **Nugi**. Repositori ini **BUKAN** tempat menyimpan kumpulan script, bukan database ide statis, bukan kalender konten, dan bukan arsip berita. Repositori ini menyimpan **cara berpikir, framework psikologi pengaruh, algoritma penceritaan, dan protokol evaluasi** sebelum sebuah ide atau naskah diproduksi.

---

## 🎯 Core Identity & Content DNA

- **Core Mission:** *"Nugi membongkar WHY di balik AI, properti, dan perubahan cara manusia hidup."*
- **Content Philosophy:** *"Membuat orang melihat sesuatu yang sebelumnya tidak mereka pikirkan."*
- **Content DNA:** `AI × PROPERTY × HUMAN × WHY`

### Siapa Nugi Sebenarnya:
- **Bukan** guru AI generik yang membagikan list 10 tools AI gratis.
- **Bukan** akun berita atau aggregator headline.
- **Bukan** agen properti yang jualan brosur cicilan atau hard-selling.
- **Bukan** motivator yang menebar optimisme klise tanpa data.
- **Nugi adalah** pengamat kritis yang mempertanyakan hal biasa, mencari akar masalah (*the deeper WHY*), menghubungkan teknologi dengan perilaku manusia nyata, dan membuka perspektif baru melalui percakapan santai, tajam, dan reflektif.

---

## 🏗️ Arsitektur Sistem

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERMANENT KNOWLEDGE (Buku Cialdini, Berger, Heath) + PSYCHOLOGY + RULES     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CONTENT INTELLIGENCE ENGINE                           │
│     (Embedding Vector Search + BGE Reranker + Analytical Thinking Engine)    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌───────────────────────┐                             ┌───────────────────────┐
│  CURRENT WEB RESEARCH │                             │  EPITEMIC SEPARATION  │
│  (DDGS / Web Provider)│                             │  (Fact vs Claim vs    │
│                       │                             │   Opinion/Speculation)│
└───────────┬───────────┘                             └───────────┬───────────┘
            └──────────────────────────┬──────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            THE 9-STAGE REASONING & STORYTELLING ALGORITHM                   │
│ (Observation → Question → Contradiction → Context → Why → Revelation → Loop)│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                RUNTIME OUTPUT: TALKING-HEAD SCRIPT / IDEAS                  │
│                     (Conversational, Anti-AI Fluff)                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            QUALITY GATE CHECKLIST & HEURISTIC INFLUENCE SCORING             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Struktur Direktori Repositori

```text
nugi-konten-kreator/
├── README.md                 # Dokumentasi arsitektur utama
├── .env.example              # Template variabel lingkungan
├── .gitignore                # Pengecualian secrets, cache, dan binary PDF
│
├── core/                     # Fondasi Identitas & Strategi
│   ├── identity.md           # Persona, suara, dan batasan Nugi
│   ├── positioning.md        # Diferensiasi 2x2 kategori unik
│   ├── content-dna.md        # 6 pola persimpangan & 4 lapis WHY
│   ├── audience.md           # Psikologi audiens, keresahan & VOC
│   └── objectives.md         # Funnel pengaruh (Attention -> Trust)
│
├── knowledge/                # Pengetahuan Permanen (Diekstrak dari 3 Buku)
│   ├── influence/            # Cialdini (Reciprocity, Social Proof, Authority, Scarcity, dll.)
│   ├── shareability/         # Berger STEPPS (Social Currency, Triggers, Emotion/Arousal, dll.)
│   ├── memorability/         # Heath SUCCESs (Simple, Unexpected, Concrete, Credible, Stories)
│   ├── human-psychology/     # Status, fear of obsolescence, territoriality
│   └── storytelling/         # Narrative transport & kurva ketegangan
│
├── research/                 # Protokol Riset Runtime
│   ├── news-research.md      # 9 tahap investigasi mendalam melampaui headline
│   ├── source-evaluation.md  # 7-tier hirarki kredibilitas sumber
│   ├── fact-checking.md      # Checklist verifikasi fakta & klaim
│   └── trend-detection.md    # Deteksi sinyal lemah (weak signals)
│
├── thinking/                 # Mesin Penalaran Analitis
│   ├── why-engine.md         # Prosedur investigasi 5-lapis WHY
│   ├── curiosity-engine.md   # Loewenstein information gap theory
│   ├── contradiction-engine.md # 3 tipe kontradiksi kognitif
│   ├── human-insight-engine.md # Kamus konversi teknis ke rasa manusia
│   └── angle-engine.md       # 6 arketipe pembangkit sudut pandang
│
├── storytelling/             # Mesin Penceritaan & Naskah
│   ├── story-engine.md       # Arsitektur narasi 8-tahap
│   ├── hook-engine.md        # 4 arketipe hook 3-detik
│   ├── revelation-engine.md  # Mekanisme penyampaian epifani / AHA-moment
│   ├── open-loop-engine.md   # Retensi open loop & pertanyaan terbuka penutup
│   └── script-engine.md      # Blueprint script talking-head 60-90 detik
│
├── retrieval/                # Spesifikasi Retrieval & Reranker
│   ├── embedding.md          # Konfigurasi embedding lokal (LM Studio)
│   ├── reranking.md          # Two-stage retrieval + BGE reranker
│   └── retrieval-policy.md   # Lean context injection matrix
│
├── skills/                   # Spesifikasi Prompt & Kontrak Skill AI
│   ├── generate-ideas.md     # Kontrak pembuatan ide berbasis riset
│   ├── generate-script.md    # Kontrak pembuatan script conversational
│   ├── generate-hooks.md     # Matriks variasi hook 3-detik
│   ├── research-topic.md     # Riset topik & evaluasi sumber
│   └── analyze-content.md    # Loop eksperimen & pembelajaran performa
│
├── evaluation/               # Gerbang Kualitas & Rubrik
│   ├── content-quality.md    # 14 checklist pre-flight & katalog anti-patterns
│   ├── influence-evaluation.md # 8 dimensi evaluasi pengaruh heuristik
│   ├── storytelling-evaluation.md # Rubrik ritme napas & daya serap narasi
│   └── learning-loop.md      # Metodologi eksperimen konten berkelanjutan
│
├── engine/                   # Engine Python Ringan & CLI
│   ├── config.py             # Parser environment variables
│   ├── providers/            # Abstraksi provider (Embedding, Reranker, Search, Media)
│   ├── ingestion/            # Pipeline ekstraksi PDF lokal & vector indexer
│   └── pipeline/             # Two-stage retriever, research runner, media pipeline, & CLI
│
├── assets/                   # Asset lokal (logo, media download results)
│   ├── logo/
│   ├── narasi_01/
│   └── media/                # Destination folder untuk Media Retrieval Agent downloads
│
└── tests/                    # Test Suite Otomatis (100% Pass)
    ├── test_providers.py     # Pengujian provider & offline fallback
    ├── test_retrieval.py     # Pengujian query semantik & reranking
    ├── test_research.py      # Pengujian klasifikasi tier sumber
    ├── test_skills_and_contracts.py # Pengujian schema output
    └── test_quality_gate.py  # Pengujian deteksi anti-pattern
```

---

## ⚡ Quickstart & Penggunaan CLI

### 1. Prasyarat Lingkungan
Pastikan server lokal berikut aktif (atau sistem otomatis menggunakan mode fallback):
- **Embedding:** LM Studio pada `http://localhost:1234/v1/embeddings` (model: `text-embedding-nomic-embed-text-v1.5`).
- **Reranker:** Reranker server pada `http://127.0.0.1:8080/v1/rerank` (model: `bge-reranker-v2-m3`).

Salin konfigurasi:
```powershell
cp .env.example .env
```

### 2. Menjalankan 2-Stage Knowledge Retrieval
Mencari pengetahuan permanen dari repositori (prinsip pengaruh, penceritaan, dan psikologi) yang paling relevan dengan topik:
```powershell
python -m engine.pipeline.engine_cli retrieve "kenapa orang ragu beli properti" --top-n 3
```

### 3. Menjalankan Runtime Web Research
Melakukan investigasi intelijen dunia nyata terkini lengkap dengan klasifikasi tingkat sumber (Tier 1 - 7):
```powershell
python -m engine.pipeline.engine_cli research "tren perumahan anak muda 2026" --max-results 5
```

### 4. Membangun Ulang Vector Store (Re-indexing)
Mengekstrak kembali buku PDF lokal di folder Downloads dan modul markdown:
```powershell
python -m engine.pipeline.engine_cli reindex --pages 30
```

### 5. 🎬 Media Retrieval Agent — Preview Hasil Pencarian
Mencari media visual dari Wikimedia Commons + Internet Archive tanpa download (preview):
```powershell
# Preview hasil pencarian (tidak ada file yang didownload)
python -m engine.pipeline.engine_cli media search "D-Day 1944 Normandy" --count 10 --type video

# Preview foto bertema emosi
python -m engine.pipeline.engine_cli media search "orang yang merasa sendirian di keramaian" --type image
```

### 6. 📥 Media Retrieval Agent — Download
Cari dan download media langsung ke folder project:
```powershell
# Download 5 footage D-Day ke assets/media/ww2/d-day/
python -m engine.pipeline.engine_cli media download "D-Day 1944 Normandy landing" \
    --count 5 --folder ww2/d-day --type video

# Download foto Albert Einstein
python -m engine.pipeline.engine_cli media download "Albert Einstein portrait 1921" \
    --count 3 --folder people/einstein --type image

# Download dengan batas ukuran file
python -m engine.pipeline.engine_cli media download "WWII archival footage" \
    --count 5 --folder ww2/general --max-size-mb 200
```

### 7. 📄 Media Retrieval Agent — Script to Asset
Ekstrak kebutuhan visual otomatis dari script narasi dan download per scene:
```powershell
python -m engine.pipeline.engine_cli media from-script "assets/narasi_01/narasi.md" \
    --folder narasi-01 --count-per-scene 3
```

### 8. 🩺 Media Retrieval Agent — Health Check
Cek ketersediaan semua layanan (Wikimedia, Internet Archive, Embedding, Reranker):
```powershell
python -m engine.pipeline.engine_cli media doctor
```

### 9. Menjalankan Test Suite
Memverifikasi 103 pengujian unit otomatis:
```powershell
python -m pytest tests/ -v
```

---

## 🛡️ Anti-Patterns: Hal yang Dilarang Keras
- ❌ **Headline Rewriting:** Berita → Ringkasan → Script tanpa ada pembongkaran *The Deeper WHY*.
- ❌ **Fabricated Statistics / Quotes:** Mengarang kutipan tokoh atau angka statistik khayalan.
- ❌ **Rage Bait & Sensationalism:** Memancing amarah buta demi komentar beracun.
- ❌ **Forced CTA:** Memaksa audiens dengan kalimat "Jangan lupa follow", "Ketik MAU di komentar", atau "Klik link di bio".
- ❌ **Generic AI Tone:** Menggunakan frasa robotik seperti *"Di era digital yang serba cepat ini..."* atau *"Menyelami samudera peluang..."*.
