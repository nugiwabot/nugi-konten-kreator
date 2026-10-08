# Stage 11 — Editorial Learning

Setelah Final QA, setiap production run menghasilkan `editorial_learning.json` di folder run dan memperbarui `output/editorial_learning_history.json`. Record menyimpan hasil QA, kategori blocker, status riset/fact-check, dan ringkasan status media. History di-upsert berdasarkan `run_id` agar resume tidak membuat duplikat run yang sama.

## Feedback manusia (opsional)

Setelah menonton draft atau konten yang sudah tayang, buat file `editorial_feedback.json` di folder run. Gunakan hanya angka atau catatan yang benar-benar diamati:

```json
{
  "schema_version": 1,
  "ratings": {
    "hook": 3,
    "clarity": 4,
    "pacing": 3,
    "evidence": 5,
    "visuals": 4,
    "brand_fit": 4
  },
  "audience_metrics": {
    "views": 0,
    "average_view_duration_seconds": 0,
    "retention_rate_pct": 0,
    "click_through_rate_pct": 0
  },
  "editor_notes": "Catatan konkret setelah meninjau video.",
  "audience_observations": "Observasi dari data analitik atau komentar yang benar-benar tersedia."
}
```

Rating menggunakan skala 1–5. Angka `0` di contoh hanyalah placeholder; ganti dengan data nyata atau hapus field metrik yang belum tersedia. Jangan memasukkan angka perkiraan seolah-olah hasil analitik.

## Cara menggunakan hasilnya

1. Buka `editorial_learning.json` untuk memahami hasil run dan tindakan korektif yang disarankan.
2. Setelah review manusia atau publikasi, tambahkan feedback ke `editorial_feedback.json`.
3. Jalankan kembali pipeline pada workspace yang sama agar learning record diperbarui, atau tinjau feedback tersebut pada run berikutnya.
4. Bandingkan history beberapa run sebelum mengubah editorial blueprint, scoring, atau workflow.

## Batasan

- Learning record adalah ringkasan observasi, bukan model prediksi performa konten.
- QA score bukan ukuran kepuasan penonton, retensi, atau konversi.
- Pipeline tidak otomatis mengubah scoring, skrip, atau keputusan publikasi dari feedback ini.
- Persetujuan publikasi tetap keputusan manusia.
