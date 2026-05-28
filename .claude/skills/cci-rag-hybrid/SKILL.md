---
name: cci-rag-hybrid
description: Use this skill whenever you implement, modify, or debug retrieval code in CCI/AVCS — anything that fetches chunks from Qdrant or BM25, fuses scores, reranks results, or filters by time. Trigger on files under services/retrieval/ or libs/cci-rag/, on file names like hybrid.py, reranker.py, temporal_filter.py, cache.py, on imports of qdrant_client, sentence_transformers, rank_bm25, cohere, on mentions of "hybrid search", "RRF", "reciprocal rank fusion", "BM25", "dense retrieval", "cross-encoder", "reranker", "top-K", "temporal filter", "Qdrant", "embedding". This skill ensures retrieval is hybrid, temporal-aware, and rerank-validated — never plain vector similarity, which is the single most common mistake in enterprise RAG.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS Hybrid RAG

L'errore numero uno nei RAG enterprise: cosine similarity da sola. Cosine similarity da sola **fallisce silenziosamente** quando la query contiene codici tecnici (ISO 27001, R001, IATF 16949) o numeri (importi, date) che le metriche semantiche non distinguono.

CCI/AVCS usa **sempre** la triade: dense + sparse + rerank, con filtro temporale obbligatorio.

## Architettura del retrieval

```
query  ───┬───►  Dense Encoder (all-MPNet)  ───►  Qdrant ANN  ──┐
          │                                                       ├──► RRF Fusion ──► Cross-Encoder Rerank ──► Temporal Filter ──► top-K
          └───►  Sparse BM25 (rank_bm25)    ───►  inverted idx ──┘
```

Tutti i path sono obbligatori. Niente "se mi va bene salto BM25". Niente "rerank solo per query premium".

## Modulo di riferimento

`libs/cci-rag/src/cci_rag/hybrid.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Sequence
import asyncio

from qdrant_client import AsyncQdrantClient, models as qm
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    domain: str
    temporal_window: tuple[date, date]  # ALWAYS required
    top_k: int = 8
    rerank_top_n: int = 24
    dense_weight: float = 1.0
    sparse_weight: float = 1.0


@dataclass(frozen=True)
class ScoredChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    dense_rank: int | None
    sparse_rank: int | None
    rerank_score: float | None
    metadata: dict


class HybridRetriever:
    def __init__(
        self,
        qdrant: AsyncQdrantClient,
        encoder: SentenceTransformer,
        reranker: CrossEncoder,
        bm25_index: BM25IndexProvider,  # per-domain
    ):
        self._qdrant = qdrant
        self._encoder = encoder
        self._reranker = reranker
        self._bm25_index = bm25_index

    async def search(self, query: RetrievalQuery) -> list[ScoredChunk]:
        # 1. Parallel dense + sparse
        dense_task = self._dense_search(query)
        sparse_task = self._sparse_search(query)
        dense_hits, sparse_hits = await asyncio.gather(dense_task, sparse_task)

        # 2. RRF fusion
        fused = self._reciprocal_rank_fusion(
            dense_hits, sparse_hits,
            dense_weight=query.dense_weight,
            sparse_weight=query.sparse_weight,
            top_n=query.rerank_top_n,
        )

        # 3. Cross-encoder rerank
        reranked = await self._rerank(query.text, fused)

        # 4. Temporal filter (post-rerank, surgical)
        in_window = self._temporal_filter(reranked, query.temporal_window)

        # 5. top-K
        return in_window[: query.top_k]

    async def _dense_search(self, query: RetrievalQuery) -> list[ScoredChunk]:
        vec = self._encoder.encode(query.text, normalize_embeddings=True).tolist()
        result = await self._qdrant.search(
            collection_name=query.domain,
            query_vector=vec,
            limit=query.rerank_top_n,
            with_payload=True,
        )
        return [
            ScoredChunk(
                chunk_id=hit.payload["chunk_id"],
                document_id=hit.payload["document_id"],
                text=hit.payload["text"],
                score=hit.score,
                dense_rank=rank,
                sparse_rank=None,
                rerank_score=None,
                metadata=hit.payload,
            )
            for rank, hit in enumerate(result)
        ]

    async def _sparse_search(self, query: RetrievalQuery) -> list[ScoredChunk]:
        bm25 = await self._bm25_index.get(query.domain)
        tokenized = query.text.lower().split()
        scores = bm25.get_scores(tokenized)
        idx_sorted = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        top = idx_sorted[: query.rerank_top_n]
        chunks = await self._bm25_index.get_chunks(query.domain, top)
        return [
            ScoredChunk(
                chunk_id=c.chunk_id, document_id=c.document_id, text=c.text,
                score=float(scores[i]), dense_rank=None, sparse_rank=rank,
                rerank_score=None, metadata=c.metadata,
            )
            for rank, (i, c) in enumerate(zip(top, chunks))
        ]

    def _reciprocal_rank_fusion(
        self,
        dense: list[ScoredChunk], sparse: list[ScoredChunk],
        *, dense_weight: float, sparse_weight: float,
        top_n: int, k: int = 60,
    ) -> list[ScoredChunk]:
        # RRF formula: score = sum_over_lists( weight / (k + rank) )
        merged: dict[str, ScoredChunk] = {}
        scores: dict[str, float] = {}

        for chunk in dense:
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + \
                                      dense_weight / (k + chunk.dense_rank + 1)
            merged[chunk.chunk_id] = chunk

        for chunk in sparse:
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + \
                                      sparse_weight / (k + chunk.sparse_rank + 1)
            if chunk.chunk_id not in merged:
                merged[chunk.chunk_id] = chunk
            else:
                # enrich with sparse rank
                old = merged[chunk.chunk_id]
                merged[chunk.chunk_id] = ScoredChunk(
                    **{**old.__dict__, "sparse_rank": chunk.sparse_rank}
                )

        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
        return [
            ScoredChunk(**{**merged[cid].__dict__, "score": scores[cid]})
            for cid in sorted_ids[:top_n]
        ]

    async def _rerank(self, query: str, candidates: list[ScoredChunk]) -> list[ScoredChunk]:
        if not candidates:
            return []
        pairs = [(query, c.text) for c in candidates]
        rerank_scores = await asyncio.to_thread(self._reranker.predict, pairs)
        reranked = [
            ScoredChunk(**{**c.__dict__, "rerank_score": float(s), "score": float(s)})
            for c, s in zip(candidates, rerank_scores)
        ]
        reranked.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return reranked

    def _temporal_filter(
        self, chunks: list[ScoredChunk], window: tuple[date, date],
    ) -> list[ScoredChunk]:
        start, end = window
        result = []
        for c in chunks:
            valid_from = date.fromisoformat(c.metadata.get("valid_from", "1900-01-01"))
            valid_to = date.fromisoformat(c.metadata.get("valid_to", "9999-12-31"))
            # chunk is in-window if its validity OVERLAPS the query window
            if valid_from <= end and valid_to >= start:
                result.append(c)
        return result
```

