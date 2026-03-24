"""
Claude API 客户端单例
AI 原生架构的核心 — 所有模块通过此客户端访问 Claude
"""
import anthropic
from app.config import settings

# 全局单例，整个应用共用
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# 模型常量
MODEL_PRIMARY = settings.model_primary   # claude-opus-4-6  — 主力
MODEL_FAST = settings.model_fast         # claude-haiku-4-5 — 快速分类

# 典型 max_tokens 设置
MAX_TOKENS_CHAT = 2048      # 聊天回复
MAX_TOKENS_HEALTH = 4096    # 健康问诊（需要详细说明）
MAX_TOKENS_SAFETY = 512     # 安全检测（短结论即可）
