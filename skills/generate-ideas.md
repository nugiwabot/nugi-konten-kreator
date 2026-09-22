# Skill: GENERATE-CONTENT-IDEAS

## 1. Deskripsi & Tujuan
Menghasilkan ide konten orisinal dan membuka pikiran dengan menggabungkan **fakta terkini dari riset dunia nyata** dengan **Content DNA Nugi (`AI × PROPERTY × HUMAN × WHY`)** serta prinsip pengaruh permanen.

⚠️ **PERINGATAN RUNTIME:** Dilarang menghasilkan ide dari imajinasi kosong. AI WAJIB menjalankan runtime web research terlebih dahulu untuk mengambil peristiwa atau data aktual.

---

## 2. Input Kontrak
```yaml
topic: string (opsional, contoh: "AI Agents", "Harga Rumah Anak Muda", atau kosong untuk tren minggu ini)
audience: string (opsional, default: "Profesional muda dan pelaku usaha 25-40 tahun")
timeframe: string (opsional, contoh: "minggu ini", "bulan ini", default: "terkini")
number_of_ideas: integer (opsional, default: 3, maksimal: 5)
platform: string (opsional, default: "TikTok / Instagram Reels / YouTube Shorts")
objective: string (opsional, default: "Attention & Curiosity, membuka mata audiens")
```

---

## 3. Prosedur Eksekusi
1. **Current Research:** Jalankan pencarian web untuk topik yang diminta. Kumpulkan minimal 3-5 sumber terpercaya.
2. **Fact & Change Extraction:** Identifikasi apa peristiwa barunya (*what changed?*).
3. **Contradiction Search:** Temukan di mana paradoks atau kejanggalan antara ekspektasi vs realitas.
4. **DNA Synthesis:** Kaitkan dengan salah satu persimpangan alami:
   - `AI × HUMAN`
   - `PROPERTY × HUMAN`
   - `AI × PROPERTY`
   - `TECHNOLOGY × HUMAN`
   - `WORK × HUMAN`
   - `FUTURE × HUMAN`
5. **Knowledge Retrieval:** Retrieve 2-3 prinsip pengaruh yang relevan (misal: *Social Currency*, *Curiosity Gap*, *Loss Aversion*).
6. **Ide Formulation:** Susun ide ke dalam kontrak output standar.

---

## 4. Format Output Kontrak (Wajib Ada untuk Setiap Ide)

Untuk setiap ide yang dihasilkan, AI wajib menyajikan:

```markdown
### IDE #[N]: [TITLE / ANGLE YANG MENARIK PERHATIAN]

- **Current Event / Trigger Berita:** [Fakta objektif terkini yang terjadi]
- **Why It Is Interesting:** [Mengapa peristiwa ini tidak biasa dan memicu rasa ingin tahu]
- **Human Question:** [Pertanyaan eksistensial/keseharian yang langsung dirasakan audiens]
- **Contradiction:** [Kejanggalan atau paradoks antara asumsi umum vs realitas data]
- **Core Insight (The Revelation):** [Sudut pandang baru yang membuat audiens tertegun]
- **Potential Emotion:** [Emosi dominan: Awe, Curiosity-Anxiety, Reflektif, Legah]
- **Conversation Potential:** [Mengapa orang tergerak untuk berdiskusi di kolom komentar]
- **Shareability Rationale:** [Mengapa orang ingin membagikan video ini ke teman/keluarga (Social Currency / Practical Value)]
- **Suggested Story Direction:** [Alur singkat 3 babak: Pembuka yang janggal -> Realitas data -> Pertanyaan penutup]
- **Sources & Evidence:** [Daftar URL/nama sumber terverifikasi dengan tingkat kredibilitasnya]
```

*Catatan:* Jangan langsung menulis naskah/script utuh pada tahap ini kecuali secara spesifik diminta oleh pengguna.
