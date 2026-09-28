# ROADMAP.md — NUGI: Prioritas Pengembangan

**Prinsip:** NICHE → SELL → IMPLEMENT → DELIVER → RETAIN.
Setiap item harus menjawab: "Apakah ini membantu **mendapatkan client, menjalankan client, atau mempertahankan client**?" Jika tidak → prioritas rendah / tidak dibangun.

> **Konteks repo:** Source code core product TIDAK ada di repo ini (ada di repo
> eksternal GREN/Yanproland). Prioritas yang butuh repo eksternal ditandai [X-REPO].
> Referensi lengkap: `docs/CLIENT_READINESS.md`.

---

## Status Fase Terakhir (Phase 4 — demo ready)
- [x] Demo simulasi alur leads (`website/demo/`) live di https://www.nugi.biz.id/demo
- [x] Tautan "Demo" di navbar homepage • vercel `cleanUrls` OK • repo sinkron dengan remote
- [x] P0-4 fix menu mobile (di-commit & terverifikasi)

---

## P0 — WAJIB SEBELUM CLIENT PERTAMA (membantu MENDAPATKAN client)

### Bisnis & Alat Jual
- [ ] Tulis ICP operasional (developer perumahan Bandung Raya, 5–15 sales, Meta Ads) & satu hero offer di website (persempit positioning).
- [ ] Template **SOW + payment + IP + garansi + change request** (review hukum Indonesia).
- [ ] Sheet pricing & scope (termasuk pass-through biaya third-party/API).

### Produk (core workflow, minimal production-ready)
- [ ] [X-REPO] Impor/hubungkan engine eksternal → env produksi end-to-end:
      lead masuk → tersimpan → round-robin → WA sales → follow-up → dashboard manager.
- [ ] [X-REPO] Auth + role (Admin/Manager/Sales) & isolasi data antar-client.
- [ ] Backup otomatis + uji restore; path export/handover data.
- [ ] Label demo simulasi konsisten di semua materi jual.

### Penjualan
- [ ] Jalankan 5 discovery call (pipeline `business/BUSINESS_DASHBOARD.md`) & validasi harga.
- [ ] Checklist presentasi 10 langkah + demo run-through.

## P1 — PENTING SETELAH CLIENT PERTAMA (membantu MENJALANKAN & MEMPERTAHANKAN)
- [ ] Case study berangka + testimoni → ganti portfolio deskriptif.
- [ ] Retainer onboarding & laporan bulanan (Rp500rb/bln mulai bulan ke-2).
- [ ] tracking.js bersama + isi ID Meta Pixel/GA4 di semua halaman.
- [ ] site-config.js single source kontak (hapus 89 hardcode WA/email).
- [ ] SOP deployment/checklist pasca-handover (UAT → live → training 30 hari).

## P2 — NANTI
- [ ] Whitelabel config-driven engine untuk delivery multi-klien.
- [ ] Halaman /kontak, Google Business Profile, SEO backlog, artikel tambahan.
- [ ] Refactor partial (header/footer/CTA) kurangi duplikasi markup.

---

## Catatan dari Audit Client Readiness (ringkas)
- **Jangan menunggu produk sempurna** — jual sebagai implementasi custom ber-SOW untuk client #1.
- Timeline aman: hero offer **2–4 minggu** (bukan 3–5 hari); CRM/custom 4–8 minggu.
- Pembayaran: **50% DP → 40% UAT → 10% handover**.
- T&C website **tidak cukup** — wajib SOW/kontrak per proyek.
- Detail lengkap: `docs/CLIENT_READINESS.md`.
