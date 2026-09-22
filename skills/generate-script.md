# Skill: GENERATE-SCRIPT

## 1. Deskripsi & Tujuan
Mengubah ide konten yang terpilih menjadi naskah video pendek (*talking-head script*) berdurasi 60-90 detik yang terdengar 100% seperti manusia berbicara langsung: jujur, tajam, reflektif, mengalir santai, dan bebas dari jargon robotik AI.

---

## 2. Input Kontrak
```yaml
content_idea: string / object (Wajib: ringkasan ide atau nomor ide yang dipilih)
platform: string (opsional, default: "TikTok / Reels / Shorts")
duration_target: string (opsional, default: "60-90 detik (~160 kata)")
tone: string (opsional, default: "Conversational, tajam, reflektif, teman ngobrol")
```

---

## 3. Tahapan Pra-Penulisan (Pre-Flight Execution)
Sebelum menulis satu baris pun kalimat script, AI wajib:
1. **Fact Verification:** Memastikan setiap angka atau fakta penting dalam ide sudah diverifikasi ke sumber primer/berita terpercaya.
2. **Knowledge Retrieval & Rerank:** Ambil 2-3 prinsip penceritaan (*storytelling*) dan pengaruh (*influence*) dari repositori melalui `retriever.retrieve()`.
3. **Determine Story Architecture:** Tentukan alur:
   `HOOK → TENSION → QUESTION → STORY / CONTEXT → REVELATION → OPEN QUESTION`

---

## 4. Format Output Script Standar

Script wajib disajikan dalam struktur berikut:

```markdown
# JUDUL VIDEO: [Judul Ringkas & Menarik]
**Topik Utama:** [Topik] | **Format:** Talking-Head (60-90 Detik) | **Kata:** ~160 kata

---

### ARSITEKTUR NARRATIVE & KNOWLEDGE ANCHOR
- **Story Arc:** [Contoh: The Creativity Plot / Unexpected Schema Break]
- **Applied Influence Principles:** [Contoh: Social Currency + Cialdini Scarcity]
- **Key Source:** [Contoh: Laporan BPS / Stanford AI Index 2026]

---

### NASKAH TALKING-HEAD (Siap Dibaca)

**[00:00 - 00:05] HOOK**
[Kalimat pembuka yang mematahkan asumsi atau menyoroti kejanggalan di depan mata]

**[00:05 - 00:18] TENSION & PARADOX**
[Memperlihatkan fakta yang bertolak belakang, mengapa situasi ini membuat kita bingung atau cemas]

**[00:18 - 00:42] CONTEXT & THE REAL DATA**
[Membeberkan fakta lapangan dan realitas apa yang sebenarnya sedang terjadi]

**[00:42 - 00:65] THE REVELATION (DEEPER WHY)**
[Membongkar alasan psikologis atau struktural di baliknya, membuat audiens melihat sesuatu yang baru]

**[00:65 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)**
[Pertanyaan penutup yang tajam untuk direnungkan audiens, TANPA forced CTA]

---

### QUALITY CHECK PRE-FLIGHT
- [x] Bahasa terasa seperti percakapan santai, bukan artikel atau kuliah.
- [x] Tidak ada kata klise AI ("Di era digital yang serba cepat...").
- [x] Tidak ada CTA mengemis ("Jangan lupa follow").
- [x] Sumber dan fakta valid dapat dipertanggungjawabkan.
```