## I non negoziabili

### 1. RRF — no naive averaging

**Mai** fare `score = 0.5 * dense_score + 0.5 * sparse_score`. Le scale sono incomparabili (BM25 può essere 10, cosine 0.8). Reciprocal Rank Fusion lavora sui ranking, non sugli score, ed è l'approccio canonico nella letteratura IR.

### 2. Reranker SEMPRE

Anche per query "facili". Il reranker cross-encoder vede query + chunk insieme e cattura interazioni semantiche che dense+sparse perdono. Senza rerank, la qualità di top-K crolla di ~15-20% nei nostri benchmark.

Default locale: `bge-reranker-v2-m3` (~600 MB, GPU opzionale, CPU acceptable per top-N ≤ 32).
Cloud opzionale: Cohere Rerank API via HTTP client diretto (in `services/retrieval/`, NON via `cci_llm.LLMClient` perché Cohere reranker non è un LLM e non passa per il citation enforcer).

### 3. Filtro temporale post-rerank, non pre

Errore comune: filtrare per `valid_to >= today()` PRIMA del recupero → si perdono chunk che documentano *passato* validamente rilevante (es. "la certificazione valida fino al 2025-12-31" è esattamente l'evidenza che serve per dimostrare uno scadenza). Filtra **dopo** RRF+rerank, applicando la `temporal_window` della query.

### 4. Per-domain Qdrant collection

Una collection per dominio:
- `hera_it`
- `aou_clinical`
- `semsotec_product`
- `ducati_automotive`
- `esg_csrd`

**Mai** una collection unica con campo `domain` filtrato. Le distribuzioni di embedding diverse degradano la qualità ANN.

### 5. Cache temporal-aware

Chiave cache: `hash(query, domain, temporal_window, top_k)`. **Non** `hash(query)` puro. La stessa query in due finestre temporali è cosa diversa.

```python
def cache_key(q: RetrievalQuery) -> str:
    h = hashlib.sha256()
    h.update(q.text.encode())
    h.update(q.domain.encode())
    h.update(q.temporal_window[0].isoformat().encode())
    h.update(q.temporal_window[1].isoformat().encode())
    h.update(str(q.top_k).encode())
    return f"rag:{h.hexdigest()}"
```

TTL Redis: 1 h per default. Invalidazione esplicita su evento `document.indexed.v1` dello stesso dominio.

### 6. Chunking semantico, NON sliding window

In `services/ingestion`: chunking per paragrafi logici, mai sliding window con overlap. Il chunking deve preservare:
- Header di sezione → metadata `section_path`
- Tabelle intere → non spezzate, un chunk = una tabella
- Liste numerate → un chunk = una lista o frammento coerente

Sliding window con overlap distrugge il citation enforcement: lo stesso fatto compare in N chunk, il LLM cita uno a caso, l'evidenza non è univoca.

## Embeddings: scelta e versionamento

Dense default: `sentence-transformers/all-mpnet-base-v2` (768 dim, multilingual decent).
Per dominio italiano puro: opzionale `intfloat/multilingual-e5-large` (1024 dim, IT/EN bilanciato).

Lo **stesso modello** deve essere usato a indicizzazione e a query. Cambio modello → reindex completo del dominio. Versionare in metadata Qdrant: `embedding_model: "all-mpnet-base-v2@1.0"`.

## Metriche obbligatorie

```python
retrieval_latency_seconds = Histogram(
    "cci_retrieval_latency_seconds",
    "Hybrid retrieval latency",
    ["domain", "stage"],  # stage: dense, sparse, rrf, rerank, temporal
)
retrieval_chunks_returned = Histogram(
    "cci_retrieval_chunks_returned",
    "Number of chunks returned per query",
    ["domain"],
)
retrieval_cache_hits = Counter(
    "cci_retrieval_cache_hits_total",
    "Cache hits/misses",
    ["domain", "result"],  # result: hit|miss
)
retrieval_empty_results = Counter(
    "cci_retrieval_empty_results_total",
    "Queries returning zero chunks (concerning!)",
    ["domain"],
)
```

Empty results > 5% in una window è red flag: ontologia incompleta o indicizzazione bug.

## Anti-pattern da rifiutare

| Sintomo | Perché è grave |
|---|---|
| Solo dense, niente sparse | Fallisce su codici tecnici (ISO 27001 vs 27017) |
| Solo sparse, niente dense | Fallisce su sinonimi semantici |
| Average weighted dei score | Scale incomparabili, RRF è lo standard |
| Skip rerank "per latenza" | -15-20% qualità top-K, inaccettabile per compliance |
| Filtro temporale `WHERE valid_to >= today()` come condizione di indicizzazione | Perdi evidenza storica, cruciale per drift |
| Collection Qdrant unica multi-dominio | ANN degrada, recall crolla |
| `top_k = 50` perché "più meglio" | Il Generator riceve troppo contesto → diluizione citation, costi LLM ↑ |
| Riusare embedding di un modello dismesso senza reindex | Mismatch silenzioso, qualità crolla |
| Tokenizzazione BM25 banale (`text.split()`) per testi italiani | Perdi i pesi BM25 di parole declinate. Usa tokenizer + stemming italiano (snowball) |

## Tokenizer BM25 per italiano

```python
import re
from nltk.stem.snowball import ItalianStemmer
_STEMMER = ItalianStemmer()
_TOKEN_RX = re.compile(r"[a-zA-ZÀ-ÿ0-9]+")
_STOPWORDS = {"il","la","i","le","un","una","di","da","del","della","e","o","che","con","per","in"}

def tokenize_it(text: str) -> list[str]:
    tokens = _TOKEN_RX.findall(text.lower())
    return [_STEMMER.stem(t) for t in tokens if t not in _STOPWORDS and len(t) > 2]
```

Per codici tecnici (ISO 27001, IATF 16949): preserva intatti con whitelist regex prima dello stemming.

## Test pattern

```python
@pytest.mark.asyncio
async def test_hybrid_retrieves_chunk_with_iso_code_via_sparse(retriever, indexed_corpus):
    # corpus contains chunk: "La certificazione ISO 27001 scade il 2026-03-31"
    query = RetrievalQuery(
        text="quando scade ISO 27001?",
        domain="hera_it",
        temporal_window=(date(2026, 1, 1), date(2026, 12, 31)),
        top_k=5,
    )
    results = await retriever.search(query)
    assert any("ISO 27001" in r.text for r in results[:3])
    # the relevant chunk should rank in top-3 thanks to BM25 + rerank


@pytest.mark.asyncio
async def test_temporal_filter_excludes_out_of_window(retriever, indexed_corpus):
    query = RetrievalQuery(
        text="commitment cloud",
        domain="hera_it",
        temporal_window=(date(2026, 1, 1), date(2026, 3, 31)),
        top_k=10,
    )
    results = await retriever.search(query)
    for r in results:
        valid_from = date.fromisoformat(r.metadata["valid_from"])
        valid_to = date.fromisoformat(r.metadata["valid_to"])
        assert valid_from <= date(2026, 3, 31) and valid_to >= date(2026, 1, 1)
```

## Riferimenti
- RRF paper: Cormack, Clarke, Buettcher (2009)
- BGE reranker: https://huggingface.co/BAAI/bge-reranker-v2-m3
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §04 (Layer 4 — RAG & Reasoning)
- Skill correlate: `cci-grounding-enforcer`, `cci-ontology-yaml`
