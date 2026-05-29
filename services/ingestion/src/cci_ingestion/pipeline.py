"""Pipeline di ingestion — orchestrazione degli step (parse→NER→chunk→embed→index→publish).

Ogni step è atomico e loggato. La pipeline è asincrona per supportare
upload multipli in concorrenza (uvicorn + asyncio).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import redis.asyncio as aioredis
from cci_common.domain import ChunkMetadata, ConfidentialityLevel, DocumentMetadata
from cci_common.observability import get_logger
from qdrant_client import AsyncQdrantClient

from cci_ingestion.config import settings
from cci_ingestion.extractors.chunker import chunk_text
from cci_ingestion.extractors.embedder import chunk_id_from_text, embed_texts
from cci_ingestion.extractors.ner_extractor import extract_entities
from cci_ingestion.parsers.document_parser import parse_document
from cci_ingestion.publishers import (
    ensure_qdrant_collection,
    publish_document_indexed,
    upsert_chunks_to_qdrant,
)

logger = get_logger(__name__)


@dataclass
class IngestionResult:
    document_id: str
    chunk_count: int
    entity_count: int
    event_msg_id: str
    errors: list[str] = field(default_factory=list)


async def run_ingestion_pipeline(
    content: bytes,
    filename: str,
    domain: str,
    confidentiality: ConfidentialityLevel,
    qdrant: AsyncQdrantClient,
    redis_client: aioredis.Redis,  # type: ignore[type-arg]
) -> IngestionResult:
    """Esegue la pipeline completa di ingestion per un documento.

    Steps:
    1. Parse documento (Unstructured)
    2. NER + pseudonimizzazione PII
    3. Chunking semantico
    4. Embedding dense (sentence-transformers)
    5. Upsert Qdrant
    6. Pubblica CloudEvent su Redis Streams

    Neo4j graph update è delegato a knowledge-service tramite CloudEvent
    per rispettare R1 (bounded context isolation).
    """
    document_id = str(uuid.uuid4())
    collection_name = f"{settings.qdrant_collection_prefix}_{domain}"

    logger.info(
        "pipeline_start",
        document_id=document_id,
        filename=filename,
        domain=domain,
    )

    # Step 1: Parse
    parsed = parse_document(content, filename)
    logger.info("step_parse_done", document_id=document_id, pages=parsed.page_count)

    # Step 2: NER + PII redaction
    ner_result = extract_entities(
        parsed.text,
        domain=domain,
        mask_pii=settings.pii_detection_enabled,
    )
    logger.info(
        "step_ner_done",
        document_id=document_id,
        entity_count=len(ner_result.entities),
        pii_found=ner_result.pii_found,
    )

    # Step 3: Chunking semantico
    chunks = chunk_text(
        ner_result.redacted_text,
        max_tokens=settings.chunk_size_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    logger.info("step_chunking_done", document_id=document_id, chunk_count=len(chunks))

    if not chunks:
        return IngestionResult(
            document_id=document_id,
            chunk_count=0,
            entity_count=0,
            event_msg_id="",
            errors=["Nessun chunk estratto dal documento"],
        )

    # Step 4: Embedding
    chunk_texts = [c.text for c in chunks]
    embeddings = embed_texts(chunk_texts, model_name=settings.embedding_model)
    logger.info("step_embedding_done", document_id=document_id, vectors=len(embeddings))

    # Step 5: Upsert Qdrant
    await ensure_qdrant_collection(
        qdrant, collection_name, vector_size=settings.embedding_dim
    )
    chunk_ids = [
        chunk_id_from_text(document_id, c.chunk_index, c.text) for c in chunks
    ]
    payloads: list[dict[str, Any]] = [
        {
            "chunk_id": cid,
            "doc_id": document_id,
            "text": c.text,
            "domain": domain,
            "source_type": parsed.source_type,
            "confidentiality": confidentiality.value,
            "chunk_index": c.chunk_index,
            "token_estimate": c.token_estimate,
        }
        for cid, c in zip(chunk_ids, chunks, strict=True)
    ]
    await upsert_chunks_to_qdrant(qdrant, collection_name, chunk_ids, embeddings, payloads)

    # Step 6: Pubblica CloudEvent
    entities_serializable = [
        {
            "entity_type": e.entity_type,
            "label": e.label,
            "confidence": e.confidence,
        }
        for e in ner_result.entities
    ]
    event_msg_id = await publish_document_indexed(
        redis_client,
        document_id=document_id,
        entities=entities_serializable,
        metadata={
            "filename": filename,
            "domain": domain,
            "source_type": parsed.source_type,
            "page_count": parsed.page_count,
            "chunk_count": len(chunks),
            "pii_detected": ner_result.pii_found,
        },
    )

    logger.info(
        "pipeline_complete",
        document_id=document_id,
        chunk_count=len(chunks),
        entity_count=len(ner_result.entities),
        event_msg_id=event_msg_id,
    )

    return IngestionResult(
        document_id=document_id,
        chunk_count=len(chunks),
        entity_count=len(ner_result.entities),
        event_msg_id=event_msg_id,
    )


def build_document_metadata(
    document_id: str,
    filename: str,
    domain: str,
    source_type: str,
    confidentiality: ConfidentialityLevel,
    pii_detected: bool,
) -> DocumentMetadata:
    return DocumentMetadata(
        document_id=document_id,
        source_filename=filename,
        source_type=source_type,
        domain=domain,
        confidentiality=confidentiality,
        pii_detected=pii_detected,
    )
