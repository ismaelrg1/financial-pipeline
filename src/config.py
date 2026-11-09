from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
        env_prefix="FINANCIAL_PIPELINE_",
        extra="ignore",
    )

    input_path: Path
    output_path: Path
    log_level: str = "INFO"

    # Frankfurter API
    frankfurter_api_url: str = "https://api.frankfurter.dev/v2/rates"
    frankfurter_provider: str = "ecb"
    frankfurter_base_currency: str = "EUR"
    frankfurter_quote_currencies: tuple[str, ...] = ("USD", "GPB", "JPY")
    http_timeout_seconds: int = Field(default=10, gt=0)