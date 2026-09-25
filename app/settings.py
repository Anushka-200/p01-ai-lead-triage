from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads config from environment variables / .env. Secrets never live in code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    cheap_model: str = "anthropic/claude-haiku-4-5-20251001"
    llm_timeout_s: float = 30.0


settings = Settings()
