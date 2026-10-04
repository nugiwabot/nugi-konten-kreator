# 🎬 Evidence-Based B-Roll & Visual Retrieval System

> *"B-roll Nugi harus terasa seperti bukti visual (visual evidence) yang membantu penonton melihat apa yang sebenarnya sedang dibicarakan, bukan sekadar memenuhi layar dengan stock footage generik."*

Sistem B-Roll & Visual Retrieval Nugi berakar pada prinsip utama:

$$\mathbf{DOCUMENTARY\ TRUTH} \rightarrow \mathbf{SPECIFICITY} \rightarrow \mathbf{EVIDENCE} \rightarrow \mathbf{RELEVANCE} \rightarrow \mathbf{AESTHETICS}$$

Visual yang sedikit kurang sinematik tetapi benar-benar menunjukkan objek, orang, dokumen, atau peristiwa sejarah yang sedang dibicarakan jauh lebih bernilai dibanding video stok generik resolusi tinggi yang tidak ada kaitannya dengan realitas naskah.

---

## 0.1 Human Relatability Visual Layer — WAJIB UNTUK SCENE MANUSIA

Untuk scene yang membawa pengalaman manusia sehari-hari, sistem memprioritaskan **visual orang nyata + tempat nyata** yang sesuai dengan konteks narasi.

Visual retrieval harus mempertimbangkan:

    HUMAN BASIC NEED
    → HEALTH / WEALTH / RELATIONSHIP
    → EVERYDAY LIFE
    → HUMAN / PLACE B-ROLL

Setiap kandidat menerima metadata:
- human_basic_need_score
- life_lens_score
- everyday_relevance_score
- human_place_relevance_score
- human_alignment_score

Skor tersebut adalah **editorial/metadata alignment**, bukan penilaian emosi seseorang dan bukan computer-vision pixel score.

Untuk visual type HUMAN_LIFE / HUMAN_LIFE_IN_PLACE:
- query cenderung menyebut real people / real place / everyday life;
- gunakan foto/video orang, keluarga, pekerja, tetangga, rumah, jalan, lingkungan, kantor, taman, dan tempat nyata lain yang memang sesuai narasi;
- jangan mengganti scene manusia dengan ilustrasi abstrak, render AI, atau visual metafora ketika visual nyata tersedia;
- visual tetap harus relevan dengan kalimat yang sedang dibicarakan, bukan sekadar 'ada orang'.
## 0.2 REAL-WORLD B-ROLL TAXONOMY — VISUALIZE THE NARRATIVE, NOT JUST PEOPLE

Prinsip utama:
> B-roll harus menjawab: Apa yang secara nyata bisa dilihat di dunia jika kalimat narasi ini terjadi?

Real B-roll bukan berarti selalu harus menampilkan orang. Kandidat visual dapat berupa orang, tempat, benda, aktivitas, lingkungan, proses, infrastruktur, dokumen/data fisik, atau detail sensorik — selama objek tersebut merupakan representasi nyata dan relevan dari narasi.

### 8 kategori visual utama

1. PEOPLE — manusia
   - orang bekerja, pulang, tidur, makan, berjalan, berbicara, keluarga, pasangan, tetangga, konsumen, pekerja, warga.
   - dipilih ketika narasi berbicara tentang perilaku, pengalaman, keputusan, emosi, atau konsekuensi manusia.

2. PLACE — tempat
   - rumah, kamar, apartemen, kampung, perumahan, jalan, trotoar, kantor, sekolah, pusat kota, pinggiran kota, taman.
   - dipilih ketika narasi menjelaskan tempat manusia hidup atau lingkungan yang membentuk perilaku.

3. OBJECT — benda
   - pintu, jendela, pagar, kasur, meja, AC, kendaraan, ponsel, meteran listrik, kabel, kulkas, furnitur, alat kerja.
   - dipilih ketika benda tersebut adalah mekanisme nyata yang sedang dibahas.

4. ACTIVITY — aktivitas
   - memasak, perjalanan pulang, membuka pintu, bekerja, berbelanja, tidur, berkumpul, mengantar anak, berjalan kaki.
   - dipilih ketika WHY narasi terlihat melalui tindakan manusia.

