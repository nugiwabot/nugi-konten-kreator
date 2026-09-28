# 🧠 Nugi Content Creator — Human–Place Content Intelligence Engine

> *"Nugi membongkar hal-hal yang kelihatannya biasa, tetapi ternyata menentukan cara kita hidup."*

Repositori ini adalah **NUGI HUMAN–PLACE CONTENT INTELLIGENCE ENGINE** — sebuah sistem editorial mandiri (*standalone*) untuk membangun media pengetahuan dan penceritaan Nugi di Indonesia.

---

## 🎯 Tujuan Repositori (Repository Purpose)

Tugas engine ini **HANYA** untuk:
1. **Discover questions:** Menemukan pertanyaan riil yang ingin dipahami manusia mengenai kehidupan nyata.
2. **Deep research:** Meriset pertanyaan tersebut menggunakan bukti empiris dan data tepercaya.
3. **Map causal relationships:** Mengidentifikasi hubungan kausal antara manusia (*Human*) dan ruang tempat manusia hidup (*Place*).
4. **Understand multi-domain change:** Memahami perubahan dalam sejarah, ekonomi, teknologi, AI, kerja, budaya, geografi, kota, perumahan, dan tanah.
5. **Construct causal chains:** Membangun rantai kausal multi-tingkat (mengapa suatu sistem terbentuk dan dampaknya).
6. **Transform into Nugi storytelling:** Mengubah riset menjadi narasi khas Nugi yang tajam, reflektif, membumi, dan bernapas manusia.
7. **Generate scripts:** Menghasilkan naskah short-form (Shorts/TikTok/Reels) dan long-form (YouTube video esai).
8. **Support visual/media planning:** Menghasilkan spesifikasi visual per micro-beat, storyboard, dan aset produksi.
9. **Learn from performance:** Belajar dari performa konten untuk mengasah fit score dan topik masa depan.

---

## 🏛️ Identitas Editorial: HUMAN × PLACE × CHANGE × WHY

Model editorial utama repositori ini adalah:

$$\mathbf{HUMAN} \times \mathbf{PLACE} \times \mathbf{CHANGE} \times \mathbf{WHY}$$

### Definisi 4 Pilar:
- **HUMAN:** Orang-orang, keluarga, pekerja, komunitas, perilaku (*behavior*), identitas, dan kebutuhan eksistensial manusia.
- **PLACE:** Rumah (*home/house/shelter*), tanah, kota, lingkungan (*neighborhood*), tempat kerja, ruang publik, dan geografi fisik.
- **CHANGE:** Sejarah, ekonomi, teknologi, AI, infrastruktur, migrasi, budaya, iklim, industri, dan kebijakan publik.
- **WHY:** Penalaran kausal (*causal reasoning*), sistem tersembunyi (*hidden systems*), insentif ekonomi, psikologi, dan sebab historis.

> [!IMPORTANT]
> **PROPERTY SEBAGAI THREAD, BUKAN TOPIK WAJIB:**  
> Properti adalah benang merah (*thread/anchor*) penting di dalam ruang lingkup **PLACE**, namun **BUKAN** subjek wajib di setiap cerita. Cerita tentang geografi, tata ruang kota, psikologi tempat tinggal, sejarah kolonial pemukiman, atau masa depan ruang kerja sepenuhnya sah tanpa harus menyebut transaksi properti.

---

## 🧭 Domain Editorial yang Diperbolehkan

- Hunian & shelter (*homes, shelter, housing*)
- Tanah & kepemilikan (*land, ownership, property rights*)
- Kota, urbanisasi & arsitektur (*cities, urbanization, architecture, geography*)
- Hubungan kerja & ruang hidup (*relationship between work and place*)
- Hubungan teknologi & tempat tinggal (*relationship between technology and place*)
- Hubungan ekonomi & ruang hidup (*relationship between economy and living space*)
- Sejarah, migrasi, infrastruktur & transportasi (*history, migration, infrastructure, transportation*)
- Masa depan cara hidup (*future of living, AI impact on spaces*)
- Psikologi, perilaku & budaya manusia (*human psychology, behavior, culture*)

