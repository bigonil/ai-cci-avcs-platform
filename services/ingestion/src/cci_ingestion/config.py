"""Configurazione ingestion-service — tutte le variabili da env (12-Factor)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Service
    service_name: str = "cci-ingestion"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection_prefix: str = "cci"

    # Redis Streams
    redis_url: str = "redis://localhost:6379/0"
    redis_stream_ingestion: str = "cci:ingestion:events"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_bucket_documents: str = "cci-documents"
    minio_secure: bool = False

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "changeme"

    # PII
    pii_detection_enabled: bool = True
    pii_mask_token: str = "[REDACTED]"

    # OTel
    otel_exporter_otlp_endpoint: str = ""

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


settings = IngestionSettings()
