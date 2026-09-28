# 📊 Keyword Dataset Guide (`riset keyword.json`)

## 1. Status & Peran Dataset

Dataset `riset keyword.json` (yang dapat diletakkan di root atau direktori output) adalah **dataset eksternal OPSIONAL dan bersifat READ-ONLY**.

Dataset ini:
- **BUKAN** ketergantungan keras (*hard dependency*). Sistem tetap dapat beroperasi normal tanpa dataset ini.
- **BUKAN** alasan untuk mengimpor repositori eksternal atau memicu ketergantungan antar-proyek.
- **HANYA DIGUNAKAN SEBAGAI SINYAL DISCOVERY:**
  - Menemukan pertanyaan riil yang sering diajukan masyarakat.
  - Mengklasifikasikan intensi pencarian alami.
  - Membantu klasterisasi semantik topik.

---

## 2. Integritas Data & Proteksi Read-Only

Untuk menjaga integritas data mentah:
1. **Never Modified in Place:** Engine dilarang menulis ulang, menimpa, atau menghapus file `riset keyword.json`.
2. **Fingerprint & Caching:** Sistem menghitung SHA-256 fingerprint dari konten dataset. Hasil ekstraksi query dan klasterisasi disimpan di direktori cache (`engine/data/cache/`) terpisah, sehingga pembacaan berikutnya instan tanpa membebani memori.
3. **Format Support:** Engine secara fleksibel dapat membaca dataset dalam format array JSON standar, newline-delimited JSON (JSONL), maupun format terbungkus (*wrapped payload*).

---

## 3. Alur Transformasi Discovery (How-To → WHY)

Pertanyaan yang ditemukan dalam dataset pencarian seringkali berformat prosedural (*how-to*) atau transaksional. Sistem menerapkan aturan reformulasi:

```text
[Input Query Mentah]
"Cara mengurus sertifikat tanah ke BPN biaya dan syarat 2026"
        ↓
[Intent Classification: Procedural + Legal]
        ↓
[Human–Place Bridge: Criterion E (how_land_is_used)]
        ↓
[Reformulasi Editorial Nugi (WHY Question)]
"Mengapa sistem sertifikasi tanah di Indonesia membutuhkan proses yang begitu panjang, dan bagaimana asal-usul birokrasi pertanahan ini terbentuk sejak era kolonial?"
```