5. ENVIRONMENT — kondisi lingkungan
   - panas, cahaya matahari, hujan, kemacetan, kebisingan, kepadatan, ruang sempit, jalan kosong, polusi, lingkungan hijau.
   - dipilih ketika kondisi ruang/lingkungan merupakan penyebab atau konsekuensi.

6. SYSTEM / INFRASTRUCTURE — sistem fisik yang terlihat
   - jalan, rel, jaringan listrik, gardu, kabel internet, tower, data center, saluran air, drainase, konstruksi, tata kota.
   - dipilih ketika narasi menjelaskan sistem yang memengaruhi kehidupan manusia.

7. PROCESS — proses yang bisa diamati
   - pembangunan rumah, lalu lintas kendaraan, transaksi, konstruksi, distribusi barang, produksi energi, perjalanan komuter.
   - dipilih ketika perubahan atau mekanisme adalah inti cerita.

8. EVIDENCE / ARTIFACT — bukti nyata
   - arsip, foto sejarah, peta, dokumen, papan harga, rambu, meteran, grafik yang bersumber, koran, artefak.
   - dipilih ketika narasi membuat klaim faktual yang membutuhkan bukti visual.
   - untuk klaim sejarah/entitas spesifik, tetap tunduk pada REAL_REQUIRED dan authenticity gate.

### Cara memilih kategori

Jangan menggunakan aturan sederhana: Narasi tentang manusia berarti cari manusia.

Gunakan urutan berpikir:
1. Apa yang sedang dikatakan: pengalaman manusia, tempat, benda, perubahan, sistem, sebab-akibat, atau fakta sejarah?
2. Apa yang paling konkret untuk mewakili kalimat itu?
3. Apa yang membuat penonton langsung melihat narasi tersebut?
4. Apakah visual itu memperkuat human basic need / Health–Wealth–Relationship yang sedang dibahas?
5. Apakah visual tersebut benar-benar ada di dunia nyata dan dapat dicari sebagai foto/video?

### Contoh

NARASI: Rumah yang lebih murah sering berada semakin jauh dari pusat kota.
B-roll: PRICE/OBJECT → papan harga atau listing nyata → PLACE → rumah di pinggiran → PEOPLE → keluarga melihat rumah → ENVIRONMENT → perjalanan panjang → ACTIVITY → orang commuting → SYSTEM → jalan dan transportasi.

NARASI: Rumah yang panas membuat tubuh lebih sulit beristirahat.
B-roll: ENVIRONMENT → ruangan panas/matahari masuk → OBJECT → kipas atau AC → PEOPLE → orang beristirahat → PLACE → kamar tidur nyata.

NARASI: Sebuah jalan yang diperlebar belum tentu menyelesaikan kemacetan.
B-roll: SYSTEM → jalan lebar → PROCESS → kendaraan bertambah → PEOPLE → komuter → ENVIRONMENT → traffic jam.

### Aturan prioritas

Untuk setiap shot, engine harus memilih primary visual category dan boleh memilih secondary category.

Metadata:
- primary_visual_category
- secondary_visual_category
- visual_reason
- narrative_visual_relation
- human_basic_need
- life_lens
- human_alignment_score

visual_reason harus menjelaskan mengapa visual tersebut mewakili kalimat, bukan hanya mendeskripsikan gambarnya.

Contoh: primary_visual_category = PEOPLE; visual_reason = Menunjukkan keluarga yang mengalami konsekuensi perjalanan rumah-kantor yang panjang.

### Prinsip penting

Human Basic Need menentukan mengapa penonton peduli.
Health / Wealth / Relationship menentukan dampaknya terhadap kehidupan.
Visual taxonomy menentukan apa yang harus ditampilkan di layar.

Jadi keduanya tidak boleh dicampur.

WEALTH bukan selalu visual uang. Dapat divisualisasikan melalui harga rumah, waktu commuting, kendaraan, biaya listrik, cicilan, lokasi kerja, dan infrastruktur.

HEALTH bukan selalu dokter atau rumah sakit. Dapat divisualisasikan melalui tidur, kamar panas, cahaya, kebisingan, aktivitas fisik, udara, dan ruang istirahat.

