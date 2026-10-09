# Creator-Led Research Workflow

> **Konteks penggunaan:** dokumen ini adalah panduan utama ketika bekerja di repository GitHub `nugiwabot/nugi-konten-kreator` melalui Nugi Konten Kreator MCP atau lingkungan kerja yang terhubung dengannya. Gunakan repository sebagai sumber kebenaran untuk skill, tool, dan aturan teknis. Instruksi ini tidak membuat tool baru dan tidak mengubah perilaku kode produksi.

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

## Menggunakan Tools MCP dan Infrastruktur yang Sudah Ada

Repository ini sudah memiliki Nugi Konten Kreator MCP dan komponen riset/retrieval. Saat MCP tersebut benar-benar tersedia di sesi kerja, **panggil tools yang relevan secara langsung**; jangan hanya membaca dokumentasinya, menyebut nama tool, atau meniru hasilnya secara manual.

Nama di bawah adalah nama tool yang terdokumentasi pada repository. Daftar tool yang benar-benar terhubung di sesi saat ini tetap menjadi acuan. Jika tool tidak tersedia atau pemanggilannya gagal, jangan mengaku sudah menjalankannya. Jelaskan batasannya dan lanjutkan dengan alternatif yang tersedia.

### Urutan pemanfaatan yang disarankan

1. **Pahami repository dan hindari topik berulang.** Gunakan `nugi_repo_tree`, `nugi_repo_read`, `nugi_repo_find`, dan/atau `nugi_repo_search` untuk membaca skill, dokumentasi editorial, serta daftar script/topik lama yang relevan. Gunakan `nugi_repo_status` hanya bila status workspace perlu diketahui. Jangan membaca atau memindai seluruh repository tanpa alasan; fokus pada file yang diperlukan.
2. **Discovery topik.** Jika pengguna belum menentukan topik, gunakan `nugi_idea_discover(count=...)` untuk memperoleh peluang konten terurut dari sumber intelijen yang tersedia. Tool ini merupakan discovery awal dengan sinyal RSS/berita dan pemeriksaan bukti terbatas. Perlakukan hasilnya sebagai kandidat, bukan fakta final. Perluas dengan pencarian web aktual jika tersedia.
3. **Rencanakan permintaan bila perlu.** Gunakan `nugi_request_plan(request=...)` untuk memeriksa bagaimana permintaan natural-language diklasifikasikan sebelum memilih langkah kerja, terutama jika ada risiko permintaan riset dianggap sebagai produksi konten.
4. **Riset mendalam untuk kandidat terpilih.** Gunakan `nugi_research_deep(topic=..., recency=..., max_evidence=..., depth=...)` jika tool ini tersedia. Pilih recency sesuai pertanyaan: `w` untuk perkembangan sekitar satu minggu, `m` untuk sekitar satu bulan, dan `all` untuk topik evergreen atau historis. Jangan menganggap dossier otomatis membuktikan semua klaim; periksa sumber, tanggal, cakupan bukti, dan kontradiksinya. Tool ini dapat menyimpan dossier ke folder output repository; gunakan lokasi output yang aman dan jangan menimpa artefak pengguna tanpa alasan.
5. **Retrieval pengetahuan permanen.** Gunakan `nugi_knowledge_retrieve(query=..., top_k=...)` ketika perlu mengambil framework storytelling, pengetahuan editorial, psikologi/perilaku, atau referensi permanen yang tersimpan. Tool ini dirancang untuk vector search yang dilanjutkan precision reranking. Bila perlu memeriksa kesiapan index, gunakan `nugi_knowledge_index_status()`. Retrieval bukan pengganti riset web dan bukan sumber untuk memverifikasi berita terbaru.
6. **Klasifikasi editorial atau question mining bila relevan.** `nugi_editorial_classify_topic(topic=...)` dapat membantu menilai domain/anchor/lensa editorial, tetapi jangan memaksakan koneksi properti jika tidak alami. Gunakan `nugi_question_mine` hanya jika tugasnya memang menambang pertanyaan dari dataset yang sudah tersedia; periksa file dan kontrak tool terlebih dahulu, jangan mengarang atau membuat dataset baru hanya untuk memanggilnya.

