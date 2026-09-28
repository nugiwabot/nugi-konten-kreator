# CLIENT_READINESS.md — NUGI: Business, Product & Client Readiness Audit

**Status audit:** Evaluasi kritis (Phase 1–4 selesai; repo berisi website marketing + docs + demo simulasi; engine produksi masih di repo eksternal).
**Posisi Nugi saat ini:** Pra-pendapatan. 0 lead/klien. Alat jual (website, demo, docs) sudah ada; fondasi legal & keamanan belum.

---

## A. NICHE & MARKET FIT

### Positioning saat ini (dari website & docs)
"Konsultan & pembuat sistem digital untuk **kantor agen, developer, dan tim marketing properti**" + sekunder **pengelola kost** + layanan **sistem custom**. → **Terlalu luas**: 3–4 segmen sekaligus dengan hero offer yang belum tunggal.

### ICP Paling Spesifik & Realistis (rekomendasi)
**Developer perumahan kecil–menengah (klaster/subsidi/komersial) di Bandung Raya & Jabar** yang:
- punya tim sales in-house **5–15 orang**,
- aktif **Meta Ads** dengan belanja iklan ±Rp5–30jt/bln,
- leads masuk via **WhatsApp/formulir** (±100–500/bln),
- masih membagikan leads **manual** (grup WA/Excel) → respons lambat, rebutan, follow-up tidak terpantau,
- **Marketing Manager/Principal** kesulitan melihat status prospek (sudah disurvey? booking? closing?).

### Apakah masalahnya "mahal"?
Ya, nyata: harga lead iklan properti ±Rp20–80rb/lead. Kehilangan 20–30% leads karena respons lambat = ratusan ribu–jutaan rupiah menguap tiap bulan. Pembayaran sekali (Rp3,5–7,5jt) lebih kecil dari belanja iklan bulanan developer. → WTP masuk akal, tapi **belum divalidasi dengan discovery call**.

### Positioning terlalu luas? → YA.
Yang dipersempit: dari "semua bisnis properti + kost + custom" menjadi **satu hero offer**:
"Distribusi & follow-up leads WhatsApp untuk developer perumahan yang beriklan di Meta Ads."

### Yang TIDAK dijual dulu
- Sistem kost/sewa unit, sales-link cloner PWA, broadcast engine, video/TTS generator.
- "Sistem custom bebas" tanpa batas → hanya sebagai add-on berbayar.

### Kenapa memilih Nugi (vs alternatif)
| Alternatif | Kelemahan mereka | Nugi |
|---|---|---|
| CRM SaaS murah | Umum, tidak WA-first, biaya sewa bulanan, config kaku | WhatsApp-first, bayar sekali, sesuai SOP |
| Freelancer programmer | Tidak paham domain properti, lama | Founder ex-SPV property (5+ thn) + AI-assisted cepat |
| Agency digital marketing | Mahal, fokus iklan bukan sistem | Fokus sistem distribusi & follow-up |
| Bangun sendiri | Butuh waktu, WA-ban risk, no support | Sudah jadi + garansi 30 hari |
| Excel/WhatsApp manual | Lambat, rebutan, tidak terpantau | Otomatis & teraudit |

### Value Proposition (paling kuat)
> "Developer membayar iklan untuk leads, lalu kehilangan leads karena respons lambat & pembagian manual. Nugi memastikan **setiap lead iklan sampai ke sales dalam <10 detik, adil (round-robin), dan follow-up terpantau** — tanpa mengubah cara kerja tim Anda."

### Skor
| Dimensi | Skor | Alasan |
|---|---|---|
| NICHE SPECIFICITY | **5/10** | Hero offer ada, tapi ICP operasional belum ditulis & masih jual 3 segmen |
| PROBLEM SEVERITY | **8/10** | Lead response time = masalah mahal & nyata (belum divalidasi client) |
| WILLINGNESS TO PAY | **6/10** | Harga kecil vs ad spend, tapi belum terbukti kesediaan bayar |
| DIFFERENTIATION | **5/10** | WA-first + domain property + kecepatan; belum ada moat |
| SELLABILITY | **5/10** | Website+demo+price ada; belum ada testimoni/case study berangka |

---

