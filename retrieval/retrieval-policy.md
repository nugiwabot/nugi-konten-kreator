# Retrieval Policy & Context Window Governance

## 1. Prinsip Utama: Lean Context Injection
Dilarang memasukkan seluruh basis pengetahuan (*entire knowledge base*) ke dalam prompt AI. Memasukkan terlalu banyak teks acak memicu halusinasi, degradasi perhatian (*attention dilution*), dan memperlambat latensi respon.

Retrieval WAJIB dilakukan secara presisi berbasis topik yang sedang dibahas (*just-in-time contextual retrieval*).

---

## 2. Matriks Kebijakan Pengambilan Pengetahuan (Retrieval Policy Matrix)

| Topik Permintaan Pengguna | Kluster Pengetahuan yang Wajib Diambil | Target Reranked Chunks |
| :--- | :--- | :---: |
| **Kecemasan AI & Karier** | `human-psychology/fear-of-obsolescence.md`, `memorability/emotional-care.md`, `influence/authority.md` | 3 - 4 chunks |
| **Tren Hunian, Tanah & Lokasi** | `human-psychology/shelter-territoriality.md`, `human-psychology/status-belonging.md`, `influence/scarcity.md` | 3 - 4 chunks |
| **Viralitas & Mengapa Orang Berbagi** | `shareability/social-currency.md`, `shareability/emotion-arousal.md`, `shareability/triggers.md` | 4 - 5 chunks |
| **Penyusunan Script & Retensi** | `storytelling/story-engine.md`, `storytelling/hook-engine.md`, `memorability/unexpected-curiosity.md` | 3 - 4 chunks |
| **Kredibilitas Data & Sanggahan** | `influence/authority.md`, `memorability/credible-grounded.md`, `research/fact-checking.md` | 3 - 4 chunks |

---

## 3. Aturan Resolusi Query
1. Sebelum memanggil `retriever.retrieve()`, AI membentuk query semantik yang fokus pada **akar permasalahan psikologis atau naratif**, bukan sekadar mengulang keyword teknis pengguna.
2. Ambil maksimal **15 kandidat di Stage 1**, lalu potong menjadi **3 - 5 hasil akhir di Stage 2 (Rerank)**.
