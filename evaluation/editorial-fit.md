# Evaluation: Editorial Fit Score v2

Dokumen ini mendefinisikan sistem penilaian kesesuaian editorial internal (*Internal Editorial Fit Score*) untuk Nugi Editorial Intelligence Engine.

⚠️ **CATATAN FUNDAMENTAL:**  
Skor ini **BUKAN** ramalan algoritma viral media sosial (*viral prediction*).  
Skor ini adalah **penjaga integritas editorial (editorial quality gate)** untuk memastikan ide konten layak menyandang nama Nugi.

---

## 1. Bobot & Dimensi Penilaian (100 Poin)

| Dimensi Penilaian | Bobot Maksimal | Deskripsi Evaluasi |
| :--- | :---: | :--- |
| **1. Human Relevance** | **25 Poin** | Seberapa kuat topik menyentuh kehidupan nyata, emosi, kecemasan, atau keputusan besar manusia sehari-hari? Bukan wacana mengawang-awang. |
| **2. Property / Life Anchor** | **20 Poin** | Seberapa kokoh dan alami hubungan kausal topik ke rumah, tanah, kota, ruang kerja, mobilitas, atau aset fisik? |
| **3. WHY Depth** | **20 Poin** | Seberapa jauh analisis menembus lapisan permukaan? Apakah membedah hingga Level 3 (reaksi manusia), Level 4 (sistem struktural), atau Level 5 (psikologi purba)? |
| **4. Evidence Potential** | **15 Poin** | Seberapa siap dan solid ketersediaan data empiris, rujukan institusi resmi (BPS/BI/jurnal), atau catatan sejarah untuk membuktikannya? |
| **5. Novelty / Uniqueness** | **10 Poin** | Apakah sudut pandang yang ditawarkan segar, membalik asumsi umum (*inversion*), dan belum diobral oleh kreator lain? |
| **6. Story Potential** | **10 Poin** | Seberapa dinamis struktur narasi yang dapat dibangun (kejelasan kontradiksi, daya pikat scene visual, dan kekuatan momen epifani)? |
| **TOTAL SKOR MAKSIMAL** | **100 Poin** | **Standar Ambang Kelayakan Editorial** |

---

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
