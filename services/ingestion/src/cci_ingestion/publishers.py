"""Publishers — pubblica CloudEvents su Redis Streams e scrive su Qdrant/Neo4j."""
from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as aioredis
from cci_common.events import DocumentIndexedEvent
from cci_common.observability import get_logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from cci_ingestion.config import settings

logger = get_logger(__name__)


async def publish_document_indexed(
    redis_client: aioredis.Redis,  # type: ignore[type-arg]
    document_id: str,
    entities: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    """Pubblica evento ingestion.document.indexed.v1 su Redis Streams."""
    event = DocumentIndexedEvent.create(
        document_id=document_id,
        entities=entities,
        metadata=metadata,
    )
    payload = json.dumps(event.model_dump_cloudevent())
    msg_id = await redis_client.xadd(
        settings.redis_stream_ingestion,
        {"event": payload},
        maxlen=10_000,
    )
    logger.info(
        "event_published",
        event_type=event.type,
        document_id=document_id,
        stream=settings.redis_stream_ingestion,
        msg_id=msg_id,
    )
    return str(msg_id)


async def ensure_qdrant_collection(
    qdrant: AsyncQdrantClient,
    collection_name: str,
    vector_size: int,
) -> None:
    """Crea la collection Qdrant se non esiste (idempotente)."""
    existing = await qdrant.get_collections()
    names = {c.name for c in existing.collections}
    if collection_name not in names:
        await qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("qdrant_collection_created", collection=collection_name)


async def upsert_chunks_to_qdrant(
    qdrant: AsyncQdrantClient,
    collection_name: str,
    chunk_ids: list[str],
    embeddings: list[list[float]],
    payloads: list[dict[str, Any]],
) -> int:
    """Upsert batch di chunk in Qdrant. Ritorna il numero di punti inseriti."""
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, cid)),
            vector=emb,
            payload=payload,
        )
        for cid, emb, payload in zip(chunk_ids, embeddings, payloads, strict=True)
    ]
    await qdrant.upsert(collection_name=collection_name, points=points)
    logger.info(
        "qdrant_chunks_upserted",
        collection=collection_name,
        count=len(points),
    )
    return len(points)
