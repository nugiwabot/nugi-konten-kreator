# 📚 Nugi Content Creator — Documentation Index

Selamat datang di dokumentasi resmi **Nugi Human–Place Content Intelligence Engine**. Repositori ini adalah sistem editorial intelligence mandiri yang mengubah pertanyaan tentang dunia nyata menjadi narasi mendalam berbasis penalaran kausal (*causal reasoning*) dan bukti empiris.

---

## 🧭 Daftar Dokumentasi

| Dokumen | Deskripsi |
| :--- | :--- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Arsitektur menyeluruh sistem editorial intelligence, diagram alur data, provider abstraction, dan modul pipeline. |
| [`EDITORIAL_PLAYBOOK.md`](EDITORIAL_PLAYBOOK.md) | Panduan operasional editorial `HUMAN × PLACE × CHANGE × WHY`, 10 kriteria Human–Place anchor, 10 Story Types, dan revelation mechanics. |
| [`LOCAL_AI_INFRASTRUCTURE.md`](LOCAL_AI_INFRASTRUCTURE.md) | Panduan infrastruktur AI lokal (LAN): LM Studio Embedding (`:1234`) dan TEI Reranker (`:8080`), fail-safe policy, dan guardrails. |
| [`KEYWORD_DATASET.md`](KEYWORD_DATASET.md) | Petunjuk pemanfaatan dataset opsional `riset keyword.json` untuk *question mining* dan klasterisasi semantik tanpa ketergantungan keras. |
| [`CLI_REFERENCE.md`](CLI_REFERENCE.md) | Panduan lengkap perintah antarmuka terminal `engine_cli.py` (`doctor`, `mine`, `research`, `generate`, `video`). |
| [`INTELLIGENCE_GAP_ANALYSIS.md`](INTELLIGENCE_GAP_ANALYSIS.md) | Audit awal dan status implementasi RSS, provider riset/media, rights, B-roll, dan verifikasi visual. |

---

## 🏛️ Batasan Repositori & Integritas Lingkup

> [!IMPORTANT]
> **INDEPENDENT SYSTEM — NO CROSS-REPO DEPENDENCIES**
> 
> Repositori ini berdiri sendiri secara otonom. Tidak ada ketergantungan runtime, impor kode, skema basis data, atau konteks bisnis dari repositori eksternal lain (misal: CRM, Leads Rotator, Landing Page developer, atau tools agensi).
> 
> Catatan historis model bisnis agensi masa lalu telah dipisahkan ke dalam [`archive/legacy_agency_system/`](../archive/legacy_agency_system/README.md).
