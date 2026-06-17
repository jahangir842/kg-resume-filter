"""Central configuration. Scoring weights live here on purpose: the reasoning
is tunable and auditable, never hidden inside a model."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    # LLM
    anthropic_api_key: str = ""
    kgrf_llm_model: str = "claude-opus-4-8"

    # Reasoning weights (per-component contribution to the fit score)
    kgrf_weight_direct: float = 1.0
    kgrf_weight_inferred: float = 0.8
    kgrf_weight_adjacent: float = 0.4
    kgrf_adjacent_max_hops: int = 2


settings = Settings()
