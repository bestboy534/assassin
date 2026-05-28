from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = ""
    model_name: str = "gpt-4o-mini"
    use_llm: bool = False

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    save_raw_billing_text: bool = False
    log_level: str = "info"
    max_input_chars: int = 30000

    enable_database: bool = True
    sqlite_path: str = "data/saas_assassin.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
