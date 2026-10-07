# 🏗️ System Architecture: Nugi Human–Place Content Intelligence Engine

## 1. Overview & Purpose

**Nugi Content Creator** adalah sistem kecerdasan editorial independen yang dirancang untuk:
1. **Discover questions:** Menemukan pertanyaan riil yang ingin dipahami manusia mengenai kehidupan nyata.
2. **Deep research:** Meriset pertanyaan tersebut menggunakan bukti empiris (data institusional, sejarah, laporan ekonomi).
3. **Map causal relationships:** Mengidentifikasi hubungan sebab-akibat antara manusia (*Human*) dan ruang tempat manusia hidup (*Place*).
4. **Contextualize changes:** Memahami perubahan dalam sejarah, ekonomi, teknologi, AI, kerja, budaya, geografi, kota, perumahan, dan lahan.
5. **Construct causal chains:** Membangun rantai kausal multi-tingkat (bukan sekadar korelasi dangkal).
6. **Distinctive storytelling:** Mengubah riset menjadi narasi khas persona Nugi (tenang, tajam, reflektif, non-sales, bernapas manusia).
7. **Multi-format scripts:** Menghasilkan naskah short-form (Shorts/TikTok/Reels) dan long-form (YouTube video esai).
8. **Visual/media planning:** Menghasilkan spesifikasi visual per micro-beat, query ekspansi aset, dan storyboard.
9. **Learning loop:** Belajar secara berkesinambungan dari performa konten untuk mengasah fit score dan topik masa depan.

---

## 2. Diagram Alur Sistem (System Dataflow)

```mermaid
graph TD
    A[User Golden Prompt / Question Mining] --> B[Executive Producer Contract & Production Plan]
    B --> C[Intent Classifier & Human–Place Engine]
    C --> D[Story Type Engine: 10 Archetypes]
    D --> E[Knowledge Retrieval & LAN Reranker]
    E --> F[Epistemic Research & Dossier Generator (S0–S7)]
    F --> G[Dynamic Script Synthesizer & Causal Reasoning]
    G --> H[4-State Fact Check Audit]
    H --> I[Visual Shot Planning & Micro-Beat Storyboard]
    I --> J[Media Retrieval, Multi-Stage Ranking & Provenance]
    J --> K[Subtitle Generator (SRT)]
    K --> L[Native CapCut Desktop Draft Generator]
    L --> M[Remotion Motion Graphics & Title Cards]
    M --> N[CapCut Desktop Library Auto-Installation]
    N --> O[Final QA Engine & Gatekeeping Report]
```

---

## 3. Komponen Inti (Core Components)

### A. Editorial Intelligence (`engine/editorial/`)
- `taxonomy.py`: Klasifikasi 4 pilar utama (`human`, `place`, `change`, `why`) dan 12 sub-domain.
- `intent_classifier.py`: Pengklasifikasi intensi pencarian (15 kelas: historical, origin, economic, urban, dll.) yang memprioritaskan intensi substantif atas kata tanya generik.
- `human_place_engine.py`: Uji anchor 10 kriteria Human–Place dan deteksi rantai kausal kanonikal.
- `story_type.py`: Klasifikasi ke dalam 10 arketipe narasi beserta seleksi *narrative device* yang alami (kontradiksi bukan syarat wajib).
- `revelation_engine.py`: Penilai kualitas dan generator cetak biru momen epifani dengan penegakan rantai kausal dan penolakan kalimat klise AI.
- `fit_score.py`: Penghitung skor editorial fit 7-dimensi tepat 100 poin (Human Relevance 25, Human–Place Anchor 20, WHY Depth 20, Evidence 15, Story Type Fit 10, Novelty 5, Editorial Coherence 5).
- `quality_gate.py`: 8 gerbang kualitas wajib dan 12 aturan penolakan mutlak (*hard rejections*).
- `script_synthesizer.py`: `DynamicScriptSynthesizer` yang menghasilkan naskah teleprompter berdurasi dinamis (30s–90s) dengan injeksi data empiris dari research dossier.

### B. Ingestion & Retrieval (`engine/ingestion/` & `engine/providers/`)
- `embedding.py`: Abstraksi provider embedding lokal (LM Studio di `http://192.168.0.114:1234/v1/embeddings`) dengan fallback deterministik SHA-256 untuk testing.
- `reranker.py`: Abstraksi provider cross-encoder reranker (BGE-Reranker di `http://192.168.0.114:8080/v1/rerank`).
- `retriever.py`: Two-stage knowledge retriever (vektor kandidat top-k dilanjutkan reranking presisi).
- `crossref_provider.py`: Query metadata jurnal akademis ber-DOI tanpa API key.
- `gdelt_provider.py`: Pemantauan berita global dan analisis peristiwa internasional.
- `search.py`: `ResilientWebResearchProvider` (SearXNG dengan fallback DuckDuckGo).

### C. Video & Timeline Engine (`engine/pipeline/`)
- `timeline_model.py`: Model kanonikal timeline (`TimelineClip`, `SubtitleCue`, `MusicTrack`, `TimelineData`) yang independen dari editor target.
- `capcut_engine.py`: `CapCutDraftGenerator` yang menghasilkan paket native folder CapCut Desktop 9.x/10.x lengkap (`draft_content.json`, `draft_meta_info.json`, `timeline_layout.json`, `attachment_pc_common.json`) dan dapat langsung di-install ke library pengguna (`User Data/Projects/com.lveditor.draft`).
- `capcut_validator.py`: `CapCutValidator` dengan 16 aturan validasi struktural, track ID, timecode, media existence, dan JSON compliance (status: `GENERATED`, `VALIDATED`, `APP_VERIFIED`).
- `remotion_engine.py`: Integrasi komponen React Remotion untuk rendering motion graphics, kinetic typography, dan title cards.
- `video_pipeline.py`: Perencanaan produksi video terpadu (script parsing, visual shot generation, SRT generation, dan CapCut timeline creation).

### D. Autonomous Production Orchestration (`engine/production/`)
- `executive_producer.py`: Merumuskan `production_plan.json` berdasarkan prompt, durasi, gaya, serta menentukan strategi reuse aset.
- `production_manifest.py`: `ProductionManifest` pelacak status tiap stage produksi yang mendukung idempoten dan resume dari stage sebelumnya.
- `final_qa.py`: `FinalQAEngine` penegak gerbang kualitas final (10 dimensi hard gates + soft score) yang menghasilkan `final_qa.json`.
- `production_orchestrator.py`: `ProductionOrchestrator` yang mengeksekusi 12 tahapan produksi end-to-end tanpa intervensi manual.

