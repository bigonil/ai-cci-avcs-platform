"""Tests for QdrantVectorStore using mocks (no container required)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from cci_knowledge.vector_store import QdrantVectorStore


@pytest.fixture()
def mock_qdrant_client():
    with patch("cci_knowledge.vector_store.AsyncQdrantClient") as MockClient:
        client = AsyncMock()
        MockClient.return_value = client

        # Simulate no existing collections
        collections_result = MagicMock()
        collections_result.collections = []
        client.get_collections = AsyncMock(return_value=collections_result)
        client.create_collection = AsyncMock()
        client.upsert = AsyncMock()
        client.search = AsyncMock(return_value=[])
        client.delete = AsyncMock()
        client.close = AsyncMock()

        yield client


@pytest.fixture()
def store(mock_qdrant_client: AsyncMock) -> QdrantVectorStore:
    return QdrantVectorStore(host="localhost", port=6333, api_key=None, embedding_dim=4)


@pytest.mark.asyncio
async def test_ensure_collection_creates_if_missing(
    store: QdrantVectorStore, mock_qdrant_client: AsyncMock
) -> None:
    await store.ensure_collection("hera_it")
    mock_qdrant_client.create_collection.assert_called_once()
    call_kwargs = mock_qdrant_client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "cci_hera_it"


@pytest.mark.asyncio
async def test_ensure_collection_idempotent(
    store: QdrantVectorStore, mock_qdrant_client: AsyncMock
) -> None:
    """Second call with existing collection must NOT call create_collection."""
    existing = MagicMock()
    existing.name = "cci_hera_it"
    result = MagicMock()
    result.collections = [existing]
    mock_qdrant_client.get_collections = AsyncMock(return_value=result)

    await store.ensure_collection("hera_it")
    mock_qdrant_client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_chunks(
    store: QdrantVectorStore, mock_qdrant_client: AsyncMock
) -> None:
    chunks = [{"chunk_id": "c1", "doc_id": "d1", "text": "hello", "domain": "test"}]
    vectors = [[0.1, 0.2, 0.3, 0.4]]
    n = await store.upsert_chunks("test", chunks, vectors)  # type: ignore[arg-type]
    assert n == 1
    mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_mismatched_raises(store: QdrantVectorStore) -> None:
    with pytest.raises(ValueError):
        await store.upsert_chunks("test", [{"chunk_id": "c1"}], [[0.1], [0.2]])  # type: ignore[list-item]


@pytest.mark.asyncio
async def test_search(
    store: QdrantVectorStore, mock_qdrant_client: AsyncMock
) -> None:
    hit = MagicMock()
    hit.score = 0.95
    hit.payload = {"text": "result"}
    hit.id = "abc"
    mock_qdrant_client.search = AsyncMock(return_value=[hit])

    results = await store.search("hera_it", [0.1, 0.2, 0.3, 0.4])
    assert len(results) == 1
    assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_delete_by_doc_id(
    store: QdrantVectorStore, mock_qdrant_client: AsyncMock
) -> None:
    mock_qdrant_client.delete = AsyncMock(return_value=MagicMock(deleted=5))
    await store.delete_by_doc_id("hera_it", "doc-123")
    mock_qdrant_client.delete.assert_called_once()
