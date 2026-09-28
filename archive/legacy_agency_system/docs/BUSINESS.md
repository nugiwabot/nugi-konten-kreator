# BUSINESS.md — NUGI: Business Direction

**Status:** PRA-PENDAPATAN (per 2 Sep 2026) — Leads 0, Klien 0, Revenue Rp0
**Sumber:** `business/`, root docs, dan `docs/CLIENT_READINESS.md`.

## Target Customer Paling Spesifik (ICP Operasional)
- **Primer:** **Developer perumahan kecil–menengah (klaster/subsidi/komersial) di Bandung Raya & Jawa Barat** dengan:
  - tim sales in-house **5–15 orang**,
  - aktif **Meta Ads** (belanja iklan ±Rp5–30jt/bln),
  - leads masuk via **WhatsApp/formulir** (±100–500/bln),
  - distribusi masih **manual** (grup WA/Excel) → respons lambat & rebutan,
  - **Marketing Manager/Principal** kesulitan memantau follow-up prospek.
- **Bukan** target utama dulu: kantor agen tanpa tim sendiri, pengelola kost, proyek custom bebas.
- Pengambil keputusan: Owner / Principal / Marketing Manager (belum tervalidasi — wajib discovery call).

## Masalah Utama Customer
1. **P01 (skor 1250):** Leads iklan dibagi manual via grup WA → rebutan & respons lambat (>1 jam).
2. **P03 (skor 640):** Landing page lambat, pixel tidak terbaca, form WA rusak.
3. **P02 (skor 533):** Owner buta status follow-up sales (survey? closing?).
4. Data prospek hilang saat sales resign; sales lupa follow-up prospek hangat.

## Solusi Utama NUGI (Hero Offer — satu, bukan banyak)
> "Developer membayar iklan untuk leads, lalu kehilangan leads karena respons lambat &
> pembagian manual. Nugi memastikan **setiap lead iklan sampai ke sales dalam <10 detik,
> adil (round-robin), dan follow-up terpantau** — tanpa mengubah cara kerja tim Anda."

Pricing eksperimen: Pilot Rp2,5–3,5jt | Standard Rp4,5–5,5jt | Full-Suite Rp7,5–12jt.
Skema pembayaran: **50% DP → 40% saat UAT disetujui → 10% saat handover**. Retainer Rp500rb/bln.

## Positioning
One-Person AI Software & Automation Studio, khusus satu niche:
"Distribusi & follow-up leads WhatsApp untuk developer perumahan yang beriklan di Meta Ads."
Bukan: software house umum, agensi marketing, jasa custom bebas tanpa batas.

## Pricing & Scope (ringkas — detail di CLIENT_READINESS.md)
- Implementation fee (sekali, sesuai SOW) • Retainer (Rp500rb/bln, opsional)
- Third-party/API cost (pass-through, milik client)
- Change request & feature tambahan = quote terpisah (bayar dulu)
- Maks 2x revisi minor dalam lingkup; **BUG gratis (garansi 30 hari) ≠ CHANGE ≠ FEATURE**.

## Risiko Kritis
| Risiko | Level | Mitigasi |
|---|---|---|
| Scope creep | Sangat Tinggi | SOW tertulis, 2x revisi minor, add-on berbayar |
| Piutang macet | Sedang–Kritis | 50% DP, staging milik studio, lunas dulu baru handover |
| WhatsApp banned | Sedang–Kritis | Anti-spam, delay, migrasi WABA/Cloud API |
| Founder overwhelm | Tinggi | Fokus 1 produk utama dulu |
| Legal (belum ada SOW/T&C) | Tinggi | Template SOW + review hukum sebelum client #1 |
| Tracking tidak aktif | Tinggi | Isi Meta Pixel/GA4 ID di semua halaman |

## Asumsi Belum Teruji (wajib divalidasi via 5–10 discovery call)
- Harga Rp3,5–5jt diterima; buying cycle 3–7 hari; retainer berkelanjutan; preferensi bayar sekali vs sewa.
