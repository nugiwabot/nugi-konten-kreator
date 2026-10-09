# Creator-Led Research Workflow

## Tujuan

Workflow ini dibuat agar AI menyiapkan bahan riset dan outline cerita untuk video YouTube, sedangkan Nugi menulis sendiri script teleprompter-nya. Tujuannya bukan hanya menghasilkan video, tetapi juga melatih kemampuan riset, memahami topik, menyusun narasi, dan berbicara natural.

## Batas kerja yang wajib dijaga

- AI boleh membantu discovery topik, riset, verifikasi fakta, memahami konsep, menyusun kronologi, menguji alur cerita, dan membuat outline.
- AI tidak boleh menulis script teleprompter lengkap, paragraf narasi siap baca, intro siap baca, atau kesimpulan siap baca sebagai output default.
- Output akhir AI adalah **research brief + source links + story outline**, bukan script.
- Nugi membaca sumber, memastikan pemahaman, lalu menulis narasi dengan kata-katanya sendiri.
- AI boleh membantu menjelaskan bagian riset yang sulit atau memberi kritik pada outline. Jika diminta mengedit kalimat tertentu, bantu bagian itu saja; jangan mengambil alih seluruh script.
- Jangan menambah agent, dependency, database, service, atau kode baru hanya untuk menerapkan workflow ini.
- Jangan mengubah pipeline, konfigurasi, atau kode produksi tanpa permintaan eksplisit.
- Jangan menjalankan pipeline end-to-end yang menghasilkan script untuk permintaan yang hanya membutuhkan riset dan outline.

## Alur kerja

### 1. Discovery

Temukan ide dan pertanyaan yang menarik serta cocok dengan arah editorial Nugi: HUMAN × PLACE × CHANGE × WHY. Properti adalah salah satu anchor, bukan topik wajib untuk semua video.

Untuk setiap kandidat, jelaskan:
- Topik dan pertanyaan utama.
- Mengapa topik menarik atau relevan.
- Cerita atau pertanyaan yang bisa ditelusuri.
- Ketersediaan sumber yang layak.
- Hal yang masih perlu diverifikasi.

### 2. Research

Cari sumber asli dan sumber sekunder yang kredibel. Prioritaskan dokumen primer, data resmi, penelitian akademik, laporan institusi, wawancara langsung, dan media tepercaya sesuai topiknya.

Untuk setiap sumber, sertakan:
- Judul.
- Penerbit/penulis dan tanggal, jika tersedia.
- Tautan langsung yang bisa dibuka.
- Ringkasan singkat tentang informasi yang relevan.
- Klaim atau bagian cerita yang didukung sumber.
- Batasan sumber, jika ada.

Bedakan dengan jelas:
- **Terverifikasi:** didukung sumber yang dapat diperiksa.
- **Perlu verifikasi:** petunjuk awal yang belum cukup kuat.
- **Diperdebatkan/tidak pasti:** ada ketidakpastian atau sumber yang berbeda.

Jangan mengarang tautan, kutipan, angka, kronologi, atau detail. Hasil pencarian, cuplikan mesin pencari, dan abstrak saja tidak otomatis menjadi bukti final. Buka sumber aslinya jika memungkinkan. Jika akses tidak tersedia, nyatakan keterbatasannya.

### 3. Memahami topik dan membangun storyline

Susun cerita berdasarkan bukti, bukan memaksakan fakta agar cocok dengan narasi dramatis. Pilih struktur yang paling alami, misalnya:
- Origin: bagaimana sesuatu bermula.
- Transformation: bagaimana keadaan berubah.
- Hidden system: mekanisme yang tidak terlihat.
- Contradiction: mengapa kenyataan berbeda dari dugaan.
- Human dilemma: pilihan dan konsekuensi yang dihadapi manusia.
- Place: mengapa sebuah tempat berkembang seperti itu.
- Evolution: perubahan sepanjang waktu.
- Future: skenario masa depan yang dibedakan dari fakta saat ini.

Tidak semua cerita harus punya konflik, tokoh antagonis, atau kejutan. Jangan menciptakan drama jika bukti tidak mendukungnya.

### 4. Menyusun outline cerita

Buat outline yang membantu Nugi menulis sendiri, bukan narasi siap baca. Struktur default yang bisa disesuaikan:

1. **Hook / pertanyaan pembuka:** fenomena, pertanyaan, atau fakta yang membuat penasaran.
2. **Konteks:** apa yang perlu diketahui penonton agar memahami cerita.
3. **Awal cerita / kronologi:** bagaimana situasi terbentuk.
4. **Perkembangan:** peristiwa, data, tokoh, atau perubahan penting.
5. **Penjelasan inti:** mekanisme dan hubungan sebab-akibat yang didukung bukti.
6. **Kompleksitas:** bukti yang berbeda, sanggahan, keterbatasan, atau hal yang belum diketahui.
7. **Jawaban sementara / kesimpulan:** apa yang bisa disimpulkan secara bertanggung jawab.
8. **Referensi per bagian:** tautan sumber untuk memeriksa klaim pada bagian tersebut.

Untuk setiap bagian outline, sertakan:
- Tujuan bagian dalam cerita.
- Poin yang perlu dijelaskan.
- Fakta atau pertanyaan pendukung.
- Link sumber yang relevan.
- Catatan yang perlu dibaca atau diverifikasi oleh Nugi.

Jangan mengisi outline dengan kalimat narasi lengkap. Gunakan bullet points, fakta, pertanyaan, dan catatan penjelasan.

### 5. Handoff kepada Nugi

Akhiri output dengan:
- Pertanyaan utama video.
- Satu paragraf ringkas tentang temuan riset (bukan narasi video).
- Outline final.
- Daftar sumber prioritas untuk dibaca, urut dari yang paling penting.
- Daftar fakta yang masih belum pasti atau perlu dicek.
- Perkiraan bagian yang paling membutuhkan pemahaman tambahan.

Setelah itu, Nugi menulis script teleprompter sendiri.

## Format output standar

# Research Brief
- Topik:
- Pertanyaan utama:
- Mengapa menarik:
- Batasan ruang lingkup:

# Temuan Utama
- Temuan + penjelasan + sumber.

# Kronologi / Mekanisme
- Urutan kejadian atau penjelasan sebab-akibat dengan sumber.

# Storyline yang Disarankan
- Struktur cerita dan alasan memilih struktur tersebut.

# Outline Video
Untuk setiap bagian: tujuan, poin-poin, sumber terkait, dan hal yang perlu dijelaskan Nugi sendiri.

# Sumber untuk Dibaca
- Judul — penerbit/tanggal — tautan — apa yang perlu dibaca.

# Hal yang Belum Pasti
- Klaim, pertanyaan, atau detail yang belum cukup terverifikasi.

# Handoff
- Pengingat bahwa script teleprompter ditulis oleh Nugi; jangan hasilkan script kecuali diminta secara eksplisit.

## Quality checklist

Sebelum menyerahkan hasil, pastikan:
- [ ] Pertanyaan utama video jelas.
- [ ] Cerita dibangun dari sumber, bukan spekulasi.
- [ ] Klaim penting memiliki tautan sumber yang relevan.
- [ ] Fakta dipisahkan dari interpretasi dan ketidakpastian.
- [ ] Kronologi dan sebab-akibat tidak disimpulkan tanpa dukungan.
- [ ] Outline punya alur yang logis dan cukup detail untuk ditulis sendiri.
- [ ] Output tidak berubah menjadi script teleprompter.
- [ ] Tidak ada kode, dependency, agent, atau arsitektur baru yang dibuat hanya untuk workflow ini.