### Batasan teknis yang wajib ditaati

- Sesuai `retrieval/embedding.md`, embedding internal **hanya untuk permanent knowledge retrieval**, bukan untuk mencari berita atau perkembangan terkini. Topik aktual harus ditelusuri melalui Runtime Web Research/pencarian web.
- Ikuti abstraksi provider dan konfigurasi yang sudah ada. Jangan memanggil endpoint lokal secara manual, mengganti URL/model, mengubah `.env`, melakukan reindex, atau mengubah index tanpa kebutuhan yang jelas dan izin yang sesuai.
- Ikuti `retrieval/reranking.md` dan `docs/LOCAL_AI_INFRASTRUCTURE.md`. Jangan menganggap embedding/reranker aktif hanya karena dokumentasinya ada. Jika layanan gagal atau menolak fallback, catat keterbatasannya; jangan menyatakan retrieval dua tahap berhasil jika tidak.
- `nugi_content_create` adalah entry point produksi dan dapat menghasilkan script serta artefak produksi. **Jangan gunakan untuk tugas research-brief dan outline saja.** Utamakan tool MCP terfokus seperti `nugi_idea_discover` dan `nugi_research_deep`.
- `nugi_research_fact_check` ditujukan untuk mengaudit script/narasi terhadap bukti. Jangan membuat script hanya agar tool itu bisa dipakai; gunakan hanya ketika pengguna memberikan script atau memang meminta audit naskah.
- Periksa kontrak input dan output tool sebelum pemanggilan bila belum jelas. Jangan memanggil tool yang tidak cocok hanya demi memakai sebanyak mungkin tools. Gunakan hanya yang menambah nilai untuk tugas.
- Jangan menjalankan CLI, end-to-end pipeline, atau tools produksi sebagai pengganti tool riset terfokus ketika hal itu tidak diperlukan. Jika MCP tidak terhubung tetapi akses terminal memang tersedia dan dibutuhkan, rujuk `docs/CLI_REFERENCE.md` dan laporkan dengan jelas metode yang benar-benar digunakan.
- Tool calls, retrieval, dan hasil search harus dipisahkan dari verifikasi faktual. Tetap buka dan periksa sumber asli jika memungkinkan, cari bukti pembanding, dan jelaskan ketidakpastian.

## Alur kerja

### 1. Discovery

Temukan ide dan pertanyaan yang menarik serta cocok dengan arah editorial Nugi: HUMAN × PLACE × CHANGE × WHY. Properti adalah salah satu anchor, bukan topik wajib untuk semua video.

Untuk discovery tanpa topik spesifik, prioritaskan pemanggilan `nugi_idea_discover` jika tersedia, lalu telusuri kandidat terbaik menggunakan pencarian web/Runtime Web Research dan skill discovery. Gunakan hasil MCP sebagai pintu masuk pencarian, bukan sebagai vonis kebenaran. Jika topik sudah ditentukan, lewati discovery umum yang tidak perlu dan langsung telusuri bukti. 

**Referensi wajib untuk discovery:** mulai dengan membaca dan menerapkan [skills/discover-phenomena.md](../skills/discover-phenomena.md). Skill ini adalah panduan utama untuk menghasilkan query pencarian yang fleksibel dan menemukan kasus nyata yang tidak biasa. Gunakan juga [skills/research-topic.md](../skills/research-topic.md) setelah kandidat dipilih, serta [skills/generate-ideas.md](../skills/generate-ideas.md) bila perlu memperluas sudut editorial. Jangan mengasumsikan ada skill terpisah bernama “Keyword Finder” jika file yang dimaksud tidak ditemukan; gunakan skill discovery yang benar-benar ada di repository ini.

#### Cara melakukan discovery agar selalu segar dan kreatif

