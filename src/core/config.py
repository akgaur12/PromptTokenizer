from __future__ import annotations
from functools import lru_cache
from typing import Any, Tuple, Type
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from pydantic_settings.sources.providers.dotenv import DotEnvSettingsSource


class _FlexDotEnvSource(DotEnvSettingsSource):
    def decode_complex_value(self, field_name: str, field_info: Any, value: Any) -> Any:
        try:
            return super().decode_complex_value(field_name, field_info, value)
        except Exception:
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            raise


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "prompt-tokenizer"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    app_version: str = "0.1.0"
    workers: int = 4
    timeout: int = 120
    graceful_timeout: int = 30

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, _FlexDotEnvSource(settings_cls), file_secret_settings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