RELATIONSHIP bukan selalu pasangan. Dapat divisualisasikan melalui keluarga, tetangga, ruang makan, ruang keluarga, privasi, jarak antar-ruang, dan interaksi di lingkungan.

Dengan demikian basic need/life lens menjadi alasan editorial, sedangkan visual category menjadi keputusan sinematografi.

## 1. Lima Kelas Kebutuhan Visual (Visual Requirement Classes)

Setiap kalimat atau segmen naskah diklasifikasikan ke dalam tepat satu dari lima status berikut:

| Status | Makna & Penggunaan | Penanganan Provider | Contoh Naskah |
|---|---|---|---|
| `REAL_REQUIRED` | Visual **harus autentik** merepresentasikan entitas, peristiwa, atau dokumen riil yang disebut. Dilarang mengganti dengan stock footage generik. | Prioritas Wikimedia Commons & Internet Archive. **Pexafy DISABLED**. | *"Pada 6 Juni 1944, pasukan Sekutu mendarat di Normandia."* / *"Steve Jobs memperkenalkan iPhone pada 2007."* |
| `REAL_PREFERRED` | Ada entitas nyata atau tempat riil yang sangat diutamakan visual aslinya, namun tidak terikat pada satu momen tanggal/kejadian tunggal yang kaku. | Wikimedia Commons & Internet Archive utama; Pexafy diizinkan sebagai fallback kontekstual. | *"Pada awal abad ke-20, Jakarta masih sangat berbeda."* / *"Kota membuat manusia tinggal semakin padat."* |
| `GENERIC_ALLOWED` | Visual atmosfer, metafora, atau konteks umum di mana estetika dan mood lebih penting daripada pembuktian historis. | Pexafy, Wikimedia Commons, dan Internet Archive seluruhnya aktif. | *"Pagi hari, kota mulai bergerak."* / *"Manusia bekerja keras mengejar tenggat waktu."* |
| `NO_BROLL` | Segmen refleksi narasi, jeda dramatis, transisi retoris, atau pertanyaan pemantik. Tidak boleh dipaksa mencari media. | **Zero Media Queries**. Provider tidak dipanggil sama sekali. | *"Tapi di sinilah masalah sebenarnya dimulai."* / *"Pertanyaannya kemudian berubah."* |
| `REMOTION_REQUIRED` | Informasi berupa angka, data persentase, perbandingan statistik, kronologi timeline, atau diagram proses kausal. Lebih baik divisualisasikan dengan grafis gerak. | **Zero Media Queries**. Diteruskan ke generator Remotion motion-spec. | *"Populasi Tokyo meningkat dari 3 juta menjadi lebih dari 10 juta."* / *"Harga rumah meningkat dua kali lipat dalam 20 tahun."* |

---

## 2. Ekstraksi Entitas & Pemeliharaan Entitas (*Entity Preservation Rule*)

Sebelum melakukan pencarian atau ekspansi kata kunci, modul `visual_requirements.py` mengekstraksi entitas dari naskah:
- **PERSON**: Tokoh nyata (misal: *Steve Jobs, Albert Einstein, Sukarno, Henry Ford*)
- **PLACE / CITY / COUNTRY**: Lokasi nyata (misal: *Normandy, Tokyo, Jakarta, Bandung, Berlin, Hiroshima*)
- **EVENT**: Peristiwa sejarah/spesifik (misal: *D-Day, Normandy landings, Apollo 11, Macworld 2007*)
- **BUILDING / LANDMARK**: Bangunan atau cagar budaya (misal: *Candi Prambanan, Gedung Sate, Monas, Berlin Wall*)
- **PRODUCT / OBJECT**: Produk atau artefak nyata (misal: *iPhone, IBM PC, Model T, B-29 Enola Gay*)
- **COMPANY / ORGANIZATION**: Lembaga atau perusahaan (misal: *Apple, Ford, Allied forces, VOC*)
- **HISTORICAL_PERIOD / DATE**: Dimensi waktu (misal: *1944, 6 Juni 1944, abad ke-20, era kolonial*)
- **STATISTIC**: Angka, persentase, rasio data

