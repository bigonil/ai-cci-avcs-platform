"""Redis-backed retrieval cache.

Key = SHA-256 of (query_text + domain + as_of_date + sorted_filter_items).
Value = JSON-encoded list of result dicts.
TTL = configurable (default 300 s).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger(__name__)

_CACHE_PREFIX = "cci:retrieval:cache:"


def _cache_key(
    query: str,
    domain: str,
    as_of: str | None,
    filters: dict[str, Any] | None,
) -> str:
    raw = json.dumps(
        {
            "q": query,
            "domain": domain,
            "as_of": as_of or date.today().isoformat(),
            "filters": sorted((filters or {}).items()),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{_CACHE_PREFIX}{digest}"


class RetrievalCache:
    def __init__(self, redis_url: str, ttl_seconds: int = 300) -> None:
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds

    async def get(
        self,
        query: str,
        domain: str,
        as_of: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        key = _cache_key(query, domain, as_of, filters)
        raw = await self._redis.get(key)
        if raw is None:
            log.debug("cache_miss", key=key[-12:])
            return None
        log.debug("cache_hit", key=key[-12:])
        return json.loads(raw)  # type: ignore[return-value]

    async def set(
        self,
        query: str,
        domain: str,
        results: list[dict[str, Any]],
        as_of: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> None:
        key = _cache_key(query, domain, as_of, filters)
        await self._redis.set(key, json.dumps(results), ex=self._ttl)
        log.debug("cache_set", key=key[-12:], ttl=self._ttl)

    async def invalidate(self, domain: str) -> int:
        """Delete all cached results for a domain (used after new document ingestion)."""
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor=cursor, match=f"{_CACHE_PREFIX}*", count=100
            )
            if keys:
                deleted += await self._redis.delete(*keys)
            if cursor == 0:
                break
        log.info("cache_invalidated", domain=domain, deleted=deleted)
        return deleted

    async def close(self) -> None:
        await self._redis.aclose()