*Domain di atas diperbolehkan hanya ketika berkontribusi untuk memahami kehidupan manusia dan/atau di mana serta bagaimana manusia hidup.*

---

## 🚫 Apa yang BUKAN Tujuan Repositori Ini

Repositori ini **BUKAN**:
- CRM atau automasi penjualan
- WhatsApp lead rotator atau sistem distribusi prospek
- Layanan landing page properti
- Sistem manajemen agensi software
- Portofolio software-house
- Saluran review tools AI generik
- Agregator repositori eksternal

---

## 🛡️ Batasan Repositori & Independensi Penuh

Sistem ini **berdiri sendiri secara otonom (independently runnable)**:
- Tidak ada dependensi kode, modul, runtime, atau API terhadap proyek CRM atau sistem penjualan lain.
- Seluruh sumber kebenaran editorial aktif dibatasi pada direktori:
  `core/`, `research/`, `thinking/`, `skills/`, `knowledge/`, `engine/`, `evaluation/`, `tests/`, `docs/`, dan `output/`.
- Seluruh catatan historis agensi masa lalu telah diarsipkan terpisah di [`archive/legacy_agency_system/`](archive/legacy_agency_system/README.md).

---

## ⚡ Infrastruktur AI Lokal (LAN Deployment)

Sistem ini terhubung langsung ke infrastruktur inferensi lokal:

```env
# Local / LAN Embedding (LM Studio / OpenAI Compatible)
EMBEDDING_URL=http://192.168.0.114:1234/v1/embeddings
EMBEDDING_MODEL=Qwen3-Embedding-4B-Q4_K_M.gguf
EMBEDDING_REQUIRED=true

# Local / LAN Reranker (BGE-Reranker-v2-m3 / TEI Compatible)
RERANKER_URL=http://192.168.0.114:8080/v1/rerank
RERANKER_REQUIRED=true

# Production Fail-Safe (false = strict fail-fast on production)
ALLOW_FALLBACK=false
```

---

## 📊 Dataset Pencarian (`riset keyword.json`)

File dataset pencarian bersifat **opsional, read-only**, dan hanya digunakan sebagai sinyal penemuan pertanyaan (*question mining*) dan pengelompokan semantik. Dataset ini tidak diubah dan tidak menjadi dependensi keras.

---

## 🩺 System Health Check (The Doctor Command)

Uji kesehatan dan kesiapan seluruh komponen engine secara mandiri:

```powershell
python -m engine.pipeline.engine_cli doctor
```

Untuk menjalankan rangkaian pengujian otomatis lengkap (235 tests):

```powershell
pytest
```

---

## 📁 Struktur Direktori Aktif

```text
nugi-konten-kreator/
├── core/            # Nilai brand, positioning, Content DNA, kebijakan editorial
├── research/        # Metodologi riset, mode riset, evaluasi sumber & fakta
├── thinking/        # Mesin sudut pandang, penalaran kausal, dekonstruksi WHY
├── skills/          # Kontrak kerja agentik ide, riset, dan skrip
├── knowledge/       # Korpus pengetahuan psikologi, pengaruh, memori, narasi
├── engine/          # Pipeline Python mandiri (mining, intent, story, retriever, video)
│   ├── editorial/   # Modul klasifikasi editorial (HP engine, story type, revelation)
│   ├── ingestion/   # Indexer korpus dokumen & chunking
│   ├── pipeline/    # Unified CLI, runner riset, media ranker & video specs
│   └── providers/   # LAN embedding & reranker client abstractions
├── evaluation/      # Gerbang kualitas konten & loop pembelajaran
├── docs/            # Dokumentasi arsitektur, playbook editorial, dan panduan CLI
├── tests/           # 235 unit & integration tests
├── output/          # Narasi, storyboard, micro-beats, dan aset visual Nugi
└── archive/         # Arsip historis sistem agensi lama (out-of-scope)
```
