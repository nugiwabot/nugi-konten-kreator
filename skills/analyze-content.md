# Skill: ANALYZE-CONTENT (The Experimentation & Learning Loop)

## 1. Deskripsi & Tujuan
Menganalisis performa video aktual berdasarkan metrik nyata yang diberikan oleh pengguna. Mengubah data dingin menjadi wawasan eksperimen terukur, membedah sinyal kuat dan lemah, serta menyusun hipotesis untuk video berikutnya.

⚠️ **PRINSIP KEJUJURAN ANALISIS:**
- Dilarang membuat kesimpulan mutlak seperti: *"Ini pasti karena hook-nya kurang bagus."*
- Jika data metrik tidak lengkap (misal: hanya ada views tanpa data retensi atau shares), sistem WAJIB menyatakan: **"Belum cukup data untuk menyimpulkan penyebab pastinya."**
- Gunakan bahasa hipotesis ilmiah (*probalistic reasoning*), bukan vonis dogma.

---

## 2. Input Kontrak
```yaml
content_title: string (Wajib: judul atau topik video)
metrics:
  views: integer (opsional)
  avg_watch_time: string (opsional, contoh: "42s")
  retention_rate_3s: string (opsional, contoh: "68%")
  completion_rate: string (opsional, contoh: "22%")
  likes: integer (opsional)
  comments: integer (opsional)
  shares: integer (opsional)
  saves: integer (opsional)
  followers_gained: integer (opsional)
  dm_count: integer (opsional)
```

---

## 3. Matriks Diagnosa Sinyal

| Metrik Menonjol | Sinyal Psikologis Yang Terindikasi |
| :--- | :--- |
| **Tinggi di Shares** | Memberikan *Social Currency* atau *Practical Value* tinggi; penonton merasa keren/peduli saat membagikannya. |
| **Tinggi di Saves** | Dianggap sebagai referensi penting atau panduan berharga yang ingin dipelajari ulang nanti. |
| **Tinggi di Comments** | Berhasil membuka *Conversation*; pertanyaan penutup tajam dan memantik perdebatan hangat. |
| **Drop di 3 Detik Pertama** | Hook gagal mematahkan skema ekspektasi atau terlalu lambat masuk ke inti persoalan. |
| **Drop di Detik ke-20-30** | Ketegangan narasi (*tension*) kendur; penjelasan terlalu berbelit atau masuk ke teori membosankan. |

---

## 4. Output Kontrak

```markdown
# EVALUASI PERFORMA & LEARNING LOOP: [Judul Konten]

### 1. APA YANG SEBENARNYA TERJADI? (What Happened?)
- Ringkasan metrik utama dan perbandingannya dengan baseline wajar.

### 2. SINYAL KUAT (What Signal is Strong?)
- Aspek yang bekerja sangat efektif dan bukti metriknya (misal: rasio Share-to-View tinggi).

### 3. SINYAL LEMAH (What Signal is Weak?)
- Titik kebocoran perhatian audiens (misal: retention drop di babak tengah).

### 4. HIPOTESIS PENJELAS (What Might Explain It?)
- Analisis psikologis berbasis prinsip Cialdini, Berger, atau Heath brothers.
- *(Jika metrik tidak memadai: cantumkan "Belum cukup data untuk menyimpulkan secara definitif").*

### 5. TINDAKAN EKSPERIMEN BERIKUTNYA (What Should We Test Next?)
- 1-2 variabel spesifik yang akan diuji pada konten serupa selanjutnya (misal: memangkas durasi setup, menguji varian Hook Arketipe 2, atau memperjelas analogi konkret).
```
