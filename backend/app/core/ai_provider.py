"""
多AI供应商客户端 — 统一接口
支持：Anthropic Claude, OpenAI, Kimi (Moonshot), MiniMax, Grok (xAI), DeepSeek
所有 OpenAI 兼容供应商共用同一套 openai.AsyncOpenAI 接口，只需切换 base_url 和 api_key
"""
import json
from collections.abc import AsyncGenerator

# ── 供应商配置表 ──────────────────────────────────────────────────────────────
PROVIDER_CONFIGS: dict[str, dict] = {
    "anthropic": {
        "name": "Anthropic Claude",
        "base_url": None,          # 使用原生 anthropic SDK
        "default_model": "claude-opus-4-6",
        "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "key_hint": "sk-ant-",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "key_hint": "sk-",
    },
    "kimi": {
        "name": "Kimi (Moonshot AI)",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-128k",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "key_hint": "sk-",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "key_hint": "sk-",
    },
    "grok": {
        "name": "Grok (xAI)",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-3-latest",
        "models": ["grok-3-latest", "grok-3-mini-latest", "grok-2-latest"],
        "key_hint": "xai-",
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "default_model": "MiniMax-Text-01",
        "models": ["MiniMax-Text-01", "abab6.5s-chat"],
        "key_hint": "",
    },
}

# ── 运行时状态 ─────────────────────────────────────────────────────────────────
_active_provider: str = "anthropic"
_api_keys: dict[str, str] = {}       # provider_id -> api_key
_selected_models: dict[str, str] = {}  # provider_id -> model


# ── 配置 API ──────────────────────────────────────────────────────────────────

def set_provider(provider: str, api_key: str, model: str | None = None) -> None:
    """设置当前活跃供应商、API Key 和模型"""
    global _active_provider
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"未知供应商: {provider}，支持: {list(PROVIDER_CONFIGS)}")
    _active_provider = provider
    _api_keys[provider] = api_key.strip()
    _selected_models[provider] = model or PROVIDER_CONFIGS[provider]["default_model"]

    # Anthropic 还需更新原生 client 单例
    if provider == "anthropic":
        from app.core.claude_client import set_api_key
        set_api_key(api_key)


def get_active_provider() -> str:
    return _active_provider


def get_provider_status() -> dict:
    """返回当前供应商状态（供 /health 和 status-bar 使用）"""
    from app.config import settings
    p = _active_provider
    cfg = PROVIDER_CONFIGS[p]
    key = _api_keys.get(p, "")
    if not key and p == "anthropic":
        key = settings.anthropic_api_key or ""
    configured = bool(key) and key not in ("", "your_anthropic_api_key_here")
    return {
        "provider": p,
        "provider_name": cfg["name"],
        "configured": configured,
        "model": _selected_models.get(p, cfg["default_model"]),
        "hint": key[:10] + "..." if configured else None,
        # 兼容旧字段（claude_client.get_api_key_status）
        "source": "runtime" if _api_keys.get(p) else "env",
    }


def get_all_providers() -> list[dict]:
    """返回所有供应商信息，供前端渲染选择器"""
    from app.config import settings
    result = []
    for pid, cfg in PROVIDER_CONFIGS.items():
        key = _api_keys.get(pid, "")
        if not key and pid == "anthropic":
            key = settings.anthropic_api_key or ""
        result.append({
            "id": pid,
            "name": cfg["name"],
            "configured": bool(key) and key not in ("", "your_anthropic_api_key_here"),
            "models": cfg["models"],
            "default_model": cfg["default_model"],
            "selected_model": _selected_models.get(pid, cfg["default_model"]),
            "active": pid == _active_provider,
        })
    return result


# ── 内部 helpers ───────────────────────────────────────────────────────────────

def _get_key(provider: str) -> str:
    from app.config import settings
    key = _api_keys.get(provider, "")
    if not key and provider == "anthropic":
        key = settings.anthropic_api_key or ""
    return key


def _get_openai_client(provider: str):
    """返回指向对应供应商的 AsyncOpenAI 客户端"""
    from openai import AsyncOpenAI
    cfg = PROVIDER_CONFIGS[provider]
    return AsyncOpenAI(api_key=_get_key(provider), base_url=cfg["base_url"])


