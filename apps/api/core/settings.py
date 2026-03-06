from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "BaseCore v0.2"
    log_dir: Path = Path("data/logs")
    enable_auth: bool = False
    service_api_key: str | None = None
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    store_raw_outputs: bool = False

    default_model_source: str = "internal"
    external_fallback_enabled: bool = True
    reviewer_default_source: str = "external"
    long_input_external_threshold: int = 6000
    max_attempts: int = 3
    request_timeout_seconds: int = 45
    max_input_chars: int = 12_000
    max_context_chars: int = 24_000

    internal_base_url: str = "http://localhost:8000/v1"
    internal_api_key: str = "EMPTY"
    internal_model_name: str = "basecore-internal"
    internal_provider: str = "openai-compatible"

    external_provider: str = "openai"
    external_base_url: str | None = None
    external_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EXTERNAL_API_KEY", "OPENAI_API_KEY"),
    )
    external_model_name: str | None = None

    vllm_model_id: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    vllm_served_model_name: str = "basecore-internal"
    hf_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    return settings
