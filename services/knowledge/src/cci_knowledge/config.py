"""Configuration for the Knowledge Service."""
from __future__ import annotations

import pathlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CCI_KNOWLEDGE_", env_file=".env", extra="ignore")

    service_name: str = "cci-knowledge"
    version: str = "0.1.0"
    port: int = 8001

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="changeme", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")

    # Qdrant
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")

    # MongoDB
    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_operational_db: str = "cci_operational"

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_stream: str = "cci:ingestion:events"
    redis_consumer_group: str = "knowledge-service"
    redis_consumer_name: str = "knowledge-0"

    # Ontologies
    ontologies_path: pathlib.Path = Field(
        default=pathlib.Path("/app/ontologies"),
        alias="ONTOLOGIES_PATH",
    )

    # Embedding
    embedding_dim: int = 768

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


def get_settings() -> KnowledgeSettings:
    return KnowledgeSettings()
