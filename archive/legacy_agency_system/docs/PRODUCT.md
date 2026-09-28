# PRODUCT.md — NUGI: Kondisi Produk Saat Ini

> **Catatan penting:** Repo ini TIDAK berisi source code core product
> (Lead Rotator / CRM / Landing Engine). Mesin tersebut berada di repo eksternal
> (Omnichannel GREN Hub, Yanproland Leads-Rotator, Yanproland CRM, LP-GREN).
> Yang ada di repo ini: website marketing statis + aset demo + dokumen bisnis.

## Layanan yang Dijual (halaman website)
| Layanan | Harga | Durasi | Status di repo |
|---|---|---|---|
| Landing Page Properti | Rp2,5jt+ | 2–4 hari | Halaman promosi statis |
| Sistem Leads & WA Rotator | Rp3,5jt+ | 3–5 hari | Halaman promosi statis (mesin di repo eksternal) |
| CRM Properti | Rp7,5jt+ | 7–14 hari | Halaman promosi statis (mesin di repo eksternal) |
| Sistem Custom | sesuai kebutuhan | variatif | Halaman promosi statis |
| Retainer Care | Rp500rb/bln | bulanan | — |

## Fitur yang Benar-Benar Berjalan di Repo Ini
- Website statis 9 halaman (Home, 4 layanan, /artikel + 3 artikel) — deploy Vercel.
- Interaksi marketing: navbar scroll, menu mobile, FAQ accordion, slideshow authority, form konsultasi → wa.me.
- SEO: JSON-LD, sitemap 10 URL, robots, canonical, OG/Twitter.
- **Demo simulasi alur leads** (`website/demo/`, tautan "Demo" di nav): lead masuk → distribusi
  round-robin → notifikasi WA sales → follow-up → progres manager. Data dummy berlabel, tanpa data pribadi.

## Fitur yang Masih Prototype / Belum Ada
- **Core workflow (Lead masuk → tersimpan → distribusi → sales menerima → follow-up → manager melihat):**
  TIDAK ADA kodenya di repo ini (mesin di repo eksternal).
- Dashboard/mockup di homepage = statis (angka contoh), bukan aplikasi hidup.
- Tracking Pixel/GA4/Google Ads: config kosong, loader hanya di index.html.
- Studi kasus berangka, testimoni, demo live interaktif: belum ada.

## Risiko Teknis Terlihat
- Menu mobile: diperbaiki (P0-4, lihat ROADMAP) — inline style di-reset saat resize ke desktop.
- Nomor WA/email hardcode 89x di HTML → rawan tidak sinkron.
- Loader tracking hanya di index.html; subhalaman tidak akan mengirim event walau ID diisi.
- `trackNugiEvent` berpotensi double-push ke dataLayer (gtag + push manual).
- Nama brand tidak konsisten (NUGIPROPERTI / Nugi Digital Studio).

## Matriks Kesiapan Jual (core workflow — detail di CLIENT_READINESS.md)
| Item | Kategori |
|---|---|
| Lead masuk tersimpan ke DB; round-robin adil; notifikasi WA; follow-up tercatat; dashboard manager | **MUST WORK BEFORE SELLING** |
| Auth+role (Admin/Manager/Sales); isolasi data antar-client; backup; export/handover | **MUST WORK BEFORE DEPLOYMENT** |
| Polish dashboard, format pesan, export, mobile | **CAN BE FIXED DURING IMPLEMENTATION** |
| CAPI/pixel konversi, reminder otomatis, unit booking | **CAN WAIT** |
| SaaS self-serve, aplikasi mobile, broadcast engine | **DO NOT BUILD YET** |

## Definisi BUG vs CHANGE vs FEATURE (anti scope-creep)
- **BUG** = perilaku menyimpang dari SOW/spec → gratis (garansi 30 hari).
- **CHANGE REQUEST** = modifikasi spec yang disepakati → quote & bayar dulu.
- **FEATURE REQUEST** = kemampuan baru di luar lingkup → project/add-on terpisah.