## B. APAKAH PRODUK SUDAH LAYAK DIJUAL?

**Jangan menunggu sempurna.** Jual sebagai *implementasi custom untuk client pertama* dengan lingkup ketat.

### Matriks Kesiapan (core workflow)
| Item | Kategori |
|---|---|
| Lead masuk (manual entry / webhook) tersimpan ke DB | **MUST WORK BEFORE SELLING** |
| Distribusi round-robin adil (tanpa dobel) | **MUST WORK BEFORE SELLING** |
| Sales menerima notifikasi WA (gateway/wa.me yang konsisten) | **MUST WORK BEFORE SELLING** |
| Follow-up bisa dicatat & status bergerak | **MUST WORK BEFORE SELLING** |
| Manager melihat progres per sales/status | **MUST WORK BEFORE SELLING** |
| Auth + role (Admin/Manager/Sales) | **MUST WORK BEFORE DEPLOYMENT** |
| Isolasi data antar-client + backup + path handover/export | **MUST WORK BEFORE DEPLOYMENT** |
| Polish dashboard, format pesan, export, mobile | **CAN BE FIXED DURING IMPLEMENTATION** |
| CAPI/pixel konversi, reminder otomatis, unit booking | **CAN WAIT** |
| SaaS self-serve, aplikasi mobile, broadcast engine | **DO NOT BUILD YET** |

### Batas minimal "production-ready" untuk client #1
Lead tersimpan → round-robin → WA terkirim → status tercatat → dashboard manager, **plus** auth+role, isolasi data, backup, dan path handover. Selain itu bisa menyusul.

### Demo boleh pakai simulasi/mock data?
**Boleh**, wajib diberi label:
- Seluruh halaman demo: **"DEMO/SIMULASI — data fiktif"** (sudah ada banner di `website/demo/`).
- Angka statistik, waktu "<10 detik", dan kartu WA = **tampilan simulasi**, bukan bukti produksi.
- Jangan pernah menyebut data demo sebagai data klien nyata.

---

## C. DEMO & PRESENTASI CLIENT

- **Demo wajib?** Tidak secara hukum, tapi **sangat disarankan** untuk harga B2B Rp3,5–7,5jt.
- **Demo simulasi cukup untuk tahap awal?** **Ya** — gunakan `website/demo/` yang sudah berjalan.
- **Demo production/live?** Setelah **client #1 live**, jadikan deployment itu case study demo.
- **Jika backend belum sempurna:** presentasikan *alur* (simulasi), transparan bahwa ini simulasi; fokus ke pemahaman workflow, bukan teknologi.
- **Boleh dijanjikan:** hasil alur (lead→sales <1 menit, adil, follow-up terpantau), waktu delivery, garansi 30 hari, penyesuaian SOP.
- **TIDAK boleh dijanjikan:** angka konversi/ROI spesifik, SLA uptime, fitur unlimited, permanensi nomor WhatsApp (risiko ban), integrasi akun Meta client tanpa akses.

### Perbedaan istilah
| Istilah | Arti |
|---|---|
| **Demo** | Simulasi interaktif berlabel; untuk memahamkan alur |
| **Prototype** | Versi fungsional parsial; belum dijual sebagai final |
| **Production system** | Terpasang, data nyata, dipakai tim client |
| **Custom implementation** | Lingkup per SOW: modul + integrasi sesuai kebutuhan |

### Struktur presentasi (maks 10 langkah)
1. Masalah (cerita developer: leads hilang karena lambat) — 2 mnt
2. Dampak (rupiah hilang, follow-up tidak terpantau)
3. Solusi Nugi (satu kalimat value proposition)
4. Demo simulasi alur (5 step di `website/demo/`)
5. Cara implementasi (milestone 2–4 minggu)
6. Hasil yang diharapkan (kriteria sukses & contoh dashboard)
7. Harga (paket + retainer + apa yang di luar lingkup)
8. Timeline (T+0 → handover)
9. Next step (diskusi alur kantor client → proposal/SOW)
10. FAQ & penutupan (garansi, dukungan, pembayaran)

---

## D. TIMELINE PENGERJAAN CLIENT

