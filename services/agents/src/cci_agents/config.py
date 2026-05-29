"""Configuration for the CCI Agents service."""
from __future__ import annotations

import pathlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    service_name: str = "cci-agents"
    version: str = "0.1.0"
    port: int = Field(default=8004, alias="CCI_AGENTS_PORT")

    # LLM
    llm_model: str = Field(default="claude-sonnet-4-6", alias="CCI_LLM_MODEL")
    llm_max_tokens: int = Field(default=4096, alias="CCI_LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.0, alias="CCI_LLM_TEMPERATURE")

    # Downstream service URLs
    retrieval_url: str = Field(default="http://localhost:8002", alias="CCI_RETRIEVAL_URL")
    coherence_url: str = Field(default="http://localhost:8003", alias="CCI_COHERENCE_URL")
    governance_url: str = Field(default="http://localhost:8005", alias="CCI_GOVERNANCE_URL")

    # MongoDB (for LangGraph checkpoint)
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017/cci_operational",
        alias="MONGODB_URI",
    )
    mongodb_checkpoint_enabled: bool = Field(
        default=True, alias="CCI_CHECKPOINT_ENABLED"
    )

    # Prompts
    prompts_path: pathlib.Path = Field(
        default=pathlib.Path("/app/prompts/v1"),
        alias="PROMPTS_PATH",
    )

    # HITL threshold (R6)
    hitl_impact_threshold_eur: float = Field(
        default=50_000.0, alias="CCI_HITL_THRESHOLD_EUR"
    )

    # Retrieval
    retrieval_top_k: int = Field(default=20, alias="CCI_RETRIEVAL_TOP_K")


def get_settings() -> AgentsSettings:
    return AgentsSettings()
