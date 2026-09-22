# Retrieval: Precision Reranking Architecture

## 1. Peran & Alur 2-Stage Retrieval
Pencarian vektor murni (*dense vector search*) unggul dalam menemukan dokumen yang berada di wilayah semantik yang mirip, namun kerap gagal membedakan nuansa presisi konteks query.

Oleh karena itu, sistem menerapkan arsitektur **Two-Stage Retrieval**:

```text
QUERY INPUT
   │
   ▼
[ Stage 1: Vector Search ]
Embedding Query → Cosine Similarity → Top 15 - 20 Candidate Chunks
   │
   ▼
[ Stage 2: Cross-Encoder Rerank ]
Reranker (BGE-Reranker-v2-m3) menghitung interaksi token query-document secara silang
   │
   ▼
Top 3 - 5 Chunks Paling Presisi → Diinjeksikan ke Konteks LLM
```

---

## 2. Abstraksi Provider (`RerankerProvider`)
- **Default Lokal:** `http://127.0.0.1:8080/v1/rerank` (atau `http://localhost:8080/v1/rerank`).
- **Model Terverifikasi:** `bge-reranker-v2-m3-q8_0.gguf`.
- **Graceful Fallback:** Jika server reranker mati atau tidak merespons dalam waktu `RERANKER_TIMEOUT`, sistem secara otomatis mengembalikan kandidat hasil Stage 1 berdasarkan skor *cosine similarity* tanpa error.

---

## 3. Konfigurasi Environment (`.env`)
```bash
RERANKER_URL=http://127.0.0.1:8080/v1/rerank
RERANKER_TIMEOUT=10
```
