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

    # Evaluation
    confidence_threshold: float = 0.5


def get_settings() -> CoherenceSettings:
    return CoherenceSettings()
