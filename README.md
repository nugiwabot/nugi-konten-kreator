# 🧠 Nugi Content Creator — Editorial Intelligence Engine v2

> *"Nugi membongkar hal-hal yang kelihatannya biasa, tetapi ternyata menentukan cara kita hidup."*

Repositori ini bukan sekadar pembuat naskah otomatis (*script generator*).  
Repositori ini adalah **Editorial Intelligence Engine** untuk membangun personal media Nugi di Indonesia dengan mengubah satu pertanyaan menarik tentang dunia nyata menjadi konten yang:
1. Relevan bagi kehidupan manusia,
2. Memiliki benang merah kausal dengan properti, tanah, kota, atau ruang hidup (*Property/Life Anchor*),
3. Didukung riset empiris dan evidence kredibel (BPS, BI, jurnal, think-tank resmi),
4. Mempunyai sudut pandang penyelidikan mendalam (*WHY Lens* Level 3–5),
5. Terdengar 100% seperti manusia berbicara,
6. Dapat diproduksi berulang kali secara terstruktur,
7. Didistribusikan lintas platform: YouTube Long-Form (Master Story), Shorts, TikTok, dan Instagram Reels.

---

## 🏛️ Brand Architecture & Hierarki Editorial

- **Audience Promise:** *"Nugi membongkar hal-hal yang kelihatannya biasa, tetapi ternyata menentukan cara kita hidup."*
- **Internal Content DNA:** `AI × PROPERTY × HUMAN × WHY` *(DNA internal, bukan headline klise).*
- **Hierarki 5 Tingkat:**
  ```text
  LEVEL 1 — Human Life    : Apa yang sedang berubah dalam kehidupan manusia?
  LEVEL 2 — Anchor        : Properti, rumah, tanah, kota, ruang, pekerjaan, aset fisik.
  LEVEL 3 — Subjects      : Property, Housing, Land, Cities, Urbanization, Economy, Work, AI, History.
  LEVEL 4 — Lens          : WHY (Mengapa terjadi? Mengapa manusia berperilaku demikian?).
  LEVEL 5 — Story         : Observation → Question → Contradiction → Evidence → Deeper Why → Revelation → Reflection.
  ```

---

## 🏠 Definisi Properti & Property Anchor Test

Properti adalah **anchor utama**, namun dengan batasan filosofis dan sosiologis:
- ❌ **BUKAN:** Jualan rumah, promo diskon developer, listing komersial, brosur cicilan KPR, atau review klaster.
- ✅ **ADALAH:** Rumah, tanah fisik terbatas, tempat tinggal, kota, ruang hidup, kepemilikan aset riil, lokasi, mobilitas komuter, dan urbanisasi.

### Uji Wajib: Property / Life Anchor Test
Setiap ide yang masuk engine **WAJIB** menjawab 5 pertanyaan uji:
1. Apakah berhubungan dengan tempat manusia hidup?
2. Apakah berhubungan dengan bagaimana manusia bekerja?
3. Apakah berhubungan dengan kota, rumah, tanah, ruang, aset, atau mobilitas?
4. Apakah menjelaskan perubahan cara manusia hidup?
5. Apakah ada hubungan struktural kausal dengan properti/ruang meskipun tidak disebut di judul?

> **Minimal 1 hubungan kausal yang jelas harus ada.** Jika tidak ada → **REJECT / OUT OF BRAND**.

---

## 📊 Target Portofolio Konten Editorial
```text
┌────────────────────────────────────────────────────────┐
│  40%  PROPERTY & HOUSING                               │
│       Harga rumah, tanah, KPR, housing crisis, lokasi  │
├────────────────────────────────────────────────────────┤
│  25%  CITY, SPACE & ECONOMY                            │
│       Urbanisasi, transportasi, kemacetan, tata ruang  │
├────────────────────────────────────────────────────────┤
│  20%  AI, TECHNOLOGY & WORK                            │
│       Remote work & disrupsi kantor, geografi hunian   │
├────────────────────────────────────────────────────────┤
│  15%  HUMAN, HISTORY & FUTURE                          │
│       Sejarah lahan, psikologi rasa aman, masa depan   │
└────────────────────────────────────────────────────────┘
```

---

## ⚡ Local AI Infrastructure (LAN Deployment)

Engine terintegrasi langsung dengan server model lokal pada jaringan LAN:

