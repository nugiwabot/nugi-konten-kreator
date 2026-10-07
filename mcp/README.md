# Nugi Konten Kreator MCP Server

Controlled semantic interface between **Antigravity / AI Agents** and the **Nugi Konten Kreator** production repository.

---

## 🏛️ Arsitektur & Lingkungan

```text
ANTIGRAVITY / REMOTE CLIENTS (PC Lain / Server IT)
                     │
         ┌───────────┴───────────┐
         │                       │
       STDIO                    SSE / HTTP
   (Local Agent)         (Remote / LAN :8000/sse)
         │                       │
         └───────────┬───────────┘
                     ▼
       NUGI KONTEN KREATOR MCP (server.py)
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
      READ          RUN          WRITE
       │             │       ┌─────┴─────┐
       │             │    output/     protected
       │             │       │           │
       │             │     ALLOW       PROPOSE
       │             │              (Proposal Flow)
       └─────────────┼─────────────┘
                     ▼
       NUGI KONTEN KREATOR REPOSITORY
   (Source of Truth: Nugi Konten Kreator Workspace)
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

## 🎬 Primary Video Engine: CapCut Desktop

Sesuai standar produksi terbaru, **CapCut Desktop Draft** adalah engine perakitan video utama:
1. `nugi_capcut_generate`: Menghasilkan paket draft CapCut dari footage mentah & B-roll di workspace target (`output/<workspace>/project/capcut/`).
2. `nugi_capcut_install`: Memasang draft yang telah dibuat langsung ke folder user draft CapCut Desktop (`com.lveditor.draft`).
3. `nugi_video_create_project`: Membangun pipeline video end-to-end dengan output CapCut Draft dan SRT subtitles.
4. `nugi_autoedit_analyze`: Mendiagnosis video mentah (resolusi, durasi, fps, audio).
5. `nugi_autoedit_validate`: Memvalidasi kelengkapan timeline CapCut.

---

## 🔍 Question Mining & Human Relatability

1. `nugi_question_mine`: Menambang peluang cerita editorial dari dataset kata kunci riset (`output/riset keyword.json`).
2. `nugi_visual_generate_shots`: Menguraikan naskah menjadi shot list visual dengan metadata **Human Relatability** lengkap (`primary_human_basic_need`, `life_lens`, `human_alignment_score`).

---

## 🧪 Menjalankan Unit Test MCP

```bash
pytest mcp/tests/test_mcp_server.py -v
```
