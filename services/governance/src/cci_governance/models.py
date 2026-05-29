from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AppendRequest(BaseModel):
    """Accepts the flat audit payload from the agents auditor node."""

    model_config = {"extra": "allow"}

    event_type: str
    correlation_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        data = self.model_dump()
        data.pop("event_type", None)
        data.pop("correlation_id", None)
        return data


class AppendResponse(BaseModel):
    seq: int
    event_id: str
    accepted: bool = True


class HitlActionCreate(BaseModel):
    correlation_id: str | None = None
    domain: str
    action_type: str
    impact_eur: float
    description: str
    motivation: str = Field(min_length=20)


class HitlActionResponse(BaseModel):
    model_config = {"extra": "ignore"}

    action_id: str
    status: str
    correlation_id: str | None = None
    domain: str
    action_type: str
    impact_eur: float
    description: str
    motivation: str
    created_at: datetime
    decided_at: datetime | None = None
    reviewer_id: str | None = None


class HitlDecisionRequest(BaseModel):
    reviewer_id: str
    motivation: str = Field(min_length=20)


class ChainVerifyResponse(BaseModel):
    valid: bool
    total_records: int
    tail_consistent: bool
    broken_links: list[dict[str, Any]] = Field(default_factory=list)
    first_seq: int | None = None
    last_seq: int | None = None