### Aturan Baku Pemeliharaan Entitas (Entity Preservation Rule):
Untuk kelas `REAL_REQUIRED` dan `REAL_PREFERRED`:
- **DILARANG KERAS** memperluas query (*broadening*) yang menghapus kata kunci entitas utama.
- ❌ **SALAH**: `"Steve Jobs iPhone 2007"` $\rightarrow$ `"businessman presentation"`, `"technology smartphone"`.
- ❌ **SALAH**: `"D-Day Normandy 1944"` $\rightarrow$ `"soldiers beach"`, `"war soldiers"`.
- ✅ **BENAR**: `"Steve Jobs iPhone 2007"` $\rightarrow$ `"Steve Jobs iPhone 2007 keynote"`, `"Apple iPhone 2007 Macworld keynote"`.
- ✅ **BENAR**: `"D-Day Normandy 1944"` $\rightarrow$ `"Normandy landings 6 June 1944 archival"`, `"D-Day Allied landing Normandy 1944 footage"`.

---

## 3. Matriks Perutean Penyedia Media (*Provider Routing Matrix*)

Penyedia media dipilih secara selektif berdasarkan kelas visual, era, dan format media:

```
[SCRIPT INPUT]
       │
       ▼
[Klasifikasi Kebutuhan Visual]
  ├── NO_BROLL ─────────────► Selesai (status: NO_BROLL, 0 queries)
  ├── REMOTION_REQUIRED ────► Remotion Motion Spec (0 queries)
  └── [Pencarian Media Aktif]
        ├── REAL_REQUIRED + HISTORICAL + VIDEO:
        │     1. Internet Archive
        │     2. Wikimedia Commons
        │     (Pexafy: DISABLED)
        │
        ├── REAL_REQUIRED + HISTORICAL + IMAGE:
        │     1. Wikimedia Commons
        │     2. Internet Archive
        │     (Pexafy: DISABLED)
        │
        ├── REAL_REQUIRED + PRESENT + IMAGE:
        │     1. Wikimedia Commons
        │     2. Internet Archive
        │     (Pexafy: DISABLED)
        │
        ├── REAL_PREFERRED:
        │     1. Wikimedia Commons
        │     2. Internet Archive
        │     3. Pexafy (fallback kontekstual)
        │
        └── GENERIC_ALLOWED:
              1. Pexafy
              2. Wikimedia Commons
              3. Internet Archive
```

---

## 4. Skor Keaslian (*Authenticity Scoring*) & Gerbang Wajib (*Hard Gate*)

Untuk memisahkan antara konsep **Relevan** (*apakah topik nyambung secara semantik?*) dan **Autentik** (*apakah visual ini membuktikan objek nyata yang dibicarakan?*), `MediaRanker` menghitung skor gabungan:

$$\text{Authenticity Score} = 0.40 \cdot S_{\text{entity}} + 0.20 \cdot S_{\text{temporal}} + 0.20 \cdot S_{\text{event}} + 0.10 \cdot S_{\text{location}} + 0.10 \cdot S_{\text{source\_specificity}}$$

### Komponen Penilaian:
1. **$S_{\text{entity}}$ (Entity Match Score)**: Kecocokan nama tokoh, institusi, produk, atau peristiwa di dalam judul/deskripsi media.
2. **$S_{\text{temporal}}$ (Temporal Match Score)**: Kesesuaian tahun atau dekade (misal: "1944" atau "2007").
3. **$S_{\text{location}}$ (Location Match Score)**: Keselarasan kota, wilayah, atau negara.
4. **$S_{\text{event}}$ (Event Match Score)**: Penyebutan kata kunci peristiwa penting (*D-Day, landing, keynote*).
5. **$S_{\text{source\_specificity}}$**: Bobot kredibilitas repositori arsip (Internet Archive dan Wikimedia Commons mendapatkan skor spesifisitas arsip tinggi; stock generik rendah).

### Gerbang Wajib (*Hard Gate Rule*) untuk `REAL_REQUIRED`:
Kandidat yang tidak lolos batas minimal keaslian akan **DITOLAK SECARA MUTLAK (`rejection_reason`)**, meskipun memiliki skor kemiripan embedding atau reranker yang tinggi:
- Jika kandidat tidak mencakup entitas kunci ($S_{\text{entity}} < 0.35$), kandidat ditolak.
- Jika skor keaslian total rendah ($\text{authenticity\_score} < 0.35$), kandidat ditolak.
- Kandidat stok generik murni yang tidak memiliki kecocokan entitas otomatis ditolak.

