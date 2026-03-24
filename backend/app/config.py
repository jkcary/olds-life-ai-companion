from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./yinling.db"
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"

    # Model configuration
    model_primary: str = "claude-opus-4-6"      # 主力模型：复杂推理、情感对话、健康问诊
    model_fast: str = "claude-haiku-4-5"         # 快速模型：简单分类、防诈骗初筛


settings = Settings()
