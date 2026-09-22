# Skill: RESEARCH-TOPIC

## 1. Deskripsi & Tujuan
Melakukan riset terstruktur secara runtime terhadap suatu topik, berita terkini, atau fenomena industri, menyaring fakta dari sekadar opini, dan membedah implikasi manusiawinya.

---

## 2. Input Kontrak
```yaml
topic: string (Wajib: topik atau kata kunci pencarian)
recency: string (opsional: 'd' untuk hari ini, 'w' untuk minggu ini, 'm' untuk bulan ini, default: 'm')
max_sources: integer (opsional, default: 5)
```

---

## 3. Output Kontrak

```markdown
# HASIL RISET RUNTIME: [Topik]

### 1. RINGKASAN INTELIGENSI DUNIA NYATA
- **Peristiwa Utama:** [Apa yang baru saja terjadi?]
- **Apa yang Berubah (The Shift):** [Perubahan dibanding kondisi sebelumnya]
- **Siapa yang Terdampak:** [Kelompok masyarakat yang terkena dampak langsung/tak langsung]

### 2. MATRIKS EVALUASI SUMBER (7-TIER HIERARCHY)
| No | Nama Sumber & Domain | Tingkat Kredibilitas | Jenis Data | URL |
| :---: | :--- | :--- | :--- | :--- |
| 1 | [Nama Media] | Tier 1/4/5 | Fakta Primer / Riset | [Link] |

### 3. PEMISAHAN STATUS EPISTEMIK
- **Fakta Terverifikasi:**
  - Poin fakta 1 (didukung data).
- **Klaim & Pernyataan Pihak Terkait:**
  - Poin klaim 1 (klaim pengembang/perusahaan).
- **Opini & Spekulasi Publik:**
  - Poin opini 1.

### 4. AKAR MASALAH (THE DEEPER WHY) & KONTRADIKSI
- **Kontradiksi Utama:** [Di mana paradoks situasinya?]
- **The Root Why:** [Alasan psikologis/struktural mendalam]
```
