# Evaluation: Editorial Fit Score v3

Dokumen ini mendefinisikan sistem penilaian kesesuaian editorial internal (*Internal Editorial Fit Score*) untuk Nugi Editorial Intelligence Engine.

⚠️ **CATATAN FUNDAMENTAL:**  
Skor ini **BUKAN** ramalan algoritma viral media sosial (*viral prediction*).  
Skor ini adalah **penjaga integritas editorial (editorial quality gate)** untuk memastikan ide konten layak menyandang nama Nugi.

---

## 1. Bobot & Dimensi Penilaian (100 Poin)

| Dimensi Penilaian | Bobot Maksimal | Deskripsi Evaluasi |
| :--- | :---: | :--- |
| **1. Human Relevance** | **25 Poin** | Seberapa kuat topik menyentuh kebutuhan manusia **dan** dapat diturunkan menjadi pengalaman kehidupan sehari-hari yang dikenali audiens? Nilai tinggi harus dibuktikan melalui Human Basic Need → Health/Wealth/Relationship → Everyday Life → Emotion/Conflict. |
| **2. Human–Place Anchor** | **20 Poin** | Seberapa kokoh dan alami hubungan kausal topik ke rumah, tanah, kota, ruang kerja, mobilitas, atau aset/ruang fisik tempat manusia hidup? |
| **3. WHY Depth** | **20 Poin** | Seberapa jauh analisis menembus lapisan permukaan menuju penyebab struktural dan/atau psikologis? |
| **4. Evidence Potential** | **15 Poin** | Seberapa siap dan solid ketersediaan data empiris, rujukan institusi resmi, jurnal, atau catatan sejarah untuk membuktikannya? |
| **5. Story Type Fit** | **10 Poin** | Seberapa natural Story Type yang dipilih terhadap fenomena dan causal chain topik? |
| **6. Novelty** | **5 Poin** | Apakah framing/sudut pandangnya segar dan tidak sekadar mengulang penjelasan umum? |
| **7. Editorial Coherence** | **5 Poin** | Apakah human question, anchor, WHY, story type, evidence, dan revelation saling konsisten? |
| **TOTAL SKOR MAKSIMAL** | **100 Poin** | **Standar Ambang Kelayakan Editorial** |

## 2. Ambang Batas Kelayakan (Thresholds & Action Gates)

```text
Skor Total ≥ 75 Poin  ──► [STATUS: APPROVED / SIAP PRODUKSI]
Skor Total 60–74 Poin ──► [STATUS: REVISE / PERBAIKI SUDUT PANDANG]
Skor Total < 60 Poin  ──► [STATUS: REJECTED / DISKUALIFIKASI]
```

### Aturan Khusus Ambang Kritis (Critical Sub-Gates):

1. **Kegagalan Anchor Properti:**
   - Jika nilai **`Property / Life Anchor < 10 / 20`**:  
     → **REJECT / OUT OF BRAND**. Ide harus diperbaiki jembatan kausalnya atau ditolak sepenuhnya, berapa pun tingginya skor dimensi lain.
2. **Kekurangan Bukti Empiris:**
   - Jika nilai **`Evidence Potential < 8 / 15`**:  
     → **HOLD FOR RESEARCH**. Dilarang menulis naskah/script. Jalankan riset sumber primer terlebih dahulu untuk memperkuat bukti data.
3. **Pelanggaran 12 Hard Rejection Rules:**
   - Pelanggaran terhadap salah satu dari 12 aturan penolakan mutlak (misal: AI tools list generik, promo sales rumah, data palsu, forced CTA) akan **langsung membatalkan ide (DISQUALIFIED)** tanpa melihat perolehan angka.


---

## 3. Human Relatability Standard

Human Relevance tidak dinilai hanya dari seberapa penting sebuah topik terdengar.

Untuk nilai Human Relevance yang tinggi, evaluator harus dapat melihat:

```
HUMAN BASIC NEED
→ HEALTH / WEALTH / RELATIONSHIP
→ KEHIDUPAN SEHARI-HARI
→ EMOSI / KONFLIK
```

Panduan nilai Human Relevance:
- 21–25: kebutuhan manusia kuat, situasi sehari-hari sangat konkret, konsekuensi hidup jelas, dan tension natural.
- 16–20: relevansi manusia kuat, tetapi scene atau tension masih perlu dipertajam.
- 10–15: topik menarik, tetapi hubungan dengan pengalaman audiens masih abstrak.
- 0–9: hubungan dengan kebutuhan atau kehidupan manusia sangat lemah.

Relatability Gate:
Jika Everyday Life Scene belum dapat dituliskan sebagai satu adegan konkret, ide BELUM BOLEH APPROVED meskipun total skor melewati 75.

Perbaiki angle terlebih dahulu. Jangan mengakali gate dengan bahasa emosional atau jargon psikologi.
