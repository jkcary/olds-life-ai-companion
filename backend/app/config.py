from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Anthropic (默认) ──────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    model_primary: str = "claude-opus-4-6"      # 主力模型：复杂推理、情感对话、健康问诊
    model_fast: str = "claude-haiku-4-5"         # 快速模型：简单分类、防诈骗初筛

    # ── 多供应商可选 API Key（通过 .env 预配置，也可运行时设置）────────────────
    openai_api_key: str = ""                    # OpenAI
    kimi_api_key: str = ""                      # Kimi (Moonshot)
    deepseek_api_key: str = ""                  # DeepSeek
    grok_api_key: str = ""                      # Grok (xAI)
    minimax_api_key: str = ""                   # MiniMax

    # ── 数据库 & 应用 ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./yinling.db"
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"


settings = Settings()
