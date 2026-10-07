# Panduan Motion Template Nugi

Library ini memakai prinsip **template = kode visual** dan **content = data**. Pilih Composition atau MCP template, lalu ubah `data`, `preset`, `layout`, `animation`, dan durasi. Isi video tidak perlu diganti dengan mengedit TSX.

## Arah visual dan design tokens

Warna diambil dari frame contoh `transisi youtube.mp4`. Palet dominannya adalah kuning hangat `#F7E962`, emas `#DEA950`, oranye `#D27441`, dan koral `#C14E33`. Template memakai gradient lembut dan garis kurva transparan seperti transisi referensi, dengan typography tegas dan gerak yang tenang.

Semua warna, overlay, font stack, typography scale dasar, dan spacing tokens tersimpan di `design-tokens.json`. Untuk mengubah warna library, edit token `brand` di file itu. Jangan menaruh nilai warna baru di setiap template. Tidak ada file font brand khusus di repository; font memakai `Aptos`, `Segoe UI`, lalu fallback `Arial` yang tersedia lokal.

## Template yang tersedia

| Kategori | Template ID | Kegunaan |
|---|---|---|
| Branding | `intro-bumper` | Nama channel dan tagline |
| Branding | `logo-reveal` | Reveal logo atau wordmark |
| Branding | `minimal-intro` | Pembuka sederhana berbasis tipografi |
| Documentary | `title-card` | Judul, subtitle, eyebrow, dan gambar opsional |
| Documentary | `chapter-title` | Nomor dan judul bab |
| Documentary | `documentary-text` | Kalimat naratif di atas latar atau gambar |
| Editorial | `headline` | Headline, kategori, dan dek |
| Informasi | `statistic` | Angka, label, deskripsi, dan sumber |
| Informasi | `fact-card` | Fakta, konteks, dan atribusi |
| Informasi | `quote-card` | Kutipan dan sumber |
| Informasi | `timeline` | Peristiwa dalam urutan waktu |
| Informasi | `number-counter` | Angka yang bergerak menuju nilainya |
| Media | `image-reveal` | Foto dengan mask reveal dan teks |
| Media | `image-focus` | Gambar/video layar penuh dengan slow zoom |
| Media | `photo-sequence` | Urutan foto dan caption |
| Editorial | `split-screen` | Visual dan copy berdampingan |
| Branding | `lower-third` | Nama, peran, atau sumber di bawah frame |
| Utility | `before-after` | Perbandingan dua keadaan |
| Utility | `progress-bar` | Penanda bab/progres cerita |
| Branding | `outro` | Penutup dan CTA ringan |

Setiap entri di `template-catalog.json` memuat Composition ID, deskripsi, kategori, durasi default, preset, input wajib/opsional, serta `defaultData` yang juga menjadi contoh preview realistis.

## Preset, motion, dan layout

Preset yang tersedia: `cinematic`, `documentary`, `editorial`, `minimal`, dan `energetic`. Preset mengubah latar, warna teks/aksen, tekstur, serta default motion. Template membatasi preset yang kurang cocok agar kombinasi tetap terjaga.

Motion memakai bahasa visual editorial yang sama: gerak terkontrol, easing terpusat, jarak kecil, stagger bertingkat, dan cukup ruang untuk membaca. Token durasi, easing, jarak, skala, stagger, serta profil per preset tinggal di `design-tokens.json`. Profil cinematic lebih lambat, documentary terukur, editorial presisi, minimal nyaris diam, dan energetic lebih cepat tanpa gerak flashy.

Animasi yang dapat dipilih: `fade`, `fade-up`, `fade-down`, `fade-left`, `fade-right`, `slide-in`, `mask-reveal`, `clip-reveal`, `word-stagger`, `character-stagger`, `line-stagger`, `tracking-reveal`, `scale-reveal`, `wipe`, `slide`, `parallax`, `slow-zoom`, `horizontal-drift`, `vertical-drift`, `counter`, dan `stagger`. Jika `animation` tidak diisi, preset mengatur pacing serta default motion. Copy memakai hierarchy eyebrow → headline → subtitle → accent; garis aksen tumbuh pelan. Scene di bawah 2,5 detik tidak dipaksa fade-out agar informasi mendapat waktu hold.

