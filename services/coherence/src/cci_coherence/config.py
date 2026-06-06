"""Configuration for the Coherence Engine."""
from __future__ import annotations

import pathlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoherenceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    service_name: str = "cci-coherence"
    version: str = "0.1.0"
    port: int = Field(default=8003, alias="CCI_COHERENCE_PORT")

    # Neo4j (optional — used for graph-based evaluation)
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="changeme", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    neo4j_enabled: bool = Field(default=True, alias="CCI_NEO4J_ENABLED")

    # Ontologies
    ontologies_path: pathlib.Path = Field(
        default=pathlib.Path("/app/ontologies"),
        alias="ONTOLOGIES_PATH",
    )

    # Optional fixture files for chunk-based fallback in dev/demo (FIXTURES_PATH env)
    fixtures_path: pathlib.Path | None = Field(default=None, alias="FIXTURES_PATH")

    # MongoDB (optional — for explanation cache)
    mongodb_uri: str = Field(
        default="mongodb://cci_app:apppassword@mongodb:27017/cci_operational?authSource=cci_operational",
        alias="MONGODB_URI",
    )
    mongodb_database: str = Field(default="cci_operational", alias="MONGODB_DATABASE")
    mongodb_enabled: bool = Field(default=True, alias="CCI_COHERENCE_MONGODB_ENABLED")

    # Agents service (for on-demand explanation generation)
    agents_service_url: str = Field(default="http://agents:8004", alias="AGENTS_SERVICE_URL")

    # Evaluation
    confidence_threshold: float = 0.5


def get_settings() -> CoherenceSettings:
    return CoherenceSettings()
