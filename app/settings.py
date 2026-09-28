from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads config from environment variables / .env. Secrets never live in code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql://p01:p01@localhost:5433/p01"
    cheap_model: str = "anthropic/claude-haiku-4-5-20251001"
    escalation_model: str = "anthropic/claude-sonnet-5"
    routing_confidence_threshold: float = 0.7  # below this, ask the bigger model too
    llm_timeout_s: float = 30.0
    webhook_shared_secret: str = ""
    webhook_max_age_s: int = 300  # reject signed requests older than this
    webhook_max_body_bytes: int = 100_000
    slack_webhook_url: str = ""
    google_sheet_id: str = ""
    google_service_account_file: str = "secrets/google-service-account.json"
    dashboard_password: str = ""
    hot_lead_priority: int = 4  # priority at or above this sends a Slack alert
    max_repairs: int = 2  # extra tries after the first, each told what was wrong

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()
