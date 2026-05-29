"""Qdrant vector store adapter for the Knowledge Service."""
from __future__ import annotations

import uuid
from typing import Any, TypedDict

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

log = structlog.get_logger(__name__)


class ChunkPayload(TypedDict, total=False):
    chunk_id: str
    doc_id: str
    text: str
    domain: str
    valid_from: str | None
    valid_to: str | None
    version: int
    source_type: str
    confidentiality: str
    cert_ref: list[str]
    embedding_model: str


class QdrantVectorStore:
    """Thin async wrapper around Qdrant for chunk indexing and search."""

    def __init__(self, host: str, port: int, api_key: str | None, embedding_dim: int) -> None:
        self._client = AsyncQdrantClient(host=host, port=port, api_key=api_key)
        self._dim = embedding_dim

    def _collection_name(self, domain: str) -> str:
        return f"cci_{domain}"

    async def ensure_collection(self, domain: str) -> None:
        name = self._collection_name(domain)
        existing = await self._client.get_collections()
        names = {c.name for c in existing.collections}
        if name not in names:
            await self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
            log.info("qdrant_collection_created", collection=name)
        else:
            log.debug("qdrant_collection_exists", collection=name)

    async def upsert_chunks(
        self,
        domain: str,
        chunks: list[ChunkPayload],
        vectors: list[list[float]],
    ) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        name = self._collection_name(domain)
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, c.get("chunk_id", str(uuid.uuid4())))),
                vector=v,
                payload=dict(c),
            )
            for c, v in zip(chunks, vectors)
        ]
        await self._client.upsert(collection_name=name, points=points)
        log.info("qdrant_upsert", collection=name, count=len(points))
        return len(points)

    async def search(
        self,
        domain: str,
        query_vector: list[float],
        limit: int = 10,
        filter_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        name = self._collection_name(domain)
        qdrant_filter: Filter | None = None
        if filter_payload:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_payload.items()
            ]
            qdrant_filter = Filter(must=conditions)
        results = await self._client.search(
            collection_name=name,
            query_vector=query_vector,
            limit=limit,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        return [
            {"score": r.score, "payload": r.payload, "id": str(r.id)}
            for r in results
        ]

    async def delete_by_doc_id(self, domain: str, doc_id: str) -> int:
        name = self._collection_name(domain)
        result = await self._client.delete(
            collection_name=name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        deleted = getattr(result, "deleted", 0) or 0
        log.info("qdrant_delete_by_doc", collection=name, doc_id=doc_id, deleted=deleted)
        return deleted

    async def close(self) -> None:
        await self._client.close()
