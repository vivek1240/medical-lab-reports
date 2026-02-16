from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./medical_lab_reports.db"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    openai_api_key: str | None = None
    llama_cloud_api_key: str | None = None
    api_base_url: str = "http://localhost:8000"
    classifier_fuzzy_threshold: int = 85
    classifier_enable_llm_fallback: bool = True
    allowed_origins: str = "http://localhost:3001"
    max_upload_size_mb: int = 20


settings = Settings()
