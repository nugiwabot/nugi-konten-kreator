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

## 2. Perintah Ekstraksi Pertanyaan (`mine` / `question-mine`)

Mengekstraksi dan mengelompokkan pertanyaan dari dataset eksternal opsional (`riset keyword.json`) menggunakan klasterisasi semantik adaptif (atau override manual) dan validasi reranker:

```powershell
# Ekstraksi dengan jalur file default (menggunakan adaptive threshold otomatis)
python -m engine.pipeline.engine_cli mine

# Ekstraksi dari file spesifik dengan override threshold jarak cosine manual
python -m engine.pipeline.engine_cli mine --dataset "output/riset keyword.json" --threshold 0.35 --top-k 10

# Menonaktifkan kalkulasi adaptive threshold (menggunakan fallback default 0.30)
python -m engine.pipeline.engine_cli mine --dataset "output/riset keyword.json" --no-adaptive --force-rebuild
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

---

## 7. Pencarian Aset Visual & Footage (`media-find`)

Pencarian aset foto dan video berkualitas menggunakan modul terpadu `MediaFinder`. Mendukung penyaringan era, gaya visual (*visual style*), jenis media (*photo/video/any*), perutean penyedia otomatis (Pexafy, Wikimedia Commons, Internet Archive), dan pengunduhan batch dengan penyimpanan metadata lisensi/provenance:

```powershell
# Foto formal pekerja kantor modern (Pexafy / Stock photo)
python -m engine.pipeline.engine_cli media-find \
  --query "manusia bekerja di kantor modern" \
  --media photo \
  --era present \
  --style formal \
  --count 8

# Footage sejarah manusia mulai menetap (Wikimedia Commons + Internet Archive)
python -m engine.pipeline.engine_cli media-find \
  --query "manusia mulai menetap pada zaman prasejarah" \
  --media any \
  --era historical \
  --style documentary \
  --count 8

# Visual konseptual masa depan rumah dengan AI
python -m engine.pipeline.engine_cli media-find \
  --query "rumah masa depan dengan AI" \
  --media photo \
  --era future \
  --style conceptual \
  --count 8

# Pencarian sekaligus mengunduh file ke assets/media/ dan mencatat provenance di sources.json
python -m engine.pipeline.engine_cli media-find \
  --query "arsip sejarah revolusi industri di pabrik" \
  --media any \
  --era historical \
  --style archival \
  --count 5 \
  --download \
  --folder "revolusi_industri"
```
