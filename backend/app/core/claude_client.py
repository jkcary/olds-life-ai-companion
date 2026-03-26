"""
Claude API 客户端单例
AI 原生架构的核心 — 所有模块通过此客户端访问 Claude
"""
import anthropic
from app.config import settings

# 全局单例，整个应用共用
_client: anthropic.Anthropic | None = None
_runtime_api_key: str | None = None  # 运行时动态设置（Demo 用）


def set_api_key(key: str) -> None:
    """运行时更新 API Key（Demo 页面配置入口）"""
    global _client, _runtime_api_key
    _runtime_api_key = key.strip()
    _client = anthropic.Anthropic(api_key=_runtime_api_key)


def get_api_key_status() -> dict:
    key = _runtime_api_key or settings.anthropic_api_key or ""
    configured = bool(key) and key != "your_anthropic_api_key_here"
    return {
        "configured": configured,
        "source": "runtime" if _runtime_api_key else "env",
        "hint": key[:8] + "..." if configured else None,
    }


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = _runtime_api_key or settings.anthropic_api_key
        _client = anthropic.Anthropic(api_key=key)
    return _client


# 模型常量
MODEL_PRIMARY = settings.model_primary   # claude-opus-4-6  — 主力
MODEL_FAST = settings.model_fast         # claude-haiku-4-5 — 快速分类

# 典型 max_tokens 设置
MAX_TOKENS_CHAT = 2048      # 聊天回复
MAX_TOKENS_HEALTH = 4096    # 健康问诊（需要详细说明）
MAX_TOKENS_SAFETY = 512     # 安全检测（短结论即可）
