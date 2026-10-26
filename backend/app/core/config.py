from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OTPROOF_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./otproof.db"
    demo_mode: bool = True
    role_tokens: str = ""
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    source_cache_ttl_seconds: int = 1800
    max_upload_bytes: int = 10 * 1024 * 1024
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

    @property
    def configured_tokens(self) -> dict[str, str]:
        if self.role_tokens:
            import json

            return json.loads(self.role_tokens)
        if self.demo_mode:
            return {
                "demo-engineer-token": "engineer",
                "demo-reviewer-token": "reviewer",
                "demo-approver-token": "approver",
                "demo-admin-token": "admin",
            }
        return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
