# Skill: ANALYZE-CONTENT v2 (Learning Loop & Audience Insight)

## 1. Deskripsi & Tujuan
Menganalisis performa konten terpublikasi berdasarkan data aktual di dua tingkat: **Content Level** (retensi, shares, saves, diskusi komentar) dan **Audience Level** (returning viewers, penonton baru, pertumbuhan kepercayaan).

Output skill ini digunakan untuk mengekstraksi wawasan berharga dan memperbarui rekomendasi topik masa depan pada ideation engine tanpa merusak integritas brand (*zero brand drift*).

---

## 2. Input Kontrak
```yaml
content_id: string (opsional, contoh: "NUGI-2026-042")
content_title: string (Wajib: judul konten)
primary_domain: string (property | city | economy | ai | work | human)
anchor: string (housing | land | city | space | work | mobility)
dna_matrix: string (Matrix A–H)
format_mode: short_form | long_form
metrics:
  views: integer (opsional)
  avg_watch_time_seconds: integer (opsional)
  retention_rate_pct: float (opsional)
  completion_rate_pct: float (opsional)
  likes: integer (opsional)
  comments_count: integer (opsional)
  shares_count: integer (opsional)
  saves_count: integer (opsional)
  new_viewers: integer (opsional)
  returning_viewers: integer (opsional)
  new_followers: integer (opsional)
```

---

## 3. Matriks Diagnosa Sinyal Dua Tingkat

```text
┌───────────────────────────────┬────────────────────────────────────────────────────────┐
│ Sinyal Menonjol               │ Makna Perilaku Audiens                                 │
├───────────────────────────────┼────────────────────────────────────────────────────────┤
│ Rasio Shares Tinggi (> 2%)    │ Social Currency tinggi: audiens bangga menyebarkannya. │
│ Rasio Saves Tinggi (> 3%)     │ Deep Value: dianggap referensi penting untuk masa depan│
│ Diskusi Komentar Bernas       │ Open Question bekerja efektif memicu refleksi diri.   │
│ Rasio Returning Viewers > 35% │ Kepercayaan jangka panjang terbentuk (Trust Funnel).   │
│ Drop-off di 5 Detik Awal      │ Hook terlalu lambat atau kurang mematahkan asumsi.     │
│ Drop-off di Babak Tengah      │ Penjelasan data terlalu teknis / kehilangan relevansi. │
└───────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 4. Format Output Laporan Analisis

```markdown
# EVALUASI PERFORMA & LEARNING LOOP v2: [Judul Konten]

### 1. RINGKASAN PERFORMA DUA TINGKAT
- **Level Konten:** [Views, Avg Watch Time, Completion Rate, Shares, Saves]
- **Level Audiens:** [Rasio New vs Returning Viewers, Pertumbuhan Komunitas]

### 2. SINYAL RESONANSI KUAT (Strong Resonance)
- [Pola yang terbukti sangat disukai audiens, misal: jembatan kausal AI ke geografi kantor]

### 3. SINYAL FRIKSI (Friction & Drop Points)
- [Titik di mana audiens kehilangan ketertarikan atau penjelasan terasa berbelit]

### 4. AKAR PENYELIDIKAN PSIKOLOGIS (Viewer Psychology)
- [Mengapa audiens bereaksi demikian? Mengaitkan data dengan dorongan psikologis audiens Nugi]

### 5. REKOMENDASI LOOP IDEASI BERIKUTNYA
- **Topik Lanjutan yang Direkomendasikan:** [1–2 sudut pandang baru yang memperdalam tema ini]
- **Penyesuaian Eksekusi:** [Variabel kreatif yang perlu dioptimalkan: hook, visual, atau kedalaman bukti]
```
