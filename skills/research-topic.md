# Skill: RESEARCH-TOPIC v2

## 1. Deskripsi & Tujuan
Melakukan penyelidikan riset mendalam (*deep inquiry*) terhadap suatu topik, pertanyaan fundamental, atau fenomena terkini. Skill ini menghasilkan **Master Research Dossier** yang memisahkan fakta dari klaim/spekulasi, mengevaluasi sumber via 7-Tier Registry, memetakan rantai kausal ke ruang hidup, dan menggali hingga akar struktural WHY.

---

## 2. Input Kontrak
```yaml
topic: string (Wajib: pertanyaan, hipotesis, atau kata kunci pencarian)
research_mode: evergreen | current | historical | data_driven (default: auto-detect)
recency: string (opsional: 'all' untuk evergreen/historical, 'm' untuk 1 bulan, 'w' untuk 1 minggu)
max_sources: integer (opsional, default: 6)
```

---

## 3. Output Kontrak: Master Research Dossier

```markdown
# MASTER RESEARCH DOSSIER: [Topik]

### 1. METADATA RISET
- **Research Mode:** [Evergreen | Current | Historical | Data-Driven]
- **Primary Domain & Anchor:** [Domain: property/city/ai/work | Anchor: housing/land/space/city]
- **Property Causal Bridge:** [Rantai kausal penghubung topik ke ruang fisik manusia]

### 2. INTELIGENSI & FAKTA UTAMA (CORE EVIDENCE)
- **Fakta Objektif (Verified Facts):**
  - [Fakta 1 beserta rujukan data/angka konkret]
  - [Fakta 2 beserta tahun dan basis data]
- **Pemisahan Status Epistemik:**
  - **CLAIMS (Klaim Pihak Berkepentingan):** [Pernyataan pejabat/pengembang/korporat]
  - **INTERPRETATION (Analisis Pakar/Ekonom):** [Sudut pandang analisis independen]
  - **SPECULATION (Prediksi Masa Depan):** [Skenario yang belum terbukti]

### 3. EVALUASI SUMBER (7-TIER REGISTRY)
| No | Nama Sumber & Institusi | Tier (1–7) | Jenis Bukti | Catatan Kredibilitas |
| :-: | :--- | :---: | :--- | :--- |
| 1 | [Nama Institusi / Jurnal / Media] | Tier 1–5 | Data Resmi / Paper | [Tingkat keandalan fakta] |

### 4. KONTRADIKSI & HUMAN CONSEQUENCE
- **Kontradiksi Utama (The Paradox):** [Jurang antara asumsi publik vs data nyata]
- **Human Consequence:** [Bagaimana hal ini mengubah dompet, waktu, dan rasa aman manusia sehari-hari]

### 5. THE DEEPER WHY & EDITORIAL ANGLE
- **Penyebab Struktural (Level 4 WHY):** [Sistem perpajakan, insentif regulasi, atau hukum ekonomi yang menopangnya]
- **Akar Eksistensial (Level 5 WHY):** [Kebutuhan psikologis purba manusia yang mendasari perilaku tersebut]
- **Rekomendasi Sudut Pandang (Angles):** [2–3 sudut pandang narasi unik khas Nugi]
```
