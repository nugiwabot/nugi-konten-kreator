# Retrieval: Local Embedding Architecture

## 1. Peran & Tanggung Jawab
Embedding digunakan **HANYA untuk pencarian pengetahuan permanen (*permanent knowledge retrieval*)** di dalam repositori (prinsip pengaruh Cialdini, viralitas Berger, daya lekat Heath brothers, psikologi manusia, dan framework storytelling).

⚠️ **ATURAN MUTLAK:** Dilarang keras menggunakan embedding internal untuk mencari berita atau perkembangan terkini. Berita terkini wajib diambil dari **Runtime Web Research**.

---

## 2. Abstraksi Provider (`EmbeddingProvider`)
Untuk memastikan sistem tahan lama bertahun-tahun dan tidak terkunci (*vendor lock-in*), sistem menggunakan antarmuka generik:
- **Default Lokal:** LM Studio OpenAI-compatible endpoint (`http://localhost:1234/v1/embeddings`).
- **Model Terverifikasi:** `text-embedding-nomic-embed-text-v1.5` (768 dimensi).
- **Graceful Fallback:** Jika LM Studio offline, sistem secara otomatis beralih ke `FallbackEmbeddingProvider` (deterministic token-hash vector) tanpa memutus alur eksekusi aplikasi.

---

## 3. Konfigurasi Environment (`.env`)
```bash
EMBEDDING_URL=http://localhost:1234/v1/embeddings
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
EMBEDDING_TIMEOUT=10
```
