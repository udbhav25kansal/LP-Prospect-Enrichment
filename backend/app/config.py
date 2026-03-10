from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite+aiosqlite:///./lp_enrichment.db"
    database_url_sync: str = "sqlite:///./lp_enrichment.db"

    # API Keys
    tavily_api_key: str = ""
    anthropic_api_key: str = ""

    # AI Model Config
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    # Rate Limiting
    tavily_requests_per_minute: int = 50
    claude_requests_per_minute: int = 30

    # Pipeline Config
    enrichment_concurrency: int = 5
    scoring_concurrency: int = 3
    batch_size: int = 10

    # Scoring Weights
    d1_weight: float = 0.35
    d2_weight: float = 0.30
    d3_weight: float = 0.20
    d4_weight: float = 0.15

    # Tier Thresholds
    tier_priority_close: float = 8.0
    tier_strong_fit: float = 6.5
    tier_moderate_fit: float = 5.0

    # Default Scores (when insufficient data)
    default_d1_score: float = 4.0
    default_d3_score: float = 3.0
    default_d4_score: float = 4.0

    # Frontend
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