| Kompleksitas | Estimasi aman | Catatan |
|---|---|---|
| Landing page saja | 1 minggu | Realistis |
| Hero offer: rotator + LP + dashboard dasar | **2–4 minggu** | Rekomendasi untuk client pertama (buffer 30–50%) |
| CRM + rotator + integrasi | 4–6 minggu | |
| Custom multi-modul | 4–8 minggu | Hati-hati, scope creep |

**Jangan janji 1 minggu untuk sistem leads.** Timeline pertama = **3–4 minggu** paling aman.

### Milestone (contoh)
1. **Discovery & requirement** (hari 1–3): alur kantor client, data contoh, role.
2. **Configuration/development** (minggu 1–2): DB, round-robin, WA, dashboard.
3. **Integration** (minggu 2–3): webhook/Meta/Google Ads/LP.
4. **Testing** (minggu 3): internal + skenario error.
5. **UAT** (minggu 3–4): demo ke client, persetujuan.
6. **Deployment** (akhir minggu 4): live, data awal, backup.
7. **Training/handover** (hari 1–3 pasca-deploy): SOP pakai, garansi 30 hari.

### Pembayaran (rekomendasi)
**50% DP** (sebelum mulai) → **40% saat UAT disetujui** → **10% saat handover**.
(Atau 50/50 bila kecil; hindari 100% di awal tanpa DP.)

---

## E. PRICING & SCOPE

Pisahkan biaya:
| Jenis | Perlakuan |
|---|---|
| **Implementation fee** | Sekali, sesuai SOW (scope pasti) |
| **Maintenance/support** | Retainer Rp500rb/bln (opsional) |
| **Third-party/API cost** | Pass-through (gateway WA, server, Meta API) — milik client |
| **Change request** | Di-quote terpisah, mis. per fitur Rp500rb–2jt |
| **Additional feature** | Per quote, baru dikerjakan setelah pembayaran |

### Hindari "bayar sekali minta fitur unlimited"
- **Revisi:** maks 2x revisi minor dalam lingkup SOW; di luar = change request.
- **Scope:** daftar modul & batasan eksplisit di SOW (termasuk apa yang TIDAK termasuk).

### BUG vs FEATURE vs CHANGE
- **BUG** = perilaku menyimpang dari SOW/spec yang disepakati → diperbaiki gratis (garansi 30 hari).
- **CHANGE REQUEST** = modifikasi spec yang sudah disepakati → quote & bayar dulu.
- **FEATURE REQUEST** = kemampuan baru di luar lingkup → dijadwalkan sebagai project baru/add-on.

---

## F. LEGAL & WEBSITE PROTECTION

### Dokumen yang dibutuhkan Nugi
Terms & Conditions (website) • Privacy Policy • Disclaimer • **Service Agreement / SOW** • Payment Terms • Warranty Terms • Maintenance Terms • Change Request Terms • Data handling/privacy • **IP/source-code ownership** • Third-party API/service terms.

### ⚠️ Apakah T&C tersembunyi di website cukup?
**TIDAK kuat.** T&C website (apalagi tersembunyi) hanya mengatur penggunaan website, bukan spesifik proyek; klausul sepihak bisa lemah di hadapan hukum konsumen Indonesia (UU No. 8/1999) dan UU ITE bila tidak ada persetujuan tegas. **Klaim "sudah tertulis di website" tidak memberi perlindungan hukum yang kuat.**

### Apakah client tetap perlu tanda tangan SOW?
**Ya, WAJIB.** Kontrak/SOW per proyek (tanda tangan basah/elektronik) jauh lebih kuat: mendefinisikan scope, harga, timeline, hak IP, garansi, pembayaran, dan data. Website T&C = pelengkap, bukan pengganti.

### IP/source-code ownership (penting!)
Tentukan jelas: setelah lunas, **client memiliki sistem yang dikirim**; Nugi **mempertahankan hak atas komponen generik** (engine/rotator reusable) yang dilisensikan ke client. Tulis di SOW.

### ⚠️ Bagian yang butuh review profesional hukum Indonesia
Pasal garansi & batas tanggung jawab, kepemilikan IP, pembayaran, penanganan data pribadi (UU PDP No. 27/2022), klausul website T&C. (Konsultasikan ke advokat/praktisi hukum sebelum client pertama.)

