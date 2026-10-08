# Tahap 00 — Audit Baseline Repository

Tanggal audit: 2026-10-09  
Repository: [nugiwabot/nugi-konten-kreator](https://github.com/nugiwabot/nugi-konten-kreator)  
Branch yang diaudit: `main`  
Commit HEAD yang terlihat saat audit: `f07f7c61e8c5bd036cb2b932362cf0ae92f037f2` — `Add SHORT 21-30 scripts in everyday spoken Indonesian`

## 1. Tujuan dan batas audit

Tahap ini memetakan arsitektur, discovery, editorial scoring, tes, dan status verifikasi sebelum perubahan perilaku dilakukan.

Audit dilakukan dengan membaca file dan metadata GitHub. Kode tidak dijalankan di lingkungan lokal pada sesi ini. Karena itu, laporan ini **bukan** pernyataan bahwa seluruh test suite lulus, bahwa produksi berjalan end-to-end, atau bahwa semua perubahan lokal pengguna sudah tersimpan di GitHub.

Tidak ada kode produksi yang diubah pada tahap ini. File audit ini adalah satu-satunya perubahan yang dibuat sebagai catatan baseline.

## 2. Baseline arsitektur yang sudah ada

Dokumentasi repository menetapkan satu jalur produksi kanonis:

`nugi_content_create → ProductionOrchestrator → PLAN → QUALIFY → RESEARCH → SCRIPT → FACT_CHECK → VISUAL_PLAN → MEDIA → SUBTITLE → CAPCUT → FINAL_QA`

Sumber state produksi adalah `ProductionManifest` di `output/<run>/manifest.json`. Workflow MCP lama didokumentasikan sebagai compatibility wrapper yang menggunakan orchestrator dan manifest yang sama.

Komponen yang sudah ada dan perlu dipertahankan kecuali ada bukti kuat sebaliknya:

- `IdeaDiscoveryEngine` untuk discovery topik.
- Taxonomy, story-type classifier, Human–Place reasoning, dan Editorial Fit Score.
- `DossierGenerator` untuk riset dan `audit_script_with_dossier` untuk pemeriksaan klaim.
- `VisualRequirementsGenerator`, `MediaFinder`, provenance media, dan rights gate.
- Subtitle, satu generator CapCut, satu validator CapCut, serta Final QA.
- Tes regresi untuk autonomous intelligence.

**Batas arsitektur:** jangan menambahkan orchestrator, pipeline produksi, state store, atau generator CapCut kedua. Perbaikan berikutnya sebaiknya dilakukan di dalam struktur yang ada.

## 3. File utama yang diperiksa

- [README.md](../README.md)
- [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/ARCHITECTURE_FREEZE_REPORT.md](ARCHITECTURE_FREEZE_REPORT.md)
- [docs/AUTONOMOUS_CONTENT_INTELLIGENCE.md](AUTONOMOUS_CONTENT_INTELLIGENCE.md)
- [engine/editorial/idea_discovery.py](../engine/editorial/idea_discovery.py)
- [engine/editorial/taxonomy.py](../engine/editorial/taxonomy.py)
- [engine/editorial/fit_score.py](../engine/editorial/fit_score.py)
- [engine/editorial/story_type.py](../engine/editorial/story_type.py)
- [engine/editorial/human_place_engine.py](../engine/editorial/human_place_engine.py)
- [tests/test_autonomous_intelligence.py](../tests/test_autonomous_intelligence.py)
- [.github/workflows/autonomous-intelligence.yml](../.github/workflows/autonomous-intelligence.yml)

## 4. Temuan awal

### A. Fondasi editorial sudah ada

Taxonomy sudah mengenal domain seperti property, city, economy, AI, technology, work, human, history, dan future. Human–Place Engine juga secara eksplisit memperluas niche agar properti bukan satu-satunya jalur cerita.

Implikasi: tidak perlu mengganti sistem taxonomy dari nol. Tahap berikutnya perlu mengevaluasi apakah taxonomy dan classifier yang ada cukup untuk membedakan topik yang benar-benar relevan dari topik yang hanya kebetulan berisi kata umum.

### B. Niche fit belum tampak sebagai penilaian kandidat yang independen

Di `engine/editorial/idea_discovery.py`, `_make_candidate()` menghitung Editorial Fit Score melalui `calculate_editorial_fit()`, tetapi mengisi `nugi_fit_score` dengan konstanta `20.0`. Jalur evergreen fallback juga mengisi nilai tetap tersebut.

Implikasi: nilai `nugi_fit_score` saat ini tidak membedakan kecocokan niche antar-kandidat. Editorial Fit Score dan niche alignment tidak boleh dianggap sebagai metrik yang sama tanpa evaluasi tambahan.

### C. Discovery lebih banyak memberi peringkat daripada membuat keputusan editorial eksplisit

Kandidat yang memiliki judul dapat dibentuk menjadi `ContentOpportunity`; hasil akhir diberi status umum `DISCOVERY_ONLY`. Pada kode yang diperiksa, belum tampak keputusan per-kandidat yang eksplisit seperti `QUALIFIED`, `NEEDS_SCOPING`, `ON_HOLD`, atau `REJECTED` berdasarkan hard gate niche dan kesiapan bukti.

Implikasi: tahap perbaikan discovery perlu menetapkan keputusan editorial yang bisa dijelaskan, bukan sekadar mengurutkan skor.

### D. Sebagian sinyal skor bersifat heuristik atau ditetapkan secara umum

Discovery membentuk pertanyaan manusia dan arah deeper-why dari klasifikasi domain, lalu memakai sejumlah nilai heuristik untuk novelty, evidence, visual potential, dan opportunity. Pada jalur kandidat feed, nilai Nugi fit diisi tetap; pada jalur evergreen, nilai opportunity memakai baseline tetap ditambah novelty dan fit.

Implikasi: skor saat ini berguna sebagai sinyal ranking awal, tetapi jangan diperlakukan sebagai penilaian kualitas yang telah dikalibrasi. Perbaikan berikutnya perlu membuat alasan, input, dan batas skor transparan serta menguji contoh yang cocok dan tidak cocok.

### E. Topic memory memiliki cakupan terbatas

Fungsi `_read_existing_content()` membaca file Markdown dari direktori `output`, membatasi pemindaian pada 120 file yang diurutkan, lalu menggunakan judul atau cuplikan isi untuk deduplikasi berbasis kemiripan token.

Implikasi: ini membantu menghindari sebagian duplikasi, tetapi belum tentu merepresentasikan seluruh naskah, topik yang pernah dibuat di luar `output`, atau kemiripan makna yang tidak berbagi banyak kata. Jangan memperluas memory sebelum cakupan dan format data yang sudah ada dipetakan.

### F. Batas bukti sudah terdokumentasi dengan baik

Dokumentasi menyatakan feed RSS dan hasil pencarian adalah discovery leads, bukan bukti terverifikasi. Satu sumber tidak cukup untuk status `VERIFIED`; riset mendalam, audit klaim, provenance media, dan Final QA tetap menjadi gate.

Implikasi: aturan ini harus dipertahankan saat discovery diperbaiki. Skor topik yang tinggi tidak boleh melewati gate verifikasi.

## 5. Baseline tes dan CI

README mendokumentasikan perintah suite lengkap:

```powershell
python -m pytest -q
```

Workflow [autonomous-intelligence.yml](../.github/workflows/autonomous-intelligence.yml) menjalankan:

1. `python -m compileall -q engine mcp tests/test_autonomous_intelligence.py`
2. `python -m unittest discover -s tests -p "test_autonomous_intelligence.py" -v`

Tes yang diperiksa mencakup resolusi request sederhana, inferensi format long-form, pengenalan permintaan discovery, dan satu skenario discovery yang menjaga batas antara feed lead dan bukti terverifikasi.

Status verifikasi pada sesi audit:

- Kode dan test file dibaca melalui GitHub.
- Tes tidak dijalankan secara lokal pada sesi ini; hasil tes aktual karena itu **belum terverifikasi oleh audit ini**.
- Status gabungan commit HEAD yang diperiksa hanya menampilkan status Vercel sukses; status tersebut bukan bukti bahwa tes Python lulus.
- Endpoint daftar workflow run yang tersedia pada sesi ini tidak memberikan hasil run yang bisa dipakai untuk memastikan hasil regresi terbaru.

## 6. Branch dan commit yang terlihat

Branch remote yang terlihat saat audit:

- `main`
- `feat/autonomous-content-intelligence`
- `tmp/nugi-10-short-scripts-1791098937863`

Commit yang terlihat terbaru pada `main` saat audit adalah `f07f7c61e8c5bd036cb2b932362cf0ae92f037f2`. Status remote tidak membuktikan apakah ada perubahan lokal yang belum di-commit pada komputer pengguna; kondisi lokal itu perlu diperiksa di lingkungan kerja sebelum melakukan operasi Git yang berisiko.

## 7. Urutan tindak lanjut yang direkomendasikan

1. **Tahap 01 — Blueprint editorial:** tetapkan spesifikasi perilaku, kontrak output, definisi niche, hard gate, status keputusan, dan rencana evaluasi tanpa membuat pipeline baru.
2. **Tahap 02 — Niche qualification:** pisahkan kecocokan niche dari potensi cerita dan editorial fit; hilangkan skor niche konstanta setelah tes yang sesuai tersedia.
3. **Tahap 03 — Discovery dan topic memory:** perbaiki input kandidat, deduplikasi, alasan seleksi, dan jejak asal ide.
4. **Tahap 04 — Scoping dan angle:** pastikan topik luas diarahkan menjadi pertanyaan cerita yang dapat diteliti.
5. Lanjutkan ke riset, uji kelayakan visual, story plan, script, fact-check, media, dan QA secara bertahap.

## 8. Kriteria penutupan Tahap 00

- Arsitektur produksi kanonis telah dipetakan.
- File utama untuk perbaikan editorial telah diidentifikasi.
- Temuan awal dan batas verifikasi telah dicatat.
- Belum ada perubahan kode produksi atau perubahan skema data.
- Tahap berikutnya dapat dimulai dengan spesifikasi yang lebih jelas, tanpa menganggap tes telah lulus atau workflow end-to-end telah terbukti berjalan.
