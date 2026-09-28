# ⚡ Local AI Infrastructure (LAN Deployment)

## 1. Authorized Endpoints

Untuk menjaga kedaulatan data (*data sovereignty*), kecepatan inferensi, dan efisiensi biaya, sistem Nugi Content Creator hanya menggunakan dua endpoint infrastruktur AI lokal pada jaringan area lokal (LAN):

| Layanan | Endpoint URL | Protokol & Tipe Model | Fungsi Utama |
| :--- | :--- | :--- | :--- |
| **Embedding Engine** | `http://192.168.0.114:1234/v1/embeddings` | OpenAI-compatible (LM Studio) | Vektorisasi teks, query semantik, klasterisasi pertanyaan |
| **Cross-Encoder Reranker** | `http://192.168.0.114:8080/v1/rerank` | TEI / BGE-Reranker-v2-m3 | Pemeringkatan presisi kandidat retrieval |

> [!IMPORTANT]
> **NO UNAPPROVED EXTERNAL SERVICES:**  
> Dilarang menambahkan dependensi runtime atau endpoint eksternal di luar provider resmi yang telah dikonfigurasikan melalui abstraksi `.env`.

---

## 2. Konfigurasi Lingkungan (`.env`)

```env
# ---------------------------------------------------------------------------
# LOCAL AI INFRASTRUCTURE
# ---------------------------------------------------------------------------
EMBEDDING_URL=http://192.168.0.114:1234/v1/embeddings
EMBEDDING_MODEL=Qwen3-Embedding-4B-Q4_K_M.gguf
EMBEDDING_REQUIRED=true

RERANKER_URL=http://192.168.0.114:8080/v1/rerank
RERANKER_REQUIRED=true

# Mode Keamanan Produksi
# False = Fail-fast saat endpoint offline pada mode operasional
# True  = Izinkan fallback deterministik SHA-256 (hanya untuk pengujian unit lokal)
ALLOW_FALLBACK=false
```

---

## 3. Fitur Keandalan & Guardrails

1. **Dimension Mismatch Guard:**
   Retriever secara otomatis memverifikasi dimensi embedding antara index corpus tersimpan dan model aktif. Jika terdeteksi ketidakcocokan (misal index 128-dim vs model 1024-dim), sistem memberikan peringatan jelas dan mengisolasi index yang kompatibel.
2. **Deterministic Offline Fallback:**
   Saat menjalankan automated testing tanpa akses ke LAN (misal di lingkungan CI/CD), sistem menyediakan `FallbackEmbeddingProvider` (berbasis SHA-256 hashing terdistribusi) dan `FallbackRerankerProvider` (berbasis keyword overlap scoring) sehingga pipeline tetap 100% testable secara offline.
3. **Fail-Fast Policy:**
   Dalam mode produksi (`ALLOW_FALLBACK=false`), jika salah satu server LAN tidak merespons, engine langsung melaporkan galat koneksi secara tegas daripada menghasilkan rekomendasi semu yang tidak akurat.
