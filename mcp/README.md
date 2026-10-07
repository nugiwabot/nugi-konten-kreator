# Nugi Konten Kreator MCP Server

Controlled semantic interface between **Antigravity / AI Agents** and the **Nugi Konten Kreator** production repository.

---

## 🏛️ Arsitektur & Workflow Brain

Nugi MCP telah ditingkatkan dari sekadar kumpulan alat (*flat toolset*) menjadi **Workflow Orchestration Layer** yang bertindak sebagai *remote control + workflow brain* untuk pabrik konten Nugi Properti:

```text
USER / AI AGENT
       │ (Goal / Outcome)
       ▼
NUGI MCP ORCHESTRATION LAYER (server.py + workflows.py)
 ├─ nugi_workflow_plan       ──► Analisis intensi & pemetaan 10 workflow terdaftar
 ├─ nugi_workflow_preflight  ──► Pengecekan kesiapan aset & prasyarat (non-destructive)
 ├─ nugi_workflow_execute    ──► Eksekusi bertahap + persisten state checkpoint
 ├─ nugi_workflow_status     ──► Observabilitas proses & hasil antara
 └─ nugi_workflow_resume     ──► Melanjutkan eksekusi dari checkpoint terakhir
       │
       ▼
BUSINESS ENGINES (engine/)
 ├─ engine.editorial: script_auditor, human_place, fit_score, quality_gate
 ├─ engine.pipeline:  research_runner, script_parser, media_finder, auto_edit_capcut
 └─ engine.providers: search, wikimedia, internet_archive, pexafy
       │
       ▼
OUTPUT WORKSPACE & CHECKPOINTS
 ├─ output/<workspace>/ (Script, SRT, B-roll, CapCut Draft)
 └─ output/.workflow_runs/<run_id>.json (State checkpoint)
```

---

## 🚀 Menjalankan MCP Server

### 1. Mode Standar (STDIO - Local AI Agent)
Digunakan secara otomatis oleh Antigravity IDE atau Claude Desktop di komputer lokal:
```bash
python mcp/server.py --repo-root "c:\Users\Nugi\Documents\nugi-konten-kreator"
```

### 2. Mode Jaringan (SSE / HTTP - Komputer Server Windows IT & Multi-User)
Jalankan file batch:
```cmd
mcp\run_server_lan.bat
```
Atau via terminal:
```bash
python mcp/server.py --transport sse --host 0.0.0.0 --port 8000 --repo-root "c:\Users\Nugi\Documents\nugi-konten-kreator"
```

Klien dari komputer manapun di jaringan lokal (LAN/WiFi) dapat terhubung ke URL:
```text
http://<IP_KOMPUTER_SERVER>:8000/sse
```

---

## 🧭 Daftar 10 Core Workflows Terdaftar

| Workflow ID | Tier | Tujuan & Alur | Prasyarat Input | Tool Utama Terkait |
|---|---|---|---|---|
| `content_idea` | Tier 1 | Kualifikasi topik: Taksonomi → Human-Place → Brand Fit → Arketipe → WHY Angle → Sintesis rekomendasi | `topic` | `nugi_editorial_brand_fit`, `nugi_editorial_human_place` |
| `research_only` | Tier 1 | Riset berbasis bukti: Pencarian multi-sumber → Evaluasi kualitas sumber (7 tier) → Pemisahan Fakta/Klaim/Opini → Dossier | `topic` | `nugi_research_run`, `nugi_research_evaluate_source` |
| `script_only` | Tier 1 | Penulisan & validasi naskah 3-layer (Teleprompter, Evidence Cards, Research Notes) + Fact & Gate Audit | `topic` | `nugi_script_parse`, `nugi_editorial_script_audit` |
| `fact_check` | Tier 1 | Audit verifikasi klaim faktual, deteksi overclaim kausalitas, dan evaluasi Brand Fit Nugi Properti | `script_text` | `nugi_editorial_script_audit` |
| `content_audit` | Tier 1 | Audit komprehensif naskah: Fact Audit + Brand Fit (0–20) + Human–Place + Fit Score (0–100) + Quality Gate + Revelation | `script_text` | `nugi_editorial_script_audit`, `nugi_editorial_quality_gate` |
| `broll` | Tier 2 | Perancangan shot visual, ekspansi query berbasis entitas, pencarian arsip, perankingan 2-tahap, dan unduhan | `script` | `nugi_visual_generate_shots`, `nugi_media_find`, `nugi_media_download` |
| `subtitle` | Tier 2 | Pembangkitan file subtitle `.srt` tersinkronisasi kata-per-kata dari segmen teleprompter | `script_path` | `nugi_subtitle_generate`, `nugi_subtitle_validate` |
| `capcut_draft` | Tier 2 | Perakitan paket proyek CapCut Desktop draft (`draft_content.json`) dari rekaman mentah, B-roll, & subtitle | `workspace` | `nugi_capcut_generate`, `nugi_autoedit_validate` |
| `short_video` | Tier 3 | **Master Workflow Shorts (65–80s)**: Idea → Research → Script → Fact Audit → Editorial Audit → Visual → B-roll → Subtitle → CapCut Draft → Final Validation | `topic` | Orkestrasi menyeluruh (11 langkah) |
| `full_video` | Tier 3 | **Dokumenter Panjang (8–15 menit)**: Riset mendalam → Naskah per bab → Fact Audit → Visual Shot Blueprint → CapCut Assembly | `topic` | Orkestrasi fail-fast bertahap |