- **Lakukan pencarian web aktual, bukan hanya brainstorming keyword.** Untuk topik berita dan fenomena terkini, cari berita/sumber yang baru diterbitkan dan periksa tanggal publikasi sekaligus tanggal kejadian. Gunakan rentang waktu yang sesuai (misalnya 7 hari, 30 hari, atau lebih lama bila topiknya berkembang perlahan). Jangan menyebut sesuatu “terbaru” tanpa memeriksa tanggal.
- **Mulai dari fenomena, bukan dari daftar keyword tetap.** Bentuk query berdasarkan temuan awal, lalu ubah arah pencarian mengikuti petunjuk baru yang muncul. Jangan mengulang template atau daftar kata kunci yang sama setiap sesi.
- **Jelajahi beberapa jalur secara paralel:** berita terkini; kejadian aneh atau langka; hasil yang bertentangan dengan dugaan umum; kegagalan dan keputusan dengan dampak tak terduga; penemuan ilmiah; perubahan kota/properti; perilaku manusia; bisnis dan ekonomi; AI/teknologi; sejarah yang baru mendapat bukti atau konteks baru; serta fenomena lokal Indonesia dan kasus internasional.
- **Kreatif dalam merangkai query.** Campurkan istilah lokal dan Inggris, lokasi, industri, periode, nama institusi, jenis kejadian, mekanisme, data, laporan investigasi, dan konsekuensi manusia. Buat beberapa jalur pencarian yang benar-benar berbeda—bukan sekadar mengganti satu kata dalam query yang sama.
- **Biarkan bukti mengubah keyword.** Setelah menemukan petunjuk, buat query lanjutan dari nama orang/tempat/lembaga, tanggal, dokumen, istilah teknis, angka, penjelasan alternatif, atau akibat yang disebut sumber. Cari juga kata kunci yang dapat membantah dugaan awal.
- **Jangan terlalu deterministik terhadap niche.** HUMAN × PLACE × CHANGE × WHY adalah kompas editorial, bukan pagar sempit. Mulai dari fenomena unik lintas bidang, lalu nilai apakah hubungannya dengan manusia, tempat, perubahan, properti, kota, bisnis, teknologi, atau kehidupan sehari-hari memang alami. Jangan memaksakan hubungan properti pada semua topik.
- **Campurkan topik fresh dan evergreen secara sadar.** Utamakan berita terbaru ketika ada perkembangan yang relevan, tetapi jangan mengabaikan fenomena lama, arsip, kasus historis, atau pertanyaan fundamental yang kembali relevan karena peristiwa baru. Bedakan jelas berita aktual dari kisah lama yang kembali ramai.
- **Hindari pengulangan.** Bandingkan kandidat dengan daftar topik/script yang sudah ada jika tersedia. Jangan hanya mengganti judul atau keyword untuk mengulang kasus yang sama; pertahankan topik serupa hanya jika ada bukti baru, sudut investigasi baru, atau pertanyaan yang berbeda.
- **Validasi kandidat sebelum merekomendasikan.** Hasil search, headline, cuplikan pencarian, dan posting viral hanyalah petunjuk. Buka sumbernya, cek tanggal dan konteks, cari sumber independen/primer, dan beri label “belum terverifikasi” jika bukti belum cukup. Jangan mengarang berita, kejadian, tautan, atau klaim.
- **Pilih karena ada cerita yang bisa diselidiki, bukan karena terdengar aneh.** Cari pertanyaan yang jelas, mekanisme atau sebab-akibat yang mungkin ditelusuri, kronologi, bukti, kontradiksi, dan dampak manusia. Jangan membuat judul sensasional yang tidak ditopang sumber.

Untuk setiap kandidat, jelaskan:
- Topik dan pertanyaan utama.
- Mengapa topik menarik atau relevan.
- Apakah ini berita/kejadian baru, perkembangan terbaru dari kasus lama, atau topik evergreen/historis.
- Tanggal kejadian dan tanggal publikasi sumber jika tersedia.
- Cerita atau pertanyaan yang bisa ditelusuri.
- Ketersediaan sumber yang layak.
- Hal yang masih perlu diverifikasi.
- Query lanjutan yang muncul dari temuan awal, bukan hanya query template.
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