# ── 流式对话 ──────────────────────────────────────────────────────────────────

async def chat_stream(
    messages: list[dict],
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 2048,
    provider: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    统一流式聊天接口。
    产出 SSE 格式：
      data: {"type": "delta", "text": "..."}
      data: {"type": "done"}
    """
    p = provider or _active_provider
    m = model or _selected_models.get(p, PROVIDER_CONFIGS[p]["default_model"])

    if p == "anthropic":
        async for chunk in _anthropic_stream(messages, system, m, max_tokens):
            yield chunk
    else:
        async for chunk in _openai_stream(p, messages, system, m, max_tokens):
            yield chunk


async def _anthropic_stream(
    messages: list[dict],
    system: str | None,
    model: str,
    max_tokens: int,
) -> AsyncGenerator[str, None]:
    """通过 Anthropic 原生 SDK 流式输出"""
    from app.core.claude_client import get_client
    client = get_client()
    kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system

    try:
        with client.messages.stream(**kwargs) as stream:
            for event in stream:
                if (
                    event.type == "content_block_delta"
                    and event.delta.type == "text_delta"
                ):
                    yield f"data: {json.dumps({'type': 'delta', 'text': event.delta.text}, ensure_ascii=False)}\n\n"
    except Exception as e:
        err_msg = str(e)
        if "authentication" in err_msg.lower() or "api_key" in err_msg.lower() or "401" in err_msg:
            err_msg = "Anthropic API Key 无效或未配置，请在顶部输入有效的 sk-ant-... Key"
        yield f"data: {json.dumps({'type': 'error', 'message': err_msg}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def _openai_stream(
    provider: str,
    messages: list[dict],
    system: str | None,
    model: str,
    max_tokens: int,
) -> AsyncGenerator[str, None]:
    """通过 OpenAI 兼容 SDK 流式输出"""
    client = _get_openai_client(provider)

    # 合并 system 提示词
    msgs: list[dict] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=msgs,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield f"data: {json.dumps({'type': 'delta', 'text': delta.content}, ensure_ascii=False)}\n\n"
    except Exception as e:
        err_msg = str(e)
        # 让前端能识别 auth 错误
        if "401" in err_msg or "Authentication" in err_msg or "Invalid API Key" in err_msg.lower() or "api key" in err_msg.lower():
            err_msg = f"API Key 无效或已过期，请重新配置 {PROVIDER_CONFIGS[provider]['name']} 的 API Key"
        yield f"data: {json.dumps({'type': 'error', 'message': err_msg}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── 非流式对话 ────────────────────────────────────────────────────────────────

async def chat_complete(
    messages: list[dict],
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 2048,
    provider: str | None = None,
) -> str:
    """统一非流式聊天接口，返回文本字符串"""
    p = provider or _active_provider
    m = model or _selected_models.get(p, PROVIDER_CONFIGS[p]["default_model"])

    if p == "anthropic":
        return await _anthropic_complete(messages, system, m, max_tokens)
    else:
        return await _openai_complete(p, messages, system, m, max_tokens)


async def _anthropic_complete(
    messages: list[dict],
    system: str | None,
    model: str,
    max_tokens: int,
) -> str:
    from app.core.claude_client import get_client
    client = get_client()
    kwargs: dict = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system
    try:
        response = client.messages.create(**kwargs)
        return next((b.text for b in response.content if b.type == "text"), "")
    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or "api_key" in err.lower() or "401" in err:
            raise ValueError("Anthropic API Key 无效或未配置，请在顶部输入有效的 sk-ant-... Key") from e
        raise


async def _openai_complete(
    provider: str,
    messages: list[dict],
    system: str | None,
    model: str,
    max_tokens: int,
) -> str:
    client = _get_openai_client(provider)
    msgs: list[dict] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=msgs,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower() or "api key" in err.lower():
            raise ValueError(f"{PROVIDER_CONFIGS[provider]['name']} API Key 无效或已过期，请重新配置") from e
        raise
