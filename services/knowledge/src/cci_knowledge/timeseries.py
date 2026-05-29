"""MongoDB time-series store for operational metrics.

Uses the pre-existing `cci_operational.metrics` time-series collection
created by infra/docker/init-scripts/02-init-databases.js.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

log = structlog.get_logger(__name__)

_METRICS_COLLECTION = "metrics"


class TimeSeriesStore:
    """Append-only time-series store for ingestion and knowledge metrics."""

    def __init__(self, mongodb_uri: str, db_name: str = "cci_operational") -> None:
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_uri)  # type: ignore[var-annotated]
        self._db: AsyncIOMotorDatabase = self._client[db_name]  # type: ignore[index]

    async def record(
        self,
        metric_name: str,
        value: float,
        meta: dict[str, Any] | None = None,
    ) -> None:
        doc = {
            "ts": datetime.now(UTC),
            "meta": {"metric": metric_name, **(meta or {})},
            "value": value,
        }
        await self._db[_METRICS_COLLECTION].insert_one(doc)
        log.debug("timeseries_recorded", metric=metric_name, value=value)

    async def query(
        self,
        metric_name: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"meta.metric": metric_name}
        if since:
            query["ts"] = {"$gte": since}
        cursor = self._db[_METRICS_COLLECTION].find(
            query,
            {"_id": 0},
            limit=limit,
            sort=[("ts", -1)],
        )
        results = await cursor.to_list(length=limit)
        return results

    async def close(self) -> None:
        self._client.close()