---

## 5. Perilaku Kegagalan Bukti (*Fallback & Insufficient Evidence*)

Jika pada kelas `REAL_REQUIRED` tidak ada kandidat yang berhasil menembus Gerbang Keaslian:
- Sistem **TIDAK AKAN** secara diam-diam beralih ke stock footage generik atau berpura-pura menemukan bukti.
- Sistem mengembalikan status:
  ```json
  {
    "visual_requirement": "REAL_REQUIRED",
    "status": "INSUFFICIENT_EVIDENCE",
    "search_completed": true,
    "usable_results": 0,
    "fallback_allowed": false
  }
  ```
- Di antarmuka CLI atau pratinjau editor ditampilkan peringatan jelas:
  ```text
  ⚠ REAL EVIDENCE NOT FOUND (0 USABLE AUTHENTIC CANDIDATES)
  ```
  sehingga editor video mengetahui bahwa aset bukti sejarah ini perlu dicari atau disediakan secara manual.

---

## 6. Format Metadata & Penamaan Berkas Bukti (*File Naming*)

Aset yang berhasil diverifikasi dan diunduh diberi nama berkas terstruktur yang mencerminkan status pembuktian:

```text
assets/media/normandy_1944/
├── 001_REAL_REQUIRED_D-Day-Normandy-Landing-1944.mp4
├── 002_REAL_REQUIRED_Normandy-Landing-6-June-1944-Archival.mp4
└── sources.json
```

Di dalam berkas `sources.json`, tersimpan rekaman audit bukti lengkap:
```json
{
  "file": "001_REAL_REQUIRED_D-Day-Normandy-Landing-1944.mp4",
  "provider": "internet_archive",
  "media_type": "video",
  "visual_requirement": "REAL_REQUIRED",
  "source_role": "PRIMARY_EVIDENCE",
  "authenticity_score": 0.94,
  "entity_match_score": 0.98,
  "event_match_score": 0.97,
  "temporal_match_score": 0.96,
  "matched_entities": ["D-Day", "Normandy", "1944"],
  "source_url": "https://archive.org/details/...",
  "license": "Public Domain"
}
```

---

## 7. Penggunaan CLI

Gunakan opsi `--visual-requirement` atau `--vr` pada sub-perintah `media-find`:

```powershell
# Pencarian bukti sejarah D-Day (REAL_REQUIRED)
python -m engine.pipeline.engine_cli media-find \
  --query "D-Day pendaratan Normandia 1944" \
  --vr REAL_REQUIRED \
  --era historical \
  --media video

# Pencarian visual atmosfer perkotaan (GENERIC_ALLOWED)
python -m engine.pipeline.engine_cli media-find \
  --query "pagi hari suasana kota ramai" \
  --vr GENERIC_ALLOWED \
  --media video

# Mode otomatis (sistem menganalisis kalimat naskah secara otonom)
python -m engine.pipeline.engine_cli media-find \
  --query "Steve Jobs meluncurkan iPhone tahun 2007" \
  --vr auto
```

---

## 8. Human Alignment Scoring

Untuk scene yang tidak memerlukan bukti entitas historis tetapi membutuhkan konteks kehidupan manusia, Human Alignment Score ikut memengaruhi ranking kandidat.

Komponen:

    Human Alignment
    = 35% Human Basic Need
    + 20% Life Lens
    + 25% Everyday Relevance
    + 20% Human–Place Relevance

Interpretasi:
- 0.80–1.00: sangat selaras dengan pengalaman manusia dan konteks tempat.
- 0.60–0.79: cukup kuat.
- 0.40–0.59: relevansi parsial; masih dapat dipakai bila visualnya paling tepat.
- <0.40: lemah untuk scene yang memang membutuhkan human-life context.

Authenticity/evidence tetap menjadi gate utama untuk REAL_REQUIRED. Human alignment tidak boleh menggantikan bukti.
