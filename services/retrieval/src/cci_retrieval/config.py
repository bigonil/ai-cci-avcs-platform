"""Configuration for the Retrieval Service."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    service_name: str = "cci-retrieval"
    version: str = "0.1.0"
    port: int = Field(default=8002, alias="CCI_RETRIEVAL_PORT")

    # Qdrant
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cache_ttl_seconds: int = 300

    # Embedding
    embedding_model: str = Field(default="all-mpnet-base-v2", alias="CCI_EMBEDDING_MODEL")
    embedding_dim: int = 768

    # Retrieval
    dense_candidate_limit: int = 100
    default_top_k: int = 10
    rrf_k: int = 60

    # Reranker — set to empty string to disable
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        alias="CCI_RERANKER_MODEL",
    )
    reranker_enabled: bool = Field(default=True, alias="CCI_RERANKER_ENABLED")

    # Citation enforcer
    citation_min_sentence_length: int = 40
    citation_pattern: str = r"\[(?:source:\s*)?[a-zA-Z0-9_\-]{8,}\]"


def get_settings() -> RetrievalSettings:
    return RetrievalSettings()
