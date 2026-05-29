"""Redis Streams consumer — processes DocumentIndexedEvents from ingestion service.

Consumer group: knowledge-service
Stream: cci:ingestion:events
On error: moves message to DLQ stream cci:ingestion:dlq
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from cci_knowledge.temporal_graph import TemporalGraph
from cci_knowledge.vector_store import QdrantVectorStore

log = structlog.get_logger(__name__)

_DLQ_STREAM = "cci:ingestion:dlq"
_BLOCK_MS = 1000


class DocumentIndexedConsumer:
    """Consumes `ingestion.document.indexed.v1` events and updates KG + vector store."""

    def __init__(
        self,
        redis_url: str,
        stream: str,
        group: str,
        consumer_name: str,
        graph: TemporalGraph,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._stream = stream
        self._group = group
        self._consumer = consumer_name
        self._graph = graph
        self._vector_store = vector_store
        self._running = False

    async def _ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._stream, self._group, id="0", mkstream=True
            )
            log.info("redis_group_created", stream=self._stream, group=self._group)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def start(self) -> None:
        await self._ensure_group()
        self._running = True
        log.info("consumer_started", stream=self._stream, group=self._group)
        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    groupname=self._group,
                    consumername=self._consumer,
                    streams={self._stream: ">"},
                    count=10,
                    block=_BLOCK_MS,
                )
                if not messages:
                    continue
                for _stream, entries in messages:
                    for msg_id, fields in entries:
                        await self._handle(msg_id, fields)
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("consumer_loop_error")
                await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False
        await self._redis.aclose()
        log.info("consumer_stopped")

    async def _handle(self, msg_id: str, fields: dict[str, str]) -> None:
        try:
            event = json.loads(fields.get("data", "{}"))
            event_type = fields.get("type", event.get("type", ""))
            if event_type != "ingestion.document.indexed.v1":
                await self._redis.xack(self._stream, self._group, msg_id)
                return
            await self._process_event(event)
            await self._redis.xack(self._stream, self._group, msg_id)
            log.info("event_processed", msg_id=msg_id, type=event_type)
        except Exception:
            log.exception("event_processing_error", msg_id=msg_id)
            await self._move_to_dlq(msg_id, fields)
            await self._redis.xack(self._stream, self._group, msg_id)

    async def _process_event(self, event: dict[str, Any]) -> None:
        data = event.get("data", {})
        doc_id: str = data.get("document_id", "")
        metadata: dict[str, Any] = data.get("metadata", {})
        entities: list[dict[str, Any]] = data.get("entities", [])
        domain: str = metadata.get("domain", "unknown")

        await self._vector_store.ensure_collection(domain)

        for entity in entities:
            await self._graph.upsert_entity(
                entity_id=entity.get("entity_id", doc_id),
                entity_type=entity.get("entity_type", "Unknown"),
                domain=domain,
                properties=entity.get("properties", {}),
                valid_from=entity.get("valid_from"),
                valid_to=entity.get("valid_to"),
                provenance_chunk_id=entity.get("provenance_chunk_id", doc_id),
                confidence=entity.get("confidence", 1.0),
            )

    async def _move_to_dlq(self, msg_id: str, fields: dict[str, str]) -> None:
        await self._redis.xadd(
            _DLQ_STREAM,
            {"original_id": msg_id, **fields},
        )
        log.warning("message_moved_to_dlq", msg_id=msg_id)
