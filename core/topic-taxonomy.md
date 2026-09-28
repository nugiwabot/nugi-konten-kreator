# Topic Taxonomy: Nugi Editorial Intelligence

Dokumen ini mendefinisikan taksonomi resmi klasifikasi topik dan skema metadata wajib untuk setiap ide konten dalam engine Nugi.

---

## 1. Skema Metadata Topik (Topic Metadata Schema)

Setiap ide topik yang dihasilkan atau dievaluasi oleh sistem wajib memiliki metadata terstruktur berikut:

```yaml
title: "Judul ide yang lugas dan memantik rasa ingin tahu"
one_line_premise: "Satu kalimat ringkas yang menjelaskan inti premis narasi"
primary_domain:
  - property
  - city
  - economy
  - ai
  - technology
  - work
  - human
  - history
  - future

anchor:
  - housing
  - land
  - city
  - space
  - work
  - ownership
  - mobility

lens:
  - economics
  - psychology
  - sociology
  - history
  - technology
  - business
  - urbanism
  - philosophy

research_mode:
  - evergreen
  - current
  - historical
  - data_driven

human_question: "Pertanyaan eksistensial tentang kehidupan nyata manusia"
why_question: "Pertanyaan penyelidikan struktural/psikologis di balik fenomena"
property_connection: "Rantai kausal logis yang menghubungkan topik dengan ruang/properti"
```

---

## 2. Definisi Domain Utama (Primary Domains)

1. **`property`**: Hunian, tanah, perumahan rakyat, pengembang, perizinan, dan pasar fisik bangunan.
2. **`city`**: Tata kota, aglomerasi perkotaan, fasilitas publik, polusi, kemacetan, dan pusat pertumbuhan baru.
3. **`economy`**: Inflasi, daya beli, tingkat suku bunga, disparitas pendapatan, pasar modal, dan produktivitas nasional.
4. **`ai`**: Algoritma cerdas, automasi penalaran, model bahasa, robotika, dan agen otonom.
5. **`technology`**: Infrastruktur internet, komputasi awan, transportasi cerdas, material bangunan baru, dan energi.
6. **`work`**: Cara manusia mencari nafkah, jam kerja, remote work, hierarki kantor, dan alienasi pekerja.
7. **`human`**: Kebutuhan psikologis dasar (rasa aman, status, identitas, kebersamaan, keluarga).
8. **`history`**: Asal-usul tata ruang zaman kolonial, evolusi hukum tanah, dan lintasan sejarah kota.
9. **`future`**: Proyeksi demografi, pergeseran generasi, dan skenario masa depan ruang hidup manusia.

---

## 3. Definisi Anchor Ruang Fisik (Anchors)

- **`housing`**: Rumah tempat tinggal (tapak, vertikal, sewa, milik).
- **`land`**: Tanah sebagai sumber daya alam terbatas yang tidak dapat diperbanyak.
- **`city`**: Ekosistem perkotaan dan dinamika masyarakat perkotaan.
- **`space`**: Ruang fisik (ruang publik, ruang privat, batas privasi vs komunal).
- **`work`**: Lingkungan dan wadah tempat aktivitas produktif berlangsung.
- **`ownership`**: Konsep hukum dan emosional kepemilikan aset riil vs sewa/akses.
- **`mobility`**: Aksesibilitas, komuter harian, jalan tol, kereta api, dan jaringan transportasi.

---

## 4. Definisi Lensa Analisis (Lenses)

- **`economics`**: Insentif finansial, supply & demand, struktur pasar, dan perputaran modal.
- **`psychology`**: Bias kognitif, ketakutan, kebutuhan status sosial, dan rasa aman.
- **`sociology`**: Stratifikasi kelas, relasi tetangga, modal sosial, dan segregasi wilayah.
- **`history`**: Preseden masa lalu, warisan hukum kolonial, dan lintasan waktu.
- **`technology`**: Efisiensi proses, disrupsi alat baru, dan desentralisasi data.
- **`business`**: Model bisnis korporasi, strategi pengembang, dan insentif industri.
- **`urbanism`**: Rancang kota, kepadatan, zonasi, dan daya dukung lingkungan.
- **`philosophy`**: Makna hidup, otonomi manusia, kebebasan, dan relasi manusia dengan alam.

---

## 5. Mode Riset (Research Modes)

- **`evergreen`**: Pertanyaan abadi tanpa tenggat waktu (misal: *"Kenapa harga tanah selalu naik?"*).
- **`current`**: Respon mendalam terhadap regulasi, berita, atau peristiwa hangat yang sedang bergulir.
- **`historical`**: Membedah lintasan sejarah dan asal-usul (misal: *"Bagaimana Menteng dirancang?"*).
- **`data_driven`**: Berangkat dari anomali data empiris (misal: *"Gaji naik 4%, harga rumah naik 18%"*).
