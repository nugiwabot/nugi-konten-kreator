# 💻 Engine CLI Reference Guide

Antarmuka baris perintah terpadu (*Unified CLI*) menyediakan akses ke seluruh subsistem Nugi Content Creator melalui modul `engine.pipeline.engine_cli`.

Jalankan perintah dari direktori root repositori:

```powershell
python -m engine.pipeline.engine_cli [COMMAND] [OPTIONS]
```

---

## 1. Perintah Pemeriksaan Sistem (`doctor`)

Memeriksa kesehatan seluruh infrastruktur (koneksi server embedding LAN, server reranker LAN, indeks korpus pengetahuan, dan integritas modul editorial):

```powershell
python -m engine.pipeline.engine_cli doctor
```

---

## 2. Perintah Ekstraksi Pertanyaan (`mine`)

Mengekstraksi dan mengelompokkan pertanyaan dari dataset eksternal opsional (`riset keyword.json`):

```powershell
# Ekstraksi dengan jalur file default
python -m engine.pipeline.engine_cli mine

# Ekstraksi dari file spesifik dengan jumlah klaster tertentu
python -m engine.pipeline.engine_cli mine --dataset "output/riset keyword.json" --clusters 10
```

---

## 3. Perintah Evaluasi Ide & Anchor (`evaluate`)

Menguji keselarasan topik terhadap identitas editorial, 10 kriteria Human–Place anchor, intensi, dan skor kelayakan:

```powershell
python -m engine.pipeline.engine_cli evaluate --topic "Kenapa harga tanah di pinggiran kota selalu naik lebih cepat dari kenaikan gaji?"
```

---

## 4. Perintah Riset Epistemik (`research`)

Menjalankan riset berbasis fakta vs klaim pada topik tertentu dengan menyerap korpus pengetahuan lokal dan retrieval dua tahap:

```powershell
python -m engine.pipeline.engine_cli research --query "Dampak remote work dan AI terhadap keterjangkauan rumah di pinggiran kota"
```

---

## 5. Perintah Pembuatan Narasi & Storyboard (`generate`)

Menghasilkan struktur narasi multi-beat (Shorts/TikTok atau Video Esai Panjang) beserta spesifikasi visual shot-by-shot:

```powershell
python -m engine.pipeline.engine_cli generate --topic "Kapan manusia pertama kali menetap dan berhenti nomaden?" --story-type origin --format short
```

---

## 6. Perintah Pipeline Video & Export (`video`)

Menjalankan pipeline pra-produksi video (parsing naskah, alokasi micro-beats, pembuatan subtitle `.srt`, dan ekspor berkas proyek `.kdenlive`):

```powershell
python -m engine.pipeline.engine_cli video --script "output/narasi-01/SCRIPT_AND_STORYBOARD.md" --out-dir "output/narasi-01/video"
```