| Layout | Ukuran default |
|---|---:|
| `landscape` | 1920 × 1080 (16:9) |
| `portrait` | 1080 × 1920 (9:16) |
| `square` | 1080 × 1080 (1:1) |

Satu template dipakai di seluruh rasio. Komposisi membaca `width` dan `height` Remotion untuk menyesuaikan skala tipografi, arah layout, dan safe margin. Untuk gambar/video lokal, render MCP menyalin media sementara ke `public/`, lalu membersihkannya setelah render. Tidak ada upload atau pengambilan font/model dari cloud.

## Remotion Studio dan gallery

Di terminal pada folder `remotion-app`:

```powershell
npm run dev
```

Studio menampilkan Composition lama `TitleCard`, Composition individual dengan prefix `Nugi-`, `Nugi-MasterSequence`, dan `Nugi-TemplateGallery`. Untuk membuat contact sheet satu frame dari seluruh template:

```powershell
npm run gallery
```

File gallery dibuat di `output/template-gallery.png`. MCP juga menyediakan `remotion_render_template_gallery`.

## Render template dari MCP atau JSON

Contoh input MCP `remotion_render_template`:

```json
{
  "template": "title-card",
  "preset": "documentary",
  "layout": "landscape",
  "animation": "mask-reveal",
  "duration_seconds": 6,
  "data": {
    "eyebrow": "HISTORY OF HOME",
    "title": "Kenapa Manusia Membutuhkan Rumah?",
    "subtitle": "Dari gua sampai megacity"
  }
}
```

Untuk media lokal, tambahkan path pada `data.image`, `data.video`, `data.logo`, `data.images`, `data.imageBefore`, atau `data.imageAfter`. Media memakai `fit: "cover"` secara default; pilih `"contain"` untuk menampilkan seluruh gambar tanpa crop. `position` menerima `center`, `top`, `bottom`, `left`, atau `right` untuk mengatur titik crop. Pada `split-screen`, `position` mengatur sisi teks, sedangkan `mediaPosition` mengatur crop gambar.

Tool template lainnya:

- `remotion_list_templates` mengembalikan daftar template, preset, layout, animation, Composition ID, dan contoh data.
- `remotion_template_schema` mengembalikan input wajib/opsional dan preset yang didukung untuk satu template.
- `remotion_render_master` merender urutan beberapa scene. `duration` atau `durationInFrames` pada setiap scene berarti jumlah frame.
- `remotion_render_template_gallery` menghasilkan contact sheet PNG.

Contoh master sequence:

```json
{
  "video": {"layout": "landscape", "fps": 30},
  "scenes": [
    {"template": "intro-bumper", "preset": "cinematic", "duration": 90,
     "data": {"title": "NUGI", "subtitle": "HUMAN × PLACE × WHY"}},
    {"template": "title-card", "preset": "documentary", "duration": 180,
     "data": {"title": "Sejarah Rumah Manusia", "subtitle": "Dari gua sampai megacity"}},
    {"template": "statistic", "preset": "editorial", "duration": 150,
     "data": {"number": "68%", "label": "populasi dunia tinggal di perkotaan", "source": "World Bank"}}
  ]
}
```

## Cara menambah template atau preset

1. Tambahkan metadata, schema, preset yang diizinkan, durasi dan `defaultData` ke `template-catalog.json`.
2. Tambahkan satu branch visual pada `TemplateScene` di `src/templates/TemplateComposition.tsx`, dengan memakai `Copy`, `MediaPanel`, `AccentRule`, token brand, dan `enterStyle` yang sudah tersedia.
3. Tambahkan `required` fields yang memang dibutuhkan. Registry otomatis mendaftarkan Composition, MCP schema, dan gallery entry.
4. Jalankan `npm exec -- tsc --noEmit`, `npm run compositions -- --quiet`, lalu `npm run gallery` untuk memeriksa semua cabang template.
5. Render template melalui `remotion_render_template` untuk menguji data dinamis dan layout target.

Preset baru ditambahkan pada `presetTokens` di `src/theme/brand.ts`, kemudian namanya ditambahkan ke katalog JSON dan ke template yang mendukungnya. Warna baru tetap didefinisikan hanya di `design-tokens.json`.
