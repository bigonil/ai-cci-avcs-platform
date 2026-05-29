"""Hybrid retriever: dense (Qdrant) + sparse (BM25) → RRF → optional rerank.

Pipeline per query:
  1. Embed query with sentence-transformers
  2. Dense search in Qdrant (top candidate_limit results, with payloads)
  3. Build ephemeral BM25 on those candidates, re-rank with BM25
  4. Fuse dense + BM25 via RRF
  5. Cross-encoder rerank if enabled
  6. Return top-K
"""
from __future__ import annotations

from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from cci_retrieval.bm25_index import EphemeralBM25
from cci_retrieval.config import RetrievalSettings
from cci_retrieval.embedder import embed_query
from cci_retrieval.reranker import rerank
from cci_retrieval.rrf import fuse_search_results

log = structlog.get_logger(__name__)


class HybridRetriever:
    def __init__(self, settings: RetrievalSettings) -> None:
        self._cfg = settings
        self._qdrant = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )

    async def search(
        self,
        query: str,
        domain: str,
        top_k: int | None = None,
        filter_payload: dict[str, Any] | None = None,
        as_of_date: str | None = None,
        rerank_enabled: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Full hybrid pipeline. Returns top-K chunks enriched with scores."""
        k = top_k or self._cfg.default_top_k
        do_rerank = (
            rerank_enabled
            if rerank_enabled is not None
            else self._cfg.reranker_enabled
        )
        collection = f"cci_{domain}"

        # Step 1 — embed query
        query_vector = await embed_query(query, self._cfg.embedding_model)

        # Step 2 — dense search (broad candidate set)
        dense_hits = await self._dense_search(
            collection, query_vector, self._cfg.dense_candidate_limit, filter_payload, as_of_date
        )

        if not dense_hits:
            return []

        # Step 3 — BM25 on candidate set
        bm25_idx = EphemeralBM25(dense_hits, text_key="text")
        bm25_hits = bm25_idx.search(query, limit=self._cfg.dense_candidate_limit)

        # Step 4 — RRF fusion
        fused = fuse_search_results(
            dense_hits, bm25_hits, id_key="chunk_id", k=self._cfg.rrf_k
        )
        log.debug("rrf_fused", total=len(fused), query=query[:60])

        # Step 5 — optional rerank
        if do_rerank and self._cfg.reranker_model:
            fused = await rerank(
                query=query,
                candidates=fused,
                model_name=self._cfg.reranker_model,
                text_key="text",
                limit=k,
            )
        else:
            fused = fused[:k]

        return fused

    async def dense_only(
        self,
        query: str,
        domain: str,
        top_k: int | None = None,
        filter_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Dense-only search for debugging or when BM25 is not applicable."""
        k = top_k or self._cfg.default_top_k
        query_vector = await embed_query(query, self._cfg.embedding_model)
        return await self._dense_search(f"cci_{domain}", query_vector, k, filter_payload, None)

    async def bm25_only(
        self,
        query: str,
        domain: str,
        top_k: int | None = None,
        filter_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """BM25-only search over a dense candidate pool."""
        k = top_k or self._cfg.default_top_k
        query_vector = await embed_query(query, self._cfg.embedding_model)
        hits = await self._dense_search(
            f"cci_{domain}", query_vector, self._cfg.dense_candidate_limit, filter_payload, None
        )
        idx = EphemeralBM25(hits, text_key="text")
        return idx.search(query, limit=k)

    async def close(self) -> None:
        await self._qdrant.close()

    async def _dense_search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int,
        filter_payload: dict[str, Any] | None,
        as_of_date: str | None,
    ) -> list[dict[str, Any]]:
        qdrant_filter: Filter | None = None
        conditions = []
        if filter_payload:
            conditions += [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_payload.items()
            ]
        if qdrant_filter is None and conditions:
            from qdrant_client.http.models import Filter as QFilter
            qdrant_filter = QFilter(must=conditions)

        try:
            results = await self._qdrant.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
        except Exception:
            log.warning("qdrant_collection_not_found", collection=collection)
            return []

        hits = []
        for r in results:
            payload = dict(r.payload or {})
            payload["_dense_score"] = r.score
            hits.append(payload)
        return hits