---

## 🛠️ Panduan Operasional Workflow (4 Mode)

### 1. Mode PLAN (`nugi_workflow_plan`)
Menerjemahkan bahasa alami pengguna menjadi rencana langkah dan mendeteksi input yang belum ada tanpa mengeksekusi apapun:
```json
// Input:
{"request": "Saya mau bikin short video tentang kenapa rumah dekat stasiun lebih mahal"}

// Output Rencana:
{
  "mode": "PLAN",
  "status": "planned",
  "detected_workflow_id": "short_video",
  "total_steps": 11,
  "ready_to_preflight": true,
  "recommended_next_action": "Run nugi_workflow_preflight(workflow_id='short_video', context={'topic': 'rumah dekat stasiun'})"
}
```

### 2. Mode PREFLIGHT (`nugi_workflow_preflight`)
Memeriksa ketersediaan aset dan ketergantungan sebelum menjalankan operasi mahal. Jika aset penting belum tersedia, sistem mengembalikan status **BLOCKED** secara terstruktur dengan petunjuk pemulihan yang jelas:
```json
// Input:
{"workflow_id": "capcut_draft", "context": {"workspace": "01-script"}}

// Output Jika Footage Belum Ada:
{
  "status": "BLOCKED",
  "missing_items": ["Main footage file (*.mp4) in footage/"],
  "recommended_next_step": "Place recorded voice-over or video into output/01-script/footage/",
  "recommended_tool": "nugi_output_create",
  "next_workflow": "broll"
}
```

### 3. Mode EXECUTE (`nugi_workflow_execute`)
Menjalankan tahapan workflow secara berurutan. Setiap langkah dicatat status, durasi, dan outputnya ke dalam state persisten:
```json
// Input:
{
  "workflow_id": "content_idea",
  "context": {"topic": "Kenapa denah rumah berubah dari zaman ke zaman?"}
}

// Output:
{
  "run_id": "wf_20261007_211500_a1b2c3",
  "status": "completed",
  "completed_steps": ["editorial_classify", "human_place", "property_brand_fit", "story_type", "why_angle", "recommendation"]
}
```

### 4. Mode RESUME (`nugi_workflow_resume`)
Jika sebuah alur terhenti di tengah jalan (misalnya B-roll gagal karena koneksi internet), pengguna dapat memperbaiki kendala lalu melanjutkan dari checkpoint terakhir tanpa mengulang langkah riset atau naskah:
```json
// Melanjutkan alur kerja:
nugi_workflow_resume(run_id="wf_20261007_211500_a1b2c3")
```

---

## 🔒 Keamanan & Batasan Operasional
1. **Confinement Mandiri:** Seluruh pembacaan dibatasi di dalam akar repositori (`REPO_ROOT`). Penulisan langsung hanya diizinkan di dalam folder `output/`.
2. **Tanpa Arbitrary Shell/Python Tool:** MCP tidak menyediakan alat eksekusi bebas (`eval`, `exec`, `shell`). Semua eksekusi berjalan melalui modul `engine/` yang telah diaudit.
3. **Persistensi State Ringan:** State run disimpan secara lokal di `output/.workflow_runs/<run_id>.json` dan dikecualikan dari Git tracking.

---

## 🧪 Menjalankan Test Suite

```bash
# Menjalankan seluruh test unit & integrasi MCP Workflow
pytest mcp/tests/ -v

# Menjalankan seluruh test repository engine
pytest tests/ -v
```