---

## G. DATA & SECURITY

### Data yang mungkin disimpan
Nama prospek, nomor HP/WA, sumber lead, catatan, status follow-up, data sales, (potensial) unit. → Data pribadi (UU PDP).

### Minimum security requirement SEBELUM client #1
1. **HTTPS** di semua env.
2. **Auth + role** (Admin/Manager/Sales); sales hanya lihat leads miliknya (sesuai kebijakan client).
3. **Isolasi data antar-client** (schema/tenant column + RLS; jangan pernah campur).
4. **Credential/API key** TIDAK pernah di repo; pakai env/secrets manager; token Meta/WhatsApp disimpan terenkripsi dengan akses minimal.
5. **Backup** otomatis harian + uji restore; kebijakan retention tertulis.
6. **Deletion/retention**: klien berhak minta hapus data; buat mekanisme hapus + **path handover/export** (CSV/JSON/DB dump) saat berakhir.
7. Log aktivitas minimal (siapa mengubah status kapan).

---

## H. CLIENT READINESS SCORE

| Dimensi | Skor | Alasan |
|---|---|---|
| NICHE | **5/10** | Ada hero offer, ICP belum operasional |
| PRODUCT | **4/10** | Demo+website ada; engine produksi belum di repo ini |
| DEMO | **7/10** | Demo simulasi berjalan, berlabel, bisa diuji |
| TECHNICAL READINESS | **4/10** | Engine eksternal belum terintegrasi; isolasi/backup/auth belum |
| BUSINESS READINESS | **4/10** | Strategi matang, tapi 0 klien/lead |
| LEGAL READINESS | **2/10** | Belum ada SOW/T&C/Privacy |
| SELLABILITY | **5/10** | Siap presentasi, belum ada bukti sosial |

- **BIGGEST RISK:** Menjual sebelum scope/legal siap → scope creep, pekerjaan tanpa bayar, sengketa; risiko ban WhatsApp.
- **BIGGEST OPPORTUNITY:** Niche ultra-spesifik (developer + Meta Ads + WhatsApp) dengan kredibilitas founder di properti; harga kecil vs belanja iklan client.
- **BIGGEST THING TO FIX:** **ICP operasional + SOW/hukum + 1 pilot berbayar** untuk membuktikan kesediaan bayar.

---

## I. ROADMAP

### P0 — Wajib sebelum client pertama (membantu MENDAPATKAN client)
- [ ] Tulis ICP operasional & satu hero offer di website (persempit positioning).
- [ ] Buat template **SOW + payment + IP + garansi + change request** (review hukum).
- [ ] Buat sheet pricing & scope (termasuk pass-through third-party).
- [ ] Security baseline: auth+role, isolasi data, backup+restore, export/handover.
- [ ] Label demo simulasi konsisten di semua materi jual.
- [ ] Jalankan 5 discovery call (pipeline business/DASHBOARD) & validasi harga.
- [ ] Checklist presentasi 10 langkah + demo run-through.

### P1 — Penting setelah client pertama (membantu MENJALANKAN & MEMPERTAHANKAN)
- [ ] Case study berangka + testimoni → ganti portfolio deskriptif.
- [ ] Retainer onboarding & laporan bulanan.
- [ ] Isi ID tracking (Pixel/GA4) di semua halaman.
- [ ] SOP deployment/checklist pasca-handover.

### P2 — Nanti
- [ ] Whitelabel engine, halaman /kontak, Google Business Profile, SEO backlog.
- [ ] Pass-through gateway WA resmi bila volume klien naik.

*Setiap item di atas menjawab: "membantu mendapatkan/menjalankan/mempertahankan client?"*

---

## J. REKOMENDASI ISI DOKUMEN
- `docs/CLIENT_READINESS.md` → dokumen ini (audit penuh).
- `docs/BUSINESS.md` → tambah bagian ICP operasional, value proposition, pricing structure, legal/security pointer.
- `docs/PRODUCT.md` → tambah matriks kesiapan (B) & definisi BUG/FEATURE/CHANGE.
- `docs/ROADMAP.md` → struktur P0/P1/P2 di atas (menggantikan daftar fitur).