```env
# Local / LAN Embedding (LM Studio / OpenAI Compatible)
EMBEDDING_URL=http://192.168.0.114:1234/v1/embeddings
EMBEDDING_MODEL=Qwen3-Embedding-4B-Q4_K_M.gguf
EMBEDDING_REQUIRED=true

# Local / LAN Reranker (BGE-Reranker-v2-m3 / TEI Compatible)
RERANKER_URL=http://192.168.0.114:8080/v1/rerank
RERANKER_REQUIRED=true

# Production Fail-Safe
ALLOW_FALLBACK=false
```

### Retrieval Policy:
1. **Stage 1 (Vector Retrieval):** 15 kandidat terbaik via cosine similarity.
2. **Stage 2 (Precision Reranking):** Top 3–5 chunks paling relevan via BGE-Reranker.
3. **Guardrails:** Deteksi otomatis ketidakcocokan dimensi/model (*dimension mismatch guard*), fail-fast saat produksi, dan fallback SHA-256 deterministik saat pengujian offline.

---

## 🩺 System Health Check (The Doctor Command)

Jalankan satu perintah CLI untuk menguji integritas seluruh subsistem secara nyata:

```powershell
python -m engine.pipeline.engine_cli doctor
```

**Output Standar:**
```text
NUGI CONTENT ENGINE HEALTH

Embedding
[OK] http://192.168.0.114:1234/v1/embeddings

Reranker
[OK] http://192.168.0.114:8080/v1/rerank

Knowledge Store
[OK] 375 chunks

Web Search
[OK]

Media
[OK]

Configuration
[OK]

Editorial Rules
[OK]
```

---

## 🔬 4 Mode Riset (Research Engine v2)

Tidak lagi mengandalkan semata-mata pada berita terkini (*anti news-centric*):
1. **MODE A — EVERGREEN:** Pertanyaan abadi tanpa batas waktu (*"Kenapa harga tanah selalu naik?"*).
2. **MODE B — CURRENT:** Membedah kebijakan, regulasi, atau rilis baru untuk mencari dampak strukturalnya.
3. **MODE C — HISTORICAL:** Melacak asal-usul tata kota, regulasi pertanahan, atau preseden masa lalu.
4. **MODE D — DATA-DRIVEN:** Berangkat dari anomali data empiris (*"Gaji naik 4%, harga rumah naik 18%"*).

---

## 🎯 100-Point Editorial Fit Score

| Dimensi | Bobot | Deskripsi |
| :--- | :---: | :--- |
| **Human Relevance** | **25 Poin** | Relevansi langsung ke dompet, waktu, dan keputusan hidup manusia. |
| **Property / Life Anchor** | **20 Poin** | Kekokohan rantai kausal ke hunian, tanah, atau kota (Min 10/20). |
| **WHY Depth** | **20 Poin** | Kedalaman analisis menembus Level 3–5 WHY. |
| **Evidence Potential** | **15 Poin** | Ketersediaan data empiris resmi / jurnal terverifikasi (Min 8/15). |
| **Novelty** | **10 Poin** | Keunikan sudut pandang (*inversion* dari asumsi umum). |
| **Story Potential** | **10 Poin** | Kekuatan kontradiksi dan daya pikat visual. |
| **TOTAL** | **100 Poin** | **Ambang Lolos: Minimal 75 Poin** |

---

## 🚫 12 Hard Rejection Rules (Aturan Gugur Mutlak)
1. Generic AI tools list (daftar "10 AI gratis")
2. Property listing (unit spesifik, alamat komersial)
3. Sales copy / promosi cicilan / DP
4. Headline rewriting tanpa analisis WHY
5. Fake statistics / angka rekaan
6. Fabricated quotes / kutipan palsu
7. Unsupported claims tanpa logika empiris
8. Forced CTA (*"Follow akun ini"*, *"Ketik MAU"*, *"Klik bio"*)
9. Forced property connection (jembatan kosmetik)
10. AI topic tanpa human consequence
11. Extreme abstraction tanpa contoh membumi
12. No revelation / naskah tanpa epifani pencerah

---

## 🎬 Dual-Mode Script Production
- **SHORT FORM (60–90 Detik):** `HOOK → TENSION → CONTEXT → REVELATION → OPEN QUESTION` (YouTube Shorts, TikTok, Reels).
- **LONG FORM (6–12 Menit):** `COLD OPEN → QUESTION → WHY THIS MATTERS → CONTEXT → EVIDENCE → CONTRADICTION → DEEPER WHY → CASE STUDY → REVELATION → IMPLICATION → REFLECTIVE ENDING` (YouTube Master Story).

---

## 🧪 Menjalankan Pengujian (Testing)

Jalankan test suite lengkap (132 unit test):
```powershell
pytest
```
Semua modul editorial, property bridge, research modes, embedding config, media pipeline, dan quality gate terlindungi oleh unit test otomatis.
